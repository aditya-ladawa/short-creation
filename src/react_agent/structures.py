import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Literal, Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from datetime import timedelta


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
    scene: str = Field(
        ...,
        description="Describe the setting and action using keywords suitable for Pexels stock footage (e.g., 'tired woman sitting alone at kitchen table', 'man staring blankly out a rainy window'). Include posture, facial expression, setting, and mood."
    )
    camera_angle: str = Field(
        ...,
        description="Specify the type of stock footage framing that best captures the emotion (e.g., 'close-up of facial expression', 'side profile in moody lighting', 'overhead shot of cluttered desk'). Keep it Pexels-search friendly."
    )
    transition: str = Field(
        ...,
        description="Simple visual transition keyword (e.g., 'cut to', 'fade to black', 'match cut') indicating how this clip flows into the next. Consider pacing and emotional tone."
    )
    sound: SectionSound = Field(
        ...,
        description="Section-specific sound elements that enhance emotion or realism. Pair well with the visuals described."
    )


class VideoSection(BaseModel):
    section: str = Field(..., description="Script section name")
    text: str = Field(..., description="Narration/dialogue text")
    visual: Visual = Field(..., description="Visual storytelling elements")

class VideoScript(BaseModel):
    title: str = Field(..., description="Attention-grabbing title")
    length: str = Field(..., description="Duration in seconds")
    background_music: GlobalSound = Field(..., description="Continuous background soundtrack")
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

class PexelsVideoMatch(BaseModel):
    video_id : str
    video_name : str

class PexelsVideoMultiMatch(BaseModel):
    matches: List[Dict[str, str]] = Field(
        ...,
        min_items=2,
        max_items=4,
        description="List of matched videos with IDs and names (2-4 items required)"
    )

def ensure_path(path: str | Path) -> Path:
    """Ensure we always work with Path objects internally"""
    return path if isinstance(path, Path) else Path(path)

class VideoMetadata(BaseModel):
    """Validated structure for Pexels video assets"""
    
    # Required Fields
    script_section: str = Field(
        ...,
        description="Script section ID this video matches",
        examples=["intro", "conclusion_1"]
    )
    
    pexels_id: int = Field(
        ...,
        gt=0,
        description="Pexels video ID for attribution"
    )
    
    file_path: str = Field(
        description="Local path to downloaded video file (as string)"
    )
    
    search_query: str = Field(
        ...,
        min_length=3,
        description="Original search query used"
    )

    # Optional Fields (with validation)
    author: Optional[str] = Field(
        None,
        min_length=2,
        description="Video creator name"
    )

    author_url: Optional[str] = Field(
        None,
        description="Pexels profile URL (as string)"
    )
    
    video_url: Optional[str] = Field(
        None,
        description="Pexels source page (as string)"
    )

    
    dimensions: Optional[str] = Field(
        None,
        pattern=r"^\d+x\d+$",
        examples=["1920x1080", "720x1280"]
    )
    
    duration: Optional[float] = Field(
        None,
        gt=0,
        le=600,
        description="Duration in seconds (max 10m)"
    )
    
    quality: Optional[Literal["sd", "hd", "uhd"]] = Field(
        None,
        description="Pexels quality tier"
    )
    
    downloaded_at: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="When file was saved locally"
    )

    # Derived Fields
    @property
    def attribution(self) -> str:
        return f"Video by {self.author} from Pexels" if self.author else "Pexels Stock Video"

    @field_validator('file_path')
    @classmethod 
    def validate_file_path(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            raise ValueError(f"File not found: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return str(path.absolute())  # Return normalized absolute path

    @field_validator('dimensions')
    @classmethod
    def validate_aspect_ratio(cls, v: str | None) -> str | None:
        if v:
            w, h = map(int, v.split('x'))
            ratio = w / h
            if not 0.4 <= ratio <= 0.8:  # Portrait orientation check
                raise ValueError(f"Invalid aspect ratio {ratio:.2f} - expected portrait")
        return v

    @field_validator('author_url', 'video_url')
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")
        return v



class AudioMetadata(BaseModel):
    """Metadata for generated TTS audio segments"""
    section: str = Field(..., description="Script section name")
    text: str = Field(..., description="Original text input")
    voice: str = Field(..., description="Voice model used")
    duration: float = Field(..., description="Audio duration in seconds")
    sample_rate: int = Field(..., description="Audio sample rate")
    file_path: str = Field(..., description="Path to WAV file")
    generated_at: datetime = Field(default_factory=datetime.now)


class SectionOutput(BaseModel):
    section_key: str
    path: str
    duration: Optional[float]

class EditMediaResult(BaseModel):
    script_title: str
    output_dir: str
    final_reel_path: Optional[str]
    sections_created: List[SectionOutput]
    warnings: List[str]


class CaptionOutput(BaseModel):
    captioned_video_path: str = Field(..., description="Path to the captioned video file")
    subtitles_json_path: Optional[str] = Field(None, description="Path to the subtitles JSON file")
    original_video_path: str = Field(..., description="Path to the original video file")
    status: str = Field("success", description="Status of the captioning operation")
    message: Optional[str] = Field(None, description="Additional status message")

class CaptioningError(BaseModel):
    error: str = Field(..., description="Error message")
    original_video_path: str = Field(..., description="Path to the original video file")
    status: str = Field("error", description="Status of the captioning operation")


class SelectedTrack(BaseModel):
    track_index: int
    track_title: str
    track_composer: str
    track_description: str
    track_duration: str  # Human-readable (MM:SS)
    track_duration_seconds: float
    track_url: str
    recommendation_reason: Optional[str] = None
    download_path: Optional[str] = None
    attribution_text: Optional[str] = None

class FinalOutput(BaseModel):
    final_reel_path: str
    original_reel_path: str
    track_info: SelectedTrack
    processing_metadata: Dict[str, Any] = {}
    video_duration: float
    audio_volume: float
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    short_link: Optional[str] = None


class PsychologyShort(BaseModel):
    concept_title: str
    explanation: str
    psychological_effect: str
    real_world_application: str
    youtube_title: str
    youtube_description: str
    hashtags: List[str]
    cta_line: str
    value_pitch: str

    