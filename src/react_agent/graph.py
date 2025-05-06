from datetime import datetime, timezone
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.utils import load_chat_model, videoscript_to_text, get_message_text, extract_video_data, sanitize_filename, extract_video_name
from react_agent.structures import *
import json
from langgraph.types import interrupt, Command
from langgraph.constants import START, END
from langchain_deepseek import ChatDeepSeek
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from pathlib import Path
import requests
import json
import re
from react_agent.pexels_handler import pexels
from react_agent.handle_kokoro import generate_tts

## Load the chat model
model = ChatDeepSeek(model='deepseek-chat', temperature=0.6)
# model = load_chat_model('google_vertexai/gemini-2.0-flash')
# model = ChatGroq(model='meta-llama/llama-4-scout-17b-16e-instruct')



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
    return {
        "scripts": [script_response],
        "messages": [AIMessage(content=script_text)]
    }


# Step 4: Request feedback from the user
async def request_feedback(state: State) -> Dict[str, Any]:
    latest_script = state.messages[-1].content
    user_feedback = interrupt(value=f'{latest_script}\n\nDo you want to revise the script? If not, answer "no" to continue towards video search, else mention the changes.')
    return {'messages': [HumanMessage(content=user_feedback)]}

# Step 5: Revise the script based on user feedback
async def revise_script(state: State) -> Dict[str, Any]:
    user_feedback = state.messages[-1].content
    latest_script_obj = state.scripts[-1]
    latest_script_text = videoscript_to_text(latest_script_obj)
    # print('\nIN REVIS SCRIPT\n')

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

    return {
        "scripts": [script_response],
        "messages": [AIMessage(content=script_text)]
    }



async def get_videos(state: State) -> dict:
    """Search Pexels for videos matching each visual scene and download multiple validated videos with metadata."""
    latest_script_obj = state.scripts[-1]
    safe_title = sanitize_filename(latest_script_obj.title)
    video_dir = Path(f"my_test_files/videos/{safe_title}/")
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure visuals directory exists
    visuals_dir = video_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    validated_videos = []
    failed_sections = []

    for section in latest_script_obj.sections:
        search_query = section.visual.scene
        search_params = {
            "query": search_query,
            "orientation": "portrait",
            "size": "medium",
            "page": 1,
            "per_page": 10,
        }

        try:
            # 1. Search Pexels
            pexels_response = pexels.search_videos(search_params)
            if pexels_response.get("status_code") != 200:
                raise ValueError(f"Pexels API returned {pexels_response.get('status_code')}")

            # 2. Extract and validate video data
            videos_data = extract_video_data(pexels_response)
            if not videos_data:
                raise ValueError("No videos returned from Pexels")

            video_dict = {
                str(video['id']): extract_video_name(video['video_url'])
                for video in videos_data
            }
            video_entries = "\n".join([f"{k}: {v}" for k, v in video_dict.items()])

            # 3. LLM Prompt for multiple matches
            system_prompt = """You are an expert video assistant.

            Given the script section:
            {section_text}

            And the search query used:
            {search_query}

            Here are some matching videos received from Pexels API in the format 'id':'video_name'.
            {video_entries}

            Choose 3-6 MOST relevant videos for this section. Respond with a list of matches where each item contains "video_id" and "video_name"."""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
            ])

            get_matching_videos = prompt | model.with_structured_output(PexelsVideoMultiMatch)
            result: PexelsVideoMultiMatch = await get_matching_videos.ainvoke({
                "section_text": section.text,
                "search_query": search_query,
                "video_entries": video_entries
            })

            print(f"\n||::|| Search query: {search_query}")
            print(f"✅ Selected matches: {[m for m in result.matches]}")

            # 4. Loop through each match and download
            for match in result.matches:
                video_id = match["video_id"]
                video_name = match["video_name"]

                # Find matching video in Pexels data
                matching_video = next(
                    (v for v in videos_data if str(v["id"]) == video_id),
                    None
                )
                
                if not matching_video:
                    print(f"⚠️ Skipped invalid video ID from LLM: {video_id}")
                    continue

                # Filter for suitable SD videos
                target_aspect = 9 / 16
                sd_videos = [
                    v for v in matching_video.get("video_files", [])
                    if v["quality"] == "sd" and v["width"] / v["height"] <= target_aspect
                ] or [
                    v for v in matching_video.get("video_files", []) 
                    if v["quality"] == "sd"
                ]

                if not sd_videos:
                    print(f"⚠️ No suitable SD format for video {video_id}")
                    continue

                # Select best aspect ratio match
                download_video = min(
                    sd_videos,
                    key=lambda v: abs((v["width"] / v["height"]) - target_aspect)
                )

                # Download the video
                filename = sanitize_filename(f"{section.section}_{video_id}") + '.mp4'
                video_path = visuals_dir / filename 

                response = requests.get(download_video["link"], stream=True)
                response.raise_for_status()
                with open(video_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Create metadata
                video_meta = VideoMetadata(
                    script_section=section.section,
                    pexels_id=matching_video["id"],
                    file_path=str(video_path),
                    search_query=search_query,
                    author=matching_video.get("author"),
                    author_url=str(matching_video.get("author_url")),
                    video_url=str(matching_video.get("video_url")),
                    dimensions=f"{download_video['width']}x{download_video['height']}",
                    duration=matching_video.get("duration"),
                    quality=download_video.get("quality")
                )
                validated_videos.append(video_meta)

        except Exception as e:
            print(f"⚠️ Failed section '{section.section}': {str(e)}")
            failed_sections.append({
                "section": section.section,
                "error": str(e),
                "query": search_query
            })
            continue

    # Save metadata
    metadata_path = visuals_dir / "video_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump([v.model_dump(mode='json') for v in validated_videos], f, indent=4)

    return {
        "videos": validated_videos,
        "failed_sections": failed_sections
    }

async def generate_audio(state: State) -> dict:
    """Generates TTS audio for the latest script without duplication"""
    latest_script = state.scripts[-1]
    script_title = sanitize_filename(latest_script.title)
    audio_segments = []
    
    for section in latest_script.sections:
        meta = generate_tts(
            text=section.text,
            video_name=script_title,
            section=section.section,
            voice="af_jessica"
        )
        if meta:  # Only append if generation succeeded
            audio_segments.append(meta)
    
    return {
        "audio_metadata": audio_segments
    }


# Route the feedback based on user's response
async def route_feedback(state: State):
    user_feedback = state.messages[-1].content
    
    if user_feedback == 'no':
        return 'get_videos'
    else:
        return 'revise_script'


# Step 6: Define the nodes and the workflow
builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Add all nodes including the new audio generation
builder.add_node('script_generator', script_generator)
builder.add_node('request_feedback', request_feedback)
builder.add_node('revise_script', revise_script)
builder.add_node('route_feedback', route_feedback)
builder.add_node('get_videos', get_videos)
# builder.add_node('generate_audio', generate_audio)  # New audio generation node



# Define workflow structure
builder.add_edge(START, "script_generator")
builder.add_edge("script_generator", "request_feedback")

builder.add_conditional_edges(
    'request_feedback',
    route_feedback,
    path_map={
        'get_videos': 'get_videos',  # No feedback → generate audio first
        'revise_script': 'revise_script'     # Feedback → revise script
    }
)

# Connect the audio generation to video fetching
# builder.add_edge("generate_audio", "get_videos")  # Audio → Videos

# Loop back for revisions
builder.add_edge("revise_script", "request_feedback")

# Final edge after video generation
builder.add_edge("get_videos", END)

graph = builder.compile()