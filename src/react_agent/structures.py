from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class GlobalSound(BaseModel):
    """Background music that plays throughout the entire video"""
    music: str = Field(
        ...,
        description="Type of continuous background music suitable for the entire video (e.g., 'calm ambient', 'subtle motivational', 'light electronic'). Should match the overall tone of the psychological concept."
    )

class SectionSound(BaseModel):
    """Sound elements specific to individual sections"""
    sound_effects: Optional[str] = Field(
        None,
        description="Specific sound effects timed with visual elements (e.g., 'clock ticking during tense moment', 'crowd murmur for social scene'). Only include if dramatically relevant."
    )
    silence_duration: Optional[str] = Field(
        None,
        description="Strategic pauses after key moments (e.g., '2 seconds after shocking statistic', '1 beat before reveal'). Format as 'X seconds' or None."
    )
    sound_effect_timing: Optional[str] = Field(
        None,
        description="When to play the sound effect relative to the action (e.g., 'as the person realizes', 'when text appears', 'during transition')"
    )

class Visual(BaseModel):
    scene: str = Field(..., description="Detailed description of the scene/action")
    camera_angle: str = Field(..., description="Shot type (e.g., 'extreme close-up', 'over-the-shoulder')")
    transition: str = Field(..., description="How this scene connects to next (e.g., 'quick cut', 'slow dissolve')")
    sound: SectionSound = Field(..., description="Section-specific sound enhancements")

class VideoSection(BaseModel):
    section: str = Field(..., description="Script section name")
    text: str = Field(..., description="Narration/dialogue text")
    visual: Visual = Field(..., description="Visual storytelling elements")

class VideoScript(BaseModel):
    title: str = Field(..., description="Attention-grabbing title")
    length: str = Field(..., description="Duration (90-120 seconds)")
    background_music: GlobalSound = Field(..., description="Continuous soundtrack")
    sections: List[VideoSection] = Field(..., description="Script sections in order")

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


# #################################
# from typing_extensions import TypedDict, Optional
# from typing import List

# class GlobalSound(TypedDict):
#     """Background music that plays throughout the entire video"""
#     music: str

# class SectionSound(TypedDict):
#     """Sound elements specific to individual sections"""
#     sound_effects: Optional[str]
#     silence_duration: Optional[str]
#     sound_effect_timing: Optional[str]

# class Visual(TypedDict):
#     scene: str
#     camera_angle: str
#     transition: str
#     sound: SectionSound

# class VideoSection(TypedDict):
#     section: str
#     text: str
#     visual: Visual

# class VideoScript(TypedDict):
#     title: str
#     length: str
#     background_music: GlobalSound
#     sections: List[VideoSection]

# class SearchQuery(TypedDict):
#     """Search the indexed documents for a query."""
#     query: str

# class RetrievalQueries(TypedDict):
#     """
#     A list of search queries designed to retrieve relevant psychological concepts, 
#     studies, and applications for script generation.
#     """
#     queries: List[str]


# #######################################

# # from typing_extensions import TypedDict, Optional, Annotated
# # from typing import List

# # class GlobalSound(TypedDict):
# #     """Background music that plays throughout the entire video"""
# #     music: Annotated[str, "A detailed description of the background track's genre, mood, tempo, instruments, and atmosphere. Example: 'Low-tempo ambient piano with occasional rainfall sounds, evoking solitude and reflection.'"]

# # class SectionSound(TypedDict):
# #     """Sound elements specific to individual sections"""
# #     sound_effects: Annotated[Optional[str], 
# #         "Describe specific sound effects such as footsteps, glass breaking, digital beeps, or crowd noise. Include timing relevance and emotional tone, e.g., 'soft echoing footsteps on marble floor during a suspenseful monologue.'"
# #     ]
# #     silence_duration: Annotated[Optional[str], 
# #         "If silence is used for effect, describe its purpose and duration. Example: '1.5 seconds of dead silence before jump scare to create tension.'"
# #     ]
# #     sound_effect_timing: Annotated[Optional[str], 
# #         "Specify when in the section the sound effect happens. Example: 'Just after the character slams the door (0:14).'"]

# # class Visual(TypedDict):
# #     scene: Annotated[str, 
# #         "Describe the environment in extreme detail using rich visual language, including setting, lighting, objects, colors, mood, background elements, and atmosphere. Example: 'A man stands on a graffiti-covered rooftop at dusk, city skyline glowing orange behind him, smoke curling from a cigarette, wind fluttering his coat.'"
# #     ]
# #     camera_angle: Annotated[str, 
# #         "Define the type of camera angle and its narrative purpose. Include terms like aerial shot, over-the-shoulder, dolly zoom, slow pan, medium close-up, handheld chaos. Example: 'Over-the-shoulder shot revealing a woman's reflection in a cracked mirror.'"
# #     ]
# #     transition: Annotated[str, 
# #         "Describe how the current shot transitions into the next. Be explicit: 'Hard cut to black', 'Soft dissolve into dream sequence', 'Quick whip pan transition to simulate confusion.'"
# #     ]
# #     sound: SectionSound

# # class VideoSection(TypedDict):
# #     section: Annotated[str, 
# #         "Label the section’s narrative role or emotional tone, such as 'Introduction – Calm Tension', 'Turning Point – Realization', 'Climax – Confrontation', or 'Resolution – Isolation'."
# #     ]
# #     text: Annotated[str, 
# #         "The actual script or dialogue/narration for the section. Should reflect emotional tone, subtext, and delivery cues if needed."
# #     ]
# #     visual: Visual

# # class VideoScript(TypedDict):
# #     title: Annotated[str, 
# #         "Concise, compelling title of the video. Should signal emotional or conceptual weight. Example: 'The Psychology of Silence in Power Struggles'."
# #     ]
# #     length: Annotated[str, 
# #         "Total video duration in seconds, e.g., '120s', or '2 minutes'. Used for timing all audio/visuals precisely."
# #     ]
# #     background_music: GlobalSound
# #     sections: Annotated[List[VideoSection], 
# #         "An ordered list of detailed video sections, each with immersive visuals, precise transitions, FX timings, and layered psychological meaning."
# #     ]

# # class SearchQuery(TypedDict):
# #     """Search the indexed documents for a query."""
# #     query: Annotated[str, "The exact question or concept you want to retrieve information about. Be specific and context-rich. Example: 'How does silence function as a dominance display in workplace dynamics?'"]

# # class RetrievalQueries(TypedDict):
# #     """
# #     A list of search queries designed to retrieve relevant psychological concepts, 
# #     studies, and applications for script generation.
# #     """
# #     queries: Annotated[List[str], 
# #         "Each query should target nuanced, real-world psychological dynamics. Example: ['Cognitive dissonance in high-stakes negotiations', 'Subtle gaslighting techniques in long-term relationships']"
# #     ]
