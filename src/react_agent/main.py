import asyncio
import os
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

from langchain_deepseek import ChatDeepSeek

from langgraph.graph import StateGraph
from langgraph.constants import START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import PoolConfig

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.graph import (
    script_generator,
    get_videos,
    generate_audio,
    media_editor,
    add_captions,
    get_and_join_bgm,
    topic_data_generator,
)
from react_agent.handle_captions import VideoCaptioner
from react_agent.utils import load_chat_model

print("All imports successful...\n")
# Load environment variables
load_dotenv()

# Ensure required directories exist
os.makedirs(os.environ.get('BASE_VIDEOS_PATH', 'videos'), exist_ok=True)
os.makedirs(os.environ.get('OUTPUT_DIR_BASE', 'outputs'), exist_ok=True)
os.makedirs(os.environ.get('BASE_SCRIPT_PATH', 'scripts'), exist_ok=True)

# DB setup
DB_URI_CHECKPOINTER = os.environ.get('DB_URI_CHECKPOINTER')
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

# Instantiate reusable global components
video_captioner = VideoCaptioner()
model = ChatDeepSeek(model='deepseek-chat', temperature=0.8)

async def build_graph_with_checkpointer(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(State, input=InputState, config_schema=Configuration)

    # Add nodes
    builder.add_node('topic_data_generator', topic_data_generator)
    builder.add_node('script_generator', script_generator)
    builder.add_node('generate_audio', generate_audio)
    builder.add_node('get_videos', get_videos)
    builder.add_node('media_editor', media_editor)
    builder.add_node('add_captions', add_captions)
    builder.add_node('get_and_join_bgm', get_and_join_bgm)

    # Define workflow edges
    builder.add_edge(START, "topic_data_generator")
    builder.add_edge("topic_data_generator", "script_generator")
    builder.add_edge("script_generator", "generate_audio")
    builder.add_edge("generate_audio", "get_videos")
    builder.add_edge("get_videos", "media_editor")
    builder.add_edge("media_editor", "add_captions")
    builder.add_edge("add_captions", "get_and_join_bgm")
    builder.add_edge("get_and_join_bgm", "__end__")

    return builder.compile(checkpointer=checkpointer)


# Entry point
async def run_job():
    # Initialize Postgres connection pool and checkpointer
    async with AsyncConnectionPool(conninfo=DB_URI_CHECKPOINTER, max_size=20, kwargs=connection_kwargs) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        print(f"\n[INFO] Checkpointer done... \n")

        # Compile graph with checkpointer
        graph = await build_graph_with_checkpointer(checkpointer)

        print(f"\n[INFO] Called graph... \n")

        config = {
          "configurable": {
          "thread_id": "short-creator-1"
        }
}

        print(f"\n[INFO] Initiated invoke... \n")
        result = await graph.ainvoke({}, config=config)
        
        print("Workflow complete:")


if __name__ == "__main__":
    asyncio.run(run_job())
