import asyncio
import os
from dotenv import load_dotenv
from pprint import pprint

from psycopg_pool import AsyncConnectionPool

from langchain_deepseek import ChatDeepSeek

from langgraph.graph import StateGraph
from langgraph.constants import START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import PoolConfig

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.structures import *
from react_agent.graph import (
    script_generator,
    get_videos,
    generate_audio,
    media_editor,
    add_captions,
    get_and_join_bgm,
    topic_data_generator,
    upload_short,
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
model = ChatDeepSeek(model='deepseek-chat', temperature=0.6)

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
    builder.add_node("upload_short", upload_short)


    # Define workflow edges
    builder.add_edge(START, "topic_data_generator")
    builder.add_edge("topic_data_generator", "script_generator")
    builder.add_edge("script_generator", "generate_audio")
    builder.add_edge("generate_audio", "get_videos")
    builder.add_edge("get_videos", "media_editor")
    builder.add_edge("media_editor", "add_captions")
    builder.add_edge("add_captions", "get_and_join_bgm")
    builder.add_edge('get_and_join_bgm', 'upload_short')
    builder.add_edge('upload_short', '__end__')

    return builder.compile(checkpointer=checkpointer)


def print_final_output_dict(final_reel):
    print("\n🎞️ FINAL REEL DETAILS")
    print(f"  📍 Final Reel Path      : {final_reel.final_reel_path}")
    print(f"  🗂️ Original Reel Path   : {final_reel.original_reel_path}")
    print(f"  🕒 Video Duration       : {final_reel.video_duration} sec")
    print(f"  🔊 Audio Volume         : {final_reel.audio_volume}")
    print(f"  🧾 Created At           : {final_reel.created_at}")

    track = final_reel.track_info
    print("\n🎵 SELECTED TRACK")
    print(f"  🎼 Title                : {track.track_title}")
    print(f"  👤 Composer             : {track.track_composer}")
    print(f"  📝 Description          : {track.track_description}")
    print(f"  ⏱️ Duration             : {track.track_duration} ({track.track_duration_seconds}s)")
    print(f"  🔗 URL                  : {track.track_url}")
    if track.recommendation_reason:
        print(f"  💡 Reason               : {track.recommendation_reason}")
    if track.attribution_text:
        print(f"  📜 Attribution          : {track.attribution_text}")
    if track.download_path:
        print(f"  📁 Download Path        : {track.download_path}")

    if final_reel.processing_metadata:
        print("\n⚙️ PROCESSING METADATA")
        pprint(final_reel.processing_metadata, indent=2)


def print_psychology_short_dict(label: str, psych):
    print(f"\n🧠 {label}")
    print(f"  🔤 Concept Title        : {psych.concept_title}")
    print(f"  📚 Explanation          : {psych.explanation}")
    print(f"  🎯 Psychological Effect : {psych.psychological_effect}")
    print(f"  🌍 Real-World Use       : {psych.real_world_application}")
    print(f"  📺 YouTube Title        : {psych.youtube_title}")
    print(f"  📝 Description          : {psych.youtube_description}")
    print(f"  🏷️ Hashtags             : {' '.join(psych.hashtags or [])}")
    print(f"  📣 CTA Line             : {psych.cta_line}")
    print(f"  💼 Value Pitch          : {psych.value_pitch}")


def print_state_summary_dict(state: dict):
    if "final_reel" in state and state["final_reel"]:
        print_final_output_dict(state["final_reel"])

    if "psych_insight" in state and state["psych_insight"]:
        print_psychology_short_dict("CURRENT PSYCHOLOGY INSIGHT", state["psych_insight"])

    if "previous_topics" in state and state["previous_topics"]:
        print("\n📚 PREVIOUS PSYCHOLOGY SHORTS")
        for idx, past in enumerate(state["previous_topics"], 1):
            print_psychology_short_dict(f"Previous #{idx}", past)


config = {"configurable": {"thread_id": "short-creator-test"}}

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

        print(f"\n[INFO] Initiated invoke... \n")
        result = await graph.ainvoke({}, config=config)
        
        print("Workflow complete:")


async def run_get_state():
    async with AsyncConnectionPool(conninfo=DB_URI_CHECKPOINTER, max_size=20, kwargs=connection_kwargs) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        print(f"\n[INFO] Checkpointer done... \n")

        graph = await build_graph_with_checkpointer(checkpointer)
        print(f"\n[INFO] Called graph... \n")


        print(f"\n[INFO] Initiated state get... \n")
        result = await graph.aget_state(config=config, subgraphs=True)

        # Pretty print selected parts of the state
        print_state_summary_dict(result.values)

        print("\n✅ Workflow complete.")



if __name__ == "__main__":
    asyncio.run(run_job())
    # asyncio.run(run_get_state())


