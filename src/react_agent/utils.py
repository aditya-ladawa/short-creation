import os
import re
import json
from pathlib import Path
from typing import List, Dict
from typing_extensions import Optional

from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

from .structures import VideoScript, VideoSection, Visual, SectionSound, GlobalSound

load_dotenv()


BASE_SCRIPT_PATH = os.environ.get('BASE_SCRIPT_PATH')

def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    return init_chat_model(model, model_provider=provider)


def videoscript_to_text(script_obj: VideoScript, safe_title: str) -> tuple[str, str]:
    """
    Converts a VideoScript Pydantic object into:
    1. A formatted text string (with visuals/sound)
    2. Section-only texts joined by '\n\n'

    Saves the section-only text to a .txt file in the specified path.

    Args:
        script_obj: VideoScript object
        safe_title: Filename-safe title for saving

    Returns:
        (formatted_script_text, section_text_only)
    """
    lines = []
    section_texts = []

    # Header with title and global music
    lines.append(f"# 🎬 {script_obj.title}\n")
    lines.append(f"🎵 Background Music: {script_obj.background_music.music}\n")
    lines.append(f"⏱ Length: {script_obj.length}\n")

    for section in script_obj.sections:
        # Full formatted content
        lines.append(f"## {section.section}\n{section.text}")
        section_texts.append(section.text)

        # Visual and audio annotations
        visual = section.visual
        lines.append(f"🎥 Scene: {visual.scene}")
        lines.append(f"✨ Transition: {visual.transition}")
        lines.append(f"📷 Camera: {visual.camera_angle}")

        sound = visual.sound
        if sound.sound_effects:
            timing = f" ({sound.sound_effect_timing})" if sound.sound_effect_timing else ""
            lines.append(f"🔊 SFX: {sound.sound_effects}{timing}")
        if sound.silence_duration:
            lines.append(f"🤫 Silence: {sound.silence_duration}")

        lines.append("")

    formatted_script = "\n".join(lines)
    section_text_only = "\n\n".join(section_texts)

    # Save section-only text
    output_path = Path(BASE_SCRIPT_PATH) / f"{safe_title}.txt"
    output_path.write_text(section_text_only, encoding="utf-8")
    print(f"✅ Saved section-only script text at: {output_path}")

    return formatted_script, section_text_only


def extract_video_data(pexels_response: Dict) -> List[Dict]:
    """Extract and format video data from Pexels API response"""
    if not pexels_response.get("data"):
        return []
        
    videos = pexels_response["data"].get("videos", [])
    
    formatted_videos = []
    for video in videos:
        formatted = {
            "id": video["id"],
            "width": video["width"],
            "height": video["height"],
            "duration": video["duration"],
            "author": video["user"]["name"],
            "author_url": video["user"]["url"],
            "video_url": video["url"],
            "preview_image": video["image"],
            "video_files": []
        }
        
        for file in video["video_files"]:
            formatted["video_files"].append({
                "file_type": file["file_type"],
                "width": file["width"],
                "height": file["height"],
                "link": file["link"],
                "quality": file["quality"],
                "fps": file.get("fps"),
                "size": file.get("size")
            })
            
        formatted_videos.append(formatted)
    
    return formatted_videos


def extract_video_name(url: str) -> str:
    """
    Extracts the descriptive name from a Pexels video URL.
    Example: "https://www.pexels.com/video/a-man-made-pond-surrounded-by-rocks-and-plants-8195680/"
             → "A Man Made Pond Surrounded By Rocks And Plants"
    """
    match = re.search(r'/video/([^/]+)-\d+/?$', url)
    if match:
        return match.group(1).replace('-', ' ').title()
    return "Untitled"


def sanitize_filename(name: str) -> str:
    """
    Convert a string to a safe filename:
    - Replace spaces with underscores
    - Remove non-alphanumeric characters (except underscores and dashes)
    - Collapse multiple underscores
    """
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w\-]", "", name)  # Keep alphanumerics, underscores, dashes
    name = re.sub(r"_+", "_", name)  # Collapse multiple underscores
    return name.strip("_")