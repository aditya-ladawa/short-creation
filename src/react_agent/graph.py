from datetime import datetime, timezone
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.utils import load_chat_model, videoscript_to_text, get_message_text
from react_agent.structures import *
import json
from langgraph.types import interrupt, Command
from langgraph.constants import START, END
from langchain_deepseek import ChatDeepSeek
from langchain_core.runnables import RunnableConfig



# Load the chat model
model = ChatDeepSeek(model='deepseek-chat', temperature=0.0)
# model = load_chat_model('google_vertexai/gemini-2.0-flash')



# Step 3: Generate the script using the retrieved documents
async def script_generator(state: State) -> Dict[str, Any]:
    script_gen_prompt = Configuration.script_gen_prompt

    trimmed_messages = trim_messages(
        messages=state.messages,
        token_counter=count_tokens_approximately,
        strategy='last',
        max_tokens=12128,
        include_system=True,
        allow_partial=False,
        start_on='human'
    )

    
    script_gen_template = ChatPromptTemplate.from_messages([
        ("system", script_gen_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    script_gen_chain = script_gen_template | model.with_structured_output(VideoScript)
    script_response = await script_gen_chain.ainvoke({"messages": trimmed_messages})
    script_text = videoscript_to_text(script_response)
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
    print('\nIN REVIS SCRIPT\n')

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

    script_response = await script_rev_chain.ainvoke(trimmed_messages)
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


builder.add_node('script_generator', script_generator)
builder.add_node('request_feedback', request_feedback)
builder.add_node('revise_script', revise_script)
builder.add_node('route_feedback', route_feedback)

# Set up the workflow structure
builder.set_entry_point("script_generator")
builder.add_edge("script_generator", "request_feedback")

# Modified conditional loop for feedback
builder.add_conditional_edges(
    'request_feedback',
    route_feedback,
    path_map={
        END: END,  # If "no", end the workflow
        'revise_script': 'revise_script'  # If feedback is provided, restart the process
    }
)

# Add these edges to handle the revision path
builder.add_edge("revise_script", "request_feedback")  # After revision, ask for feedback again

graph = builder.compile()