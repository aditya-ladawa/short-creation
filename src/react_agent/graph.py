import os
import re
import json
import asyncio
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Annotated, Optional
import random
from pprint import pprint

from dotenv import load_dotenv
from pydantic import BaseModel

import ffmpeg

from langchain_core.messages import AIMessage, HumanMessage, trim_messages, SystemMessage
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
from react_agent.qdrant_db import TopicVectorStore, topic_store
from react_agent.handle_shorts_upload import youtube_upload_short
from react_agent.utils import (
    load_chat_model,
    videoscript_to_text,
    get_message_text,
    extract_video_data,
    sanitize_filename,
    extract_video_name,
    get_video_duration
)


from react_agent.handle_kokoro import generate_tts
from react_agent.handle_captions import VideoCaptioner
from react_agent.pexels_handler import pexels, search_and_validate_videos
from react_agent.handle_bensound_free import (
    BensoundScraper, 
    fetch_track, 
    download_track_with_selenium, 
    add_bgm_to_narrated_video_async
)

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


model = ChatDeepSeek(model='deepseek-chat', temperature=0.7)


async def topic_data_generator(state: State) -> dict:
    psych_gen_prompt = Configuration.psych_gen_prompt
    base_system_msg = (
        "You are a ruthless expert in real-world psychology, influence, and manipulation, "
        "trained to uncover deep, rarely-discussed tactics that give people real leverage in chaotic environments. "
        "Your output must be raw, actionable, and gray-area by nature."
    )

    prior_titles = [entry.concept_title for entry in state.previous_topics] if state.previous_topics else []
    print(f"\n [INFO] PRIOR TITLES: {prior_titles} \n")
    retry_attempts = 3

    for attempt in range(retry_attempts):
        retry_info = ""
        if prior_titles:
            retry_info = (
                f"\nAvoid these previously generated topics: {', '.join(prior_titles)}.\n"
                "Avoid previously discussed topics. Focus on deeply overlooked, radically novel psychological angles that are rarely touched in popular content."
            )

        # Trim conversation messages
        trimmed_messages = trim_messages(
            messages=state.messages,
            token_counter=count_tokens_approximately,
            strategy='last',
            max_tokens=121128,
            include_system=True,
            allow_partial=False,
            start_on='human'
        )

        # Prepare prompt
        psych_prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=base_system_msg + retry_info),
            SystemMessage(content=psych_gen_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

        # Create chain
        psych_gen_chain = psych_prompt_template | model.with_structured_output(PsychologyShort)

        # Call model with context
        insight: PsychologyShort = await psych_gen_chain.ainvoke({
            "messages": trimmed_messages
        })

        print(f"\n[INFO] Title: {insight.concept_title}  \n")

        # Check for duplication
        is_duplicate, match_title = await topic_store.is_duplicate(insight)
        if not is_duplicate:
            await topic_store.add_concept(insight)
            updated_topics = state.previous_topics + [insight] if state.previous_topics else [insight]
            return {
                'psych_insight': insight,
                'previous_topics': updated_topics
            }

    raise ValueError(f"All {retry_attempts} attempts generated duplicate topics. "
                     "Consider revising the prompt or increasing creativity.")



async def script_generator(state: State) -> Dict[str, Any]:
    script_gen_prompt = Configuration.script_gen_prompt
    topic_selected = state.psych_insight

    trimmed_messages = trim_messages(
        messages=state.messages,
        token_counter=count_tokens_approximately,
        strategy='last',
        max_tokens=12128,
        include_system=True,
        allow_partial=False,
        start_on='human'
    )

    human_message = f"""
        Concept title: {topic_selected.concept_title}\n
        Explanation: {topic_selected.explanation}\n
        Psychological Effect: {topic_selected.psychological_effect}\n
        Real World Application: {topic_selected.real_world_application}\n


    """
    
    script_gen_template = ChatPromptTemplate.from_messages([
        ("system", script_gen_prompt),
        ('human', human_message),
    ])

    script_gen_chain = script_gen_template | model.with_structured_output(VideoScript)
    script_response = await script_gen_chain.ainvoke({})
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
        print('\n [INFO] section', section.section, '\n')
        meta = generate_tts(
            text=section.text,
            video_name=script_title,
            section=section.section,
            voice="af_bella"
        )
        if meta:
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

    # print(f"\n [INFO] Processing Script folder: {safe_title}\n")
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

    print(f"\n [INFO] Using captioner from state: {video_captioner} \n")

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

    reel_audio = await video_captioner.extract_audio_from_video(reel_video)

    # Step 2: Generate word-level subtitles
    print("[INFO] Generating word-level subtitles...")
    word_segments = await video_captioner.generate_subtitles(str(reel_audio))

    # Step 3: Structure subtitles into lines
    print("[INFO] Structuring subtitles into lines...")
    line_subtitles = await video_captioner.create_line_level_subtitles(word_segments)

    # Step 4: Save subtitle JSON
    print(f"[INFO] Saving subtitles to JSON: {subtitles_json}")
    await video_captioner.save_subtitles_to_json(line_subtitles, str(subtitles_json))

    # Step 5: Add animated captions to video
    print("[INFO] Rendering video with captions...")
    await video_captioner.add_captions_to_video(
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

    return {'captioned_output': captioned_output}




async def get_and_join_bgm(state: State) -> FinalOutput:
    print("Starting get_and_join_bgm...")

    latest_script_obj = state.scripts[-1]
    reel_bgm_genre = latest_script_obj.background_music.music
    # print(reel_bgm_genre)
    # print(type(reel_bgm_genre))

    latest_captioned_reel = state.captioned_output
    # print(type(latest_captioned_reel))
    # print(latest_captioned_reel)
    captioned_reel_path = latest_captioned_reel.captioned_video_path
    print(f"\nCaptioned reel path: {captioned_reel_path} ")

    reel_duration = get_video_duration(captioned_reel_path)
    print(f"Video duration: {reel_duration:.2f} seconds")

    bgm_volume = 0.35
    fade_duration = 1.0

    # general_bgm_genres = ['ambient piano', 'subtle piano', 'calm', 'ambient', 'chill', 'lofi']
    # random_bgm_genre = random.choice(general_bgm_genres)
    print(f"Selected random BGM genre: {reel_bgm_genre}")
    # print(f"\nSelected random BGM genre: 'dark ambient'\n")

    print("\nFetching tracks from Bensound...")
    tracks_info_str, tracks_data = await fetch_track(
        n_pages=1,
        save_path=state.media_result.output_dir,
        input_query=reel_bgm_genre
    )
    print(f"Number of tracks fetched: {len(tracks_data)}")

    if not tracks_data:
        print("No tracks found for selected genre")
        raise ValueError("No tracks found for selected genre")

    print("Requesting model recommendation...")
    model_recommendation = await model.with_structured_output(SelectedTrack).ainvoke(
        f"Video duration: {reel_duration:.2f}s. Genre: '{reel_bgm_genre}'. "
        f"Select a track (duration >= video) with matching mood:\n{tracks_info_str}"
    )
    print(f"Model recommended track index: {model_recommendation.track_index}")
    print(f"Reason: {model_recommendation.recommendation_reason}")


    selected_track = tracks_data[model_recommendation.track_index - 1]
    print(f"Selected track title: {selected_track['title']}")

    download_dir = os.path.abspath(state.media_result.output_dir)
    os.makedirs(download_dir, exist_ok=True)
    print(f"\nDownloading track to: {download_dir}\n")
    attribution_text = download_track_with_selenium(selected_track["url"], download_dir)
    print(f"Track downloaded successfully. \n")
    selected_track_name = (selected_track['title']).strip().lower().replace(' ', '')
    print(selected_track_name)
    track_path = os.path.join(download_dir, f"{selected_track_name}.mp3")

    base_name = os.path.basename(captioned_reel_path)
    final_output_path = os.path.join(
        state.media_result.output_dir,
        f"FINAL_{base_name}"
    )
    print(f"\n [INFO] Final output video path: {final_output_path}\n")

    try:
        print("Starting ffmpeg processing to add BGM...")
        final_output_path = await add_bgm_to_narrated_video_async(
            video_path=captioned_reel_path,
            bgm_path=track_path,
            output_path=final_output_path,
            bgm_volume=bgm_volume,
            fade_duration=fade_duration,
            sc_threshold='-40dB',
            sc_ratio=4,
            sc_attack=200,
            sc_release=1600,
            sc_level_in=1,
            sc_level_sc=1,
            sc_makeup=1
        )
        # print("FFmpeg processing completed successfully")
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode('utf8') if e.stderr else str(e)
        print(f"FFmpeg processing failed: {error_msg}")
        raise RuntimeError(f"FFmpeg processing failed: {error_msg}")

    final_output = FinalOutput(
        final_reel_path=final_output_path,
        original_reel_path=captioned_reel_path,
        track_info=SelectedTrack(
            track_index=model_recommendation.track_index,
            track_title=selected_track['title'],
            track_composer=selected_track['composer'],
            track_description=selected_track['description'],
            track_duration=str(selected_track['duration']),
            track_duration_seconds=model_recommendation.track_duration_seconds,
            track_url=selected_track['url'],
            recommendation_reason=model_recommendation.recommendation_reason,
            download_path=track_path,
            attribution_text=attribution_text
        ),
        processing_metadata={
            'bgm_volume': bgm_volume,
            'fade_duration': fade_duration,
            'original_audio_present': True  # Assuming video has audio if narration volume is used
        },
        video_duration=reel_duration,
        audio_volume=bgm_volume
    )

    # state.final_reel = final_output

    # Save final output JSON
    # json_path = os.path.join(state.media_result.output_dir, "final_output.json")
    # with open(json_path, "w", encoding="utf-8") as f:
    #     json.dump(final_output.dict(), f, indent=4)
    # print(f"Final output JSON saved to: {json_path}")

    print("\nFINAL OUTPUT METADATA: \n", final_output.dict(), '\n')
    return {"final_reel": final_output}


async def upload_short(state: State) -> State:
    short: PsychologyShort = state.psych_insight
    final: FinalOutput = state.final_reel

    print(f"\n[INFO] Loaded short and final data...")

    # Build full description
    track = final.track_info
    full_description = (
        f"{short.youtube_description}\n\n"
        f"{short.value_pitch}\n"
        f"{short.cta_line}\n\n"
        f"Tags: {' '.join(tag for tag in short.hashtags)}\n\n"
        f"Attribution text:\n"
        f"{track.attribution_text}\n\n"
        f"URL:\n {track.track_url}"
    )

    print(f"\n[INFO] Running upload...")

    # Upload in thread pool
    loop = asyncio.get_event_loop()
    short_link = await loop.run_in_executor(
        None,
        youtube_upload_short,
        final.final_reel_path,
        short.youtube_title,
        full_description,
        ",".join(short.hashtags),
        "27",  # categoryId for Education
        "public"
    )

    if short_link:
        final.short_link = short_link
        print(f"\n✅ Uploaded. Link: {short_link}")
    else:
        print("\n⚠️ Upload failed or link not returned.")

    json_path = os.path.join(state.media_result.output_dir, "final_output.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final.dict(), f, indent=4)
    print(f"Final output JSON saved to: {json_path}")

    return {"final_reel": final}



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
builder.add_node('get_and_join_bgm', get_and_join_bgm)
builder.add_node('topic_data_generator', topic_data_generator)
builder.add_node("upload_short", upload_short)


# Define workflow structure
builder.add_edge(START, "topic_data_generator")

builder.add_edge('topic_data_generator', "script_generator")
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

builder.add_edge('add_captions', 'get_and_join_bgm')
builder.add_edge('get_and_join_bgm', 'upload_short')
builder.add_edge('upload_short', '__end__')




graph = builder.compile()

