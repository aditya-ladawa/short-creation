# from typing import List, Optional, Dict
# from pydantic import BaseModel, Field

# class GlobalSound(BaseModel):
#     """Background music that plays throughout the entire video"""
#     music: str = Field(
#         ...,
#         description="Type of continuous background music suitable for the entire video (e.g., 'calm ambient', 'subtle motivational', 'light electronic'). Should match the overall tone of the psychological concept."
#     )

# class SectionSound(BaseModel):
#     """Sound elements specific to individual sections"""
#     sound_effects: Optional[str] = Field(
#         None,
#         description="Specific sound effects timed with visual elements (e.g., 'clock ticking during tense moment', 'crowd murmur for social scene'). Only include if dramatically relevant."
#     )
#     silence_duration: Optional[str] = Field(
#         None,
#         description="Strategic pauses after key moments (e.g., '2 seconds after shocking statistic', '1 beat before reveal'). Format as 'X seconds' or None."
#     )
#     sound_effect_timing: Optional[str] = Field(
#         None,
#         description="When to play the sound effect relative to the action (e.g., 'as the person realizes', 'when text appears', 'during transition')"
#     )

# class Visual(BaseModel):
#     scene: str = Field(..., description="Detailed description of the scene/action")
#     camera_angle: str = Field(..., description="Shot type (e.g., 'extreme close-up', 'over-the-shoulder')")
#     transition: str = Field(..., description="How this scene connects to next (e.g., 'quick cut', 'slow dissolve')")
#     sound: SectionSound = Field(..., description="Section-specific sound enhancements")

# class VideoSection(BaseModel):
#     section: str = Field(..., description="Script section name")
#     text: str = Field(..., description="Narration/dialogue text")
#     visual: Visual = Field(..., description="Visual storytelling elements")

# class VideoScript(BaseModel):
#     title: str = Field(..., description="Attention-grabbing title")
#     length: str = Field(..., description="Duration (90-120 seconds)")
#     background_music: GlobalSound = Field(..., description="Continuous soundtrack")
#     sections: List[VideoSection] = Field(..., description="Script sections in order")

# class SearchQuery(BaseModel):
#     """Search the indexed documents for a query."""

#     query: str


# class RetrievalQueries(BaseModel):
#     """
#     A list of search queries designed to retrieve relevant psychological concepts, 
#     studies, and applications for script generation.
#     """
#     queries: List[str] = Field(
#         ...,
#         min_items=1,
#         max_items=3,
#         description="List of distinct search queries to retrieve psychological concepts, studies, and real-world applications. Each query should be specific enough to target relevant information but broad enough to capture diverse perspectives."
#     )

from typing_extensions import TypedDict, Optional
from typing import List

class GlobalSound(TypedDict):
    """Background music that plays throughout the entire video"""
    music: str

class SectionSound(TypedDict):
    """Sound elements specific to individual sections"""
    sound_effects: Optional[str]
    silence_duration: Optional[str]
    sound_effect_timing: Optional[str]

class Visual(TypedDict):
    scene: str
    camera_angle: str
    transition: str
    sound: SectionSound

class VideoSection(TypedDict):
    section: str
    text: str
    visual: Visual

class VideoScript(TypedDict):
    title: str
    length: str
    background_music: GlobalSound
    sections: List[VideoSection]

class SearchQuery(TypedDict):
    """Search the indexed documents for a query."""
    query: str

class RetrievalQueries(TypedDict):
    """
    A list of search queries designed to retrieve relevant psychological concepts, 
    studies, and applications for script generation.
    """
    queries: List[str]
