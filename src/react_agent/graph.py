import os
import re
import json
import asyncio
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

from dotenv import load_dotenv
from pydantic import BaseModel

import ffmpeg

from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command
from langgraph.constants import START, END

from langchain_deepseek import ChatDeepSeek
from langchain_groq import ChatGroq

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.structures import *
from react_agent.utils import (
    load_chat_model,
    videoscript_to_text,
    get_message_text,
    extract_video_data,
    sanitize_filename,
    extract_video_name,
)
from react_agent.handle_kokoro import generate_tts
from react_agent.handle_captions import VideoCaptioner
from react_agent.pexels_handler import pexels, search_and_validate_videos
from react_agent.video_editor import (
    BASE_VIDEOS_PATH,
    OUTPUT_DIR_BASE,
    SECTION_ORDER,
    get_duration,
    apply_segment_effects,
    create_reel_for_audio,
    concatenate_sections,
)

load_dotenv()
video_captioner = VideoCaptioner()

os.makedirs(os.environ.get('BASE_VIDEOS_PATH'), exist_ok=True)
os.makedirs(os.environ.get('OUTPUT_DIR_BASE'), exist_ok=True)
os.makedirs(os.environ.get('BASE_SCRIPT_PATH'), exist_ok=True)

model = ChatDeepSeek(model='deepseek-chat', temperature=0.6)


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
    safe_title = sanitize_filename(script_response.title)
    script_text, _ = videoscript_to_text(script_response, safe_title)
    return {
        "scripts": [script_response],
        "messages": [AIMessage(content=script_text)]
    }


async def request_feedback(state: State) -> Dict[str, Any]:
    latest_script = state.messages[-1].content
    user_feedback = interrupt(value=f'{latest_script}\n\nDo you want to revise the script? If not, answer "no" to continue towards video search, else mention the changes.')
    return {'messages': [HumanMessage(content=user_feedback)]}


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

    visuals_dir = video_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    validated_videos = []
    failed_sections = []

    for section in latest_script_obj.sections:
        section_dir = visuals_dir / sanitize_filename(f"section_{section.section}")
        section_dir.mkdir(parents=True, exist_ok=True)

        videos, failures = await search_and_validate_videos(section=section, model=model, section_dir=section_dir)
        validated_videos.extend(videos)
        failed_sections.extend(failures)

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
        print('section', section.section, '\n')
        meta = generate_tts(
            text=section.text,
            video_name=script_title,
            section=section.section,
            voice="af_bella"
        )
        if meta:  # Only append if generation succeeded
            audio_segments.append(meta)
    
    return {
        "audio_metadata": audio_segments
    }


async def route_feedback(state: State):
    user_feedback = state.messages[-1].content
    
    if (user_feedback).lower().strip() == 'no':
        return 'generate_audio'
    else:
        return 'revise_script'


async def media_editor(state: State) -> EditMediaResult:
    latest_script_obj = state.scripts[-1]
    safe_title = sanitize_filename(latest_script_obj.title)

    script_path = os.path.join(BASE_VIDEOS_PATH, safe_title)
    script_audio_path = os.path.join(script_path, 'audio')
    script_video_path = os.path.join(script_path, 'visuals')
    output_script_root = os.path.join(OUTPUT_DIR_BASE, safe_title)

    os.makedirs(output_script_root, exist_ok=True)

    warnings = []
    sections_created = []
    section_tasks = []

    if not os.path.isdir(script_audio_path):
        warning = f"Audio directory not found for script {safe_title}: {script_audio_path}"
        print(warning)
        return EditMediaResult(
            script_title=safe_title,
            output_dir=output_script_root,
            final_reel_path=None,
            sections_created=[],
            warnings=[warning]
        )

    print(f"\nProcessing Script folder: {safe_title}")
    available_audio_files = sorted([
        f for f in os.listdir(script_audio_path)
        if f.lower().endswith(('.wav', '.mp3', '.m4a', '.aac'))
    ])

    if not available_audio_files:
        warning = f"No audio files found in {script_audio_path} for script {safe_title}."
        print(warning)
        return EditMediaResult(
            script_title=safe_title,
            output_dir=output_script_root,
            final_reel_path=None,
            sections_created=[],
            warnings=[warning]
        )

    intermediate_output_dir = os.path.join(output_script_root, "intermediate_sections")
    os.makedirs(intermediate_output_dir, exist_ok=True)

    section_task_map = {}

    for audio_file in available_audio_files:
        section_name = os.path.splitext(audio_file)[0]
        section_key = section_name.upper()
        audio_path = os.path.join(script_audio_path, audio_file)

        vids_for_section = []
        section_visuals_folder = os.path.join(script_video_path, f'section_{section_name}')
        potential_visual_sources = [d for d in [section_visuals_folder, script_video_path] if os.path.isdir(d)]

        for source_dir in potential_visual_sources:
            vids_for_section.extend([
                os.path.join(source_dir, f)
                for f in os.listdir(source_dir)
                if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
            ])

        vids_for_section = sorted(list(set(vids_for_section)))

        if not vids_for_section:
            warning = f"No visual files found for section {section_key} in expected folders."
            print(warning)
            warnings.append(warning)
            section_task_map[section_key] = None
            continue

        safe_section_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in section_name)
        output_path = os.path.join(intermediate_output_dir, f'reel_{safe_section_name}.mp4')

        task = asyncio.create_task(create_reel_for_audio(audio_path, vids_for_section, output_path))
        section_task_map[section_key] = task

    # Await all tasks
    processed_section_files_map = {}
    for section_key, task in section_task_map.items():
        if task is None:
            processed_section_files_map[section_key] = None
            continue
        try:
            result_path = await task
            if result_path:
                duration = await get_duration(result_path)
                processed_section_files_map[section_key] = result_path
                sections_created.append(SectionOutput(
                    section_key=section_key,
                    path=result_path,
                    duration=duration
                ))
                print(f"Section {section_key} processed: {result_path}")
            else:
                warning = f"Section {section_key} failed to render a valid reel."
                warnings.append(warning)
                print(warning)
                processed_section_files_map[section_key] = None
        except Exception as e:
            warning = f"Exception in processing section {section_key}: {e}"
            print(warning)
            warnings.append(warning)
            processed_section_files_map[section_key] = None

    # Final Concatenation
    ordered_paths = []
    print(f"\nPreparing final reel for script '{safe_title}' based on order: {SECTION_ORDER}")
    for key in SECTION_ORDER:
        if key in processed_section_files_map and processed_section_files_map[key]:
            ordered_paths.append(processed_section_files_map[key])
            print(f"  + Added section '{key}'")
        else:
            msg = f"  - Warning: Section '{key}' missing or failed"
            print(msg)
            warnings.append(msg)

    final_reel_path = None
    if ordered_paths:
        final_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in safe_title)
        final_reel_path = os.path.join(output_script_root, f"{final_name}.mp4")
        await concatenate_sections(ordered_paths, final_reel_path)
    else:
        warning = f"No valid sections found for concatenation in script '{safe_title}'"
        print(warning)
        warnings.append(warning)

    result = EditMediaResult(
        script_title=safe_title,
        output_dir=output_script_root,
        final_reel_path=final_reel_path,
        sections_created=sections_created,
        warnings=warnings
    )
    return {
        "media_result": result
    }


