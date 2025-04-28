from datetime import datetime, timezone
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.utils import load_chat_model, videoscript_to_text, get_message_text
from react_agent.structures import VideoScript, SearchQuery
from react_agent.utils import format_docs
import json
from langgraph.types import interrupt, Command
from langgraph.constants import START, END
from langchain_deepseek import ChatDeepSeek
from react_agent.retrieval import make_retriever
from langchain_core.runnables import RunnableConfig



# Load the chat model
model = ChatDeepSeek(model='deepseek-chat')

# Step 1: Generate the query for document retrieval
async def generate_query(state: State) -> Dict[str, Any]:
    messages = state.messages
    if len(messages) == 1:
        # For the first user input, we use it directly as the query
        user_input = get_message_text(messages[-1])
        return {"queries": [user_input]}
    else:
        # For subsequent messages, generate a refined query using the model
        configuration = Configuration.from_context()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", configuration.query_system_prompt),
                ("placeholder", "{messages}"),
            ]
        )
        query_model = load_chat_model(configuration.query_model)
        message_value = await prompt.ainvoke({"messages": state.messages})
        query_response = await query_model.ainvoke(message_value)
        return {"queries": [query_response]}

# Step 2: Retrieve documents based on the query
async def retrieve(state: State, config: RunnableConfig) -> Dict[str, Any]:
    with retrieval.make_retriever(config) as retriever:
        response = await retriever.ainvoke(state.queries[-1], config)
        return {"retrieved_docs": response}

# Step 3: Generate the script using the retrieved documents
async def script_generator(state: State) -> Dict[str, Any]:
    configuration = Configuration.from_context()
    script_gen_prompt = Configuration.script_gen_prompt

    # Retrieve documents for context
    retriever_results = await retrieve(state, configuration)
    retrieved_docs = retriever_results["retrieved_docs"]
    
    # Format retrieved documents
    formatted_docs = format_docs(retrieved_docs)

    # Trim the messages for the script generation
    trimmed_messages = trim_messages(
        messages=state.messages,
        token_counter=count_tokens_approximately,
        strategy='last',
        max_tokens=12128,
        include_system=True,
        allow_partial=False,
        start_on='human'
    )

    # Combine the retrieved documents with the user messages
    script_gen_template = ChatPromptTemplate(
        messages=[
            ('system', script_gen_prompt),
            MessagesPlaceholder(variable_name="messages"),
            ('system', f"Context from retrieved documents: {formatted_docs}"),
        ]
    )
    script_gen_chain = script_gen_template | model.with_structured_output(VideoScript)

    script_response = await script_gen_chain.ainvoke({"messages": trimmed_messages})
    script_text = videoscript_to_text(script_response)

    print('Generated script based on retrieved documents:')
    print(script_text)

    return {"scripts": [script_response], "messages": [AIMessage(content=script_text)]}

# Step 4: Request feedback from the user
async def request_feedback(state: State) -> Dict[str, Any]:
    latest_script = state.messages[-1].content
    user_feedback = interrupt(value=f'{latest_script}\n\nDo you want to revise the script? If not, answer "no", else mention the changes.')
    return {'messages': [HumanMessage(content=user_feedback)]}

# Step 5: Revise the script based on user feedback
async def revise_script(state: State) -> Dict[str, Any]:
    user_feedback = state.messages[-1].content
    latest_script_obj = state.scripts[-1]
    latest_script_text = videoscript_to_text(latest_script_obj)

    trimmed_messages = trim_messages(
        messages=state.messages,
        token_counter=count_tokens_approximately,
        strategy='last',
        max_tokens=12128,
        include_system=True,
        allow_partial=False,
        start_on='human'
    )

    system_prompt = f"""Revise the following script based on user's feedback.
    
    User feedback:
    {user_feedback}

    Latest script:
    {latest_script_text}

    Only return the revised script in the same format.
    """

    script_rev_template = ChatPromptTemplate(
        messages=[
            ('system', system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    script_rev_chain = script_rev_template | model.with_structured_output(VideoScript)

    script_response = await script_rev_chain.ainvoke({"messages": trimmed_messages})
    script_text = videoscript_to_text(script_response)

    return {"scripts": [script_response], "messages": [AIMessage(content=script_text)]}

# Route the feedback based on user's response
async def route_feedback(state: State):
    user_feedback = state.messages[-1].content

    if user_feedback.strip().lower() == 'no':
        return END
    else:
        return 'revise_script'

# Step 6: Define the nodes and the workflow
builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Add nodes to the graph
builder.add_node('generate_query', generate_query)
builder.add_node('retrieve', retrieve)
builder.add_node('script_generator', script_generator)
builder.add_node('request_feedback', request_feedback)
builder.add_node('revise_script', revise_script)

# Set up the workflow structure
builder.set_entry_point("generate_query")
builder.add_edge("generate_query", "retrieve")
builder.add_edge("retrieve", "script_generator")
builder.add_edge("script_generator", "request_feedback")
builder.add_edge("revise_script", "request_feedback")

# Conditional loop for feedback
builder.add_conditional_edges(
    'request_feedback',
    route_feedback,  # This function determines continue or end
    path_map={
        END: END,  # If "no", end the workflow
        'revise_script': 'revise_script'  # If feedback is provided, revise the script
    }
)

graph = builder.compile()
