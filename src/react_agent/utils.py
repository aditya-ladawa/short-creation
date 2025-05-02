"""Utility & helper functions."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
from typing_extensions import Optional, List, Dict
import re
import json


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

def _format_doc(doc: Document) -> str:
    """Format a single document as XML.

    Args:
        doc (Document): The document to format.

    Returns:
        str: The formatted document as an XML string.
    """
    metadata = doc.metadata or {}
    meta = "".join(f" {k}={v!r}" for k, v in metadata.items())
    if meta:
        meta = f" {meta}"

    return f"<document{meta}>\n{doc.page_content}\n</document>"


def format_docs(docs: Optional[list[Document]]) -> str:
    """Format a list of documents as XML.

    This function takes a list of Document objects and formats them into a single XML string.

    Args:
        docs (Optional[list[Document]]): A list of Document objects to format, or None.

    Returns:
        str: A string containing the formatted documents in XML format.

    Examples:
        >>> docs = [Document(page_content="Hello"), Document(page_content="World")]
        >>> print(format_docs(docs))
        <documents>
        <document>
        Hello
        </document>
        <document>
        World
        </document>
        </documents>

        >>> print(format_docs(None))
        <documents></documents>
    """
    if not docs:
        return "<documents></documents>"
    formatted = "\n".join(_format_doc(doc) for doc in docs)
    return f"""<documents>
{formatted}
</documents>"""



from typing import List
from .structures import VideoScript, VideoSection, Visual, SectionSound, GlobalSound

def videoscript_to_text(script_obj: VideoScript) -> str:
    """
    Converts a VideoScript Pydantic object into a formatted text string.
    Now supports unified background music and section-specific sound design.
    
    Args:
        script_obj: An instance of the VideoScript Pydantic model with:
                   - Unified background_music (GlobalSound)
                   - Section-specific sound effects (SectionSound)
                   
    Returns:
        A formatted string representing the video script with audio annotations.
    """
    lines = []
    
    # Header with title and global music
    lines.append(f"# 🎬 {script_obj.title}\n")
    lines.append(f"🎵 Background Music: {script_obj.background_music.music}\n")
    lines.append(f"⏱ Length: {script_obj.length}\n")
    
    # Process each section
    for section in script_obj.sections:
        lines.append(f"## {section.section}\n{section.text}")
        
        # Visual elements
        visual = section.visual
        lines.append(f"🎥 Scene: {visual.scene}")
        lines.append(f"✨ Transition: {visual.transition}")
        lines.append(f"📷 Camera: {visual.camera_angle}")
        
        # Sound design elements
        sound = visual.sound
        if sound.sound_effects:
            timing = f" ({sound.sound_effect_timing})" if sound.sound_effect_timing else ""
            lines.append(f"🔊 SFX: {sound.sound_effects}{timing}")
        if sound.silence_duration:
            lines.append(f"🤫 Silence: {sound.silence_duration}")
        
        lines.append("")  # Section separator
    
    return "\n".join(lines)


# from typing import List
# from .structures import VideoScript, VideoSection, Visual, SectionSound, GlobalSound

# def videoscript_to_text(script_obj: VideoScript) -> str:
#     """
#     Converts a VideoScript TypedDict object into a formatted text string.
#     Now supports unified background music and section-specific sound design.
    
#     Args:
#         script_obj: An instance of the VideoScript TypedDict with:
#                    - Unified background_music (GlobalSound)
#                    - Section-specific sound effects (SectionSound)
                   
#     Returns:
#         A formatted string representing the video script with audio annotations.
#     """
#     lines = []
    
#     # Header with title and global music
#     lines.append(f"# 🎬 {script_obj['title']}\n")
#     lines.append(f"🎵 Background Music: {script_obj['background_music']['music']}\n")
#     lines.append(f"⏱ Length: {script_obj['length']}\n")
    
#     # Process each section
#     for section in script_obj['sections']:
#         lines.append(f"## {section['section']}\n{section['text']}")
        
#         # Visual elements
#         visual = section['visual']
#         lines.append(f"🎥 Scene: {visual['scene']}")
#         lines.append(f"✨ Transition: {visual['transition']}")
#         lines.append(f"📷 Camera: {visual['camera_angle']}")
        
#         # Sound design elements
#         sound = visual['sound']
#         if sound.get('sound_effects'):
#             timing = f" ({sound['sound_effect_timing']})" if sound.get('sound_effect_timing') else ""
#             lines.append(f"🔊 SFX: {sound['sound_effects']}{timing}")
#         if sound.get('silence_duration'):
#             lines.append(f"🤫 Silence: {sound['silence_duration']}")
        
#         lines.append("")  # Section separator
    
#     return "\n".join(lines)



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

# def extract_video_data(videos_dict):
#     results = []
#     for video in videos_dict.get('data', {}).get('videos', []):
#         video_info = {
#             'id': video.get('id'),
#             'duration': video.get('duration'),
#             'width': video.get('width'),
#             'height': video.get('height'),
#             'preview_image': video.get('image'),
#             'author': video.get('user', {}).get('name'),
#             'author_url': video.get('user', {}).get('url'),
#             'video_url': video.get('url'),
#             'video_files': []
#         }

#         for vf in video.get('video_files', []):
#             video_info['video_files'].append({
#                 'quality': vf.get('quality'),
#                 'file_type': vf.get('file_type'),
#                 'width': vf.get('width'),
#                 'height': vf.get('height'),
#                 'fps': vf.get('fps'),
#                 'link': vf.get('link'),
#                 'size': vf.get('size')
#             })

#         results.append(video_info)

#     return results
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