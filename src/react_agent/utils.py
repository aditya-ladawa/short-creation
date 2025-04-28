"""Utility & helper functions."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
from typing_extensions import Optional


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
# Make sure to import VideoScript from wherever you defined your structures
from .structures import VideoScript, VideoSection, Visual, Sound # Assuming structures.py

def videoscript_to_text(script_obj: VideoScript) -> str:
    """
    Converts a VideoScript Pydantic object into a formatted text string.

    Args:
        script_obj: An instance of the VideoScript Pydantic model.

    Returns:
        A formatted string representing the video script.
    """
    lines = []

    # Access attributes directly from the Pydantic object
    title = script_obj.title
    length = script_obj.length

    lines.append(f"# 🎬 {title}\n")

    # Iterate through the list of VideoSection Pydantic objects
    for section in script_obj.sections:
        # Access attributes from the nested Pydantic objects
        section_title = section.section
        text = section.text
        visual: Visual = section.visual # Type hint for clarity
        sound: Sound = visual.sound     # Type hint for clarity

        scene = visual.scene
        transition = visual.transition
        music = sound.music
        sound_effects = sound.sound_effects

        lines.append(f"## {section_title}\n{text}")

        # Pydantic handles optional fields gracefully; checking for truthiness works.
        if scene:
            lines.append(f"🎥 Scene: {scene}")
        if transition:
            lines.append(f"✨ Transition: {transition}")
        if music:
            lines.append(f"🎶 Music: {music}")
        if sound_effects:
            lines.append(f"🔊 Sound Effects: {sound_effects}")

        lines.append("")  # blank line between sections

    lines.append(f"⏱ Estimated Length: {length}")

    return "\n".join(lines)