async def add_captions(state: State) -> CaptionOutput:
    """Add captions to video and return structured output"""

    captioner = video_captioner
    print(f"\n[INFO] Using captioner from state: {captioner}\n")

    # Get the latest script and create a sanitized title
    latest_script_obj = state.scripts[-1]
    safe_title = sanitize_filename(latest_script_obj.title)

    # Create output directory
    output_dir = Path(os.path.join(OUTPUT_DIR_BASE, safe_title))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define file paths
    reel_video = output_dir / f"{safe_title}.mp4"
    reel_captioned = output_dir / f"CAPTIONED_{safe_title}.mp4"
    subtitles_json = output_dir / f"{safe_title}.json"

    reel_audio = await captioner.extract_audio_from_video(reel_video)

    # Step 2: Generate word-level subtitles
    print("[INFO] Generating word-level subtitles...")
    word_segments = await captioner.generate_subtitles(str(reel_audio))

    # Step 3: Structure subtitles into lines
    print("[INFO] Structuring subtitles into lines...")
    line_subtitles = await captioner.create_line_level_subtitles(word_segments)

    # Step 4: Save subtitle JSON
    print(f"[INFO] Saving subtitles to JSON: {subtitles_json}")
    await captioner.save_subtitles_to_json(line_subtitles, str(subtitles_json))

    # Step 5: Add animated captions to video
    print("[INFO] Rendering video with captions...")
    await captioner.add_captions_to_video(
        video_path=str(reel_video),
        subtitles=line_subtitles,
        output_path=str(reel_captioned)
    )

    print(f"[SUCCESS] Captioned video created at: {reel_captioned}")

    captioned_output = CaptionOutput(
        captioned_video_path=str(reel_captioned),
        subtitles_json_path=str(subtitles_json),
        original_video_path=str(reel_video),
        audio_path=str(reel_audio)
    )

    return {'captioned_output': caption_output}




# Define the nodes and the workflow
builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Add all nodes including the new audio generation
builder.add_node('script_generator', script_generator)
# builder.add_node('request_feedback', request_feedback)
# builder.add_node('revise_script', revise_script)
# builder.add_node('route_feedback', route_feedback)
builder.add_node('get_videos', get_videos)
builder.add_node('generate_audio', generate_audio)  # New audio generation node
builder.add_node('media_editor', media_editor)
builder.add_node('add_captions', add_captions)


# Define workflow structure
builder.add_edge(START, "script_generator")
# builder.add_edge("script_generator", "request_feedback")
builder.add_edge("script_generator", "generate_audio")

# builder.add_conditional_edges(
#     'request_feedback',
#     route_feedback,
#     path_map={
#         'generate_audio': 'generate_audio',
#         'revise_script': 'revise_script'
#     }
# )

# Connect the audio generation to video fetching
builder.add_edge("generate_audio", "get_videos")

# # Loop back for revisions
# builder.add_edge("revise_script", "request_feedback")

# Final edge after video generation
builder.add_edge("get_videos", 'media_editor')
builder.add_edge('media_editor', 'add_captions')

builder.add_edge('add_captions', '__end__')


graph = builder.compile()