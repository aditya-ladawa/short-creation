from typing import List, Optional, Dict
from pydantic import BaseModel, Field

## script_generator
# Sound class for defining sound-related elements in the script
class Sound(BaseModel):
    music: str = Field(..., description="Type of background music suitable for the given scenario, e.g., 'calm', 'motivational', etc.")
    sound_effects: Optional[str] = Field(None, description="Any sound effects, e.g., 'clock ticking', 'murmurs', etc.")
    silence_duration: Optional[str] = Field(None, description="Duration of silence after key moments, e.g., '2 seconds', None if no silence.")

# Visual class for defining visual elements in the script
class Visual(BaseModel):
    scene: str = Field(..., description="Description of the scene or action happening.")
    camera_angle: str = Field(..., description="Type of camera angle used in the scene (e.g., 'close-up', 'medium shot').")
    transition: str = Field(..., description="Transition type between scenes (e.g., 'fade-in', 'cut to', 'zoom-in').")
    sound: Sound = Field(..., description="Sound properties associated with the visual (music, sound effects, silence).")

# Video section class for defining each section in the script
class VideoSection(BaseModel):
    section: str = Field(..., description="Section name, e.g., 'Hook', 'Real-World Example', 'Actionable Tip'.")
    text: str = Field(..., description="Text to be said during this section of the video.")
    visual: Visual = Field(..., description="Visual and sound details associated with this section.")

# Full video script structure
class VideoScript(BaseModel):
    title: str = Field(..., description="Title of the video, e.g., 'The Power of Silence in Communication'.")
    length: str = Field(..., description="Video length in seconds, e.g., '60-90 seconds'.")
    sections: List[VideoSection] = Field(..., description="List of sections in the script, each containing text and visual information.")


class SearchQuery(BaseModel):
    """Search the indexed documents for a query."""

    query: str


class RetrievalQueries(BaseModel):
    """
    A list of search queries designed to retrieve relevant psychological concepts, 
    studies, and applications for script generation.
    """
    queries: List[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="List of distinct search queries to retrieve psychological concepts, studies, and real-world applications. Each query should be specific enough to target relevant information but broad enough to capture diverse perspectives."
    )