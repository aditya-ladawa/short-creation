"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

from datetime import UTC, datetime
from typing import Dict, List, Literal, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.utils import (
    trim_messages, 
    count_tokens_approximately
)
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools import TOOLS
from react_agent.utils import load_chat_model

# Define the function that calls the model


async def generate_script(state: State) -> Dict[str, List[AIMessage]]:
    """Call the LLM powering our "agent".

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state (State): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the model's response message.
    """
    configuration = Configuration.from_context()

    # Initialize the model with tool binding. Change the model or add more tools here.
    model = load_chat_model(configuration.model)

    # Format the system prompt. Customize this to change the agent's behavior.
    system_message = configuration.script_gen_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

    # Trim history
    trimmed_messages=trim_messages(
        messages=state.messages,
        token_counter=count_tokens_approximately,
        strategy='last',
        max_tokens=12128,
        include_system=True,
        allow_partial=False,
        start_on='human'
    )

    # Get the model's response
    response = cast(
        AIMessage,
        await model.ainvoke(
            [{"role": "system", "content": system_message}] + list(trimmed_messages)
        ),
    )

    # Return the model's response as a list to be added to existing messages
    return {"messages": [response]}


# Define a new graph

builder = StateGraph(State, input=InputState, config_schema=Configuration)

builder.add_node(generate_script)
builder.add_edge("__start__", "generate_script")
builder.add_edge('generate_script', '__end__')

# Compile the builder into an executable graph
graph = builder.compile(name="short_creation_workflow")
