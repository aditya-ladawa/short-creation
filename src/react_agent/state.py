from __future__ import annotations

import operator
import uuid
from dataclasses import dataclass, field
from typing import Sequence, List, Optional, Union, Literal, Any, Dict

from typing_extensions import Annotated

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep

from react_agent.structures import (
    VideoScript,
    VideoMetadata,
    AudioMetadata,
    EditMediaResult,
    CaptionOutput,
)
from react_agent.handle_captions import VideoCaptioner

def add_queries(existing: Sequence[str], new: Sequence[str]) -> Sequence[str]:
    return list(existing) + list(new)

def reduce_docs(
    existing: Optional[Sequence[Document]],
    new: Union[
        Sequence[Document],
        Sequence[dict[str, Any]],
        Sequence[str],
        str,
        Literal["delete"],
    ],
) -> Sequence[Document]:
    if new == "delete":
        return []
    if isinstance(new, str):
        return [Document(page_content=new, metadata={"id": str(uuid.uuid4())})]
    if isinstance(new, list):
        coerced = []
        for item in new:
            if isinstance(item, str):
                coerced.append(
                    Document(page_content=item, metadata={"id": str(uuid.uuid4())})
                )
            elif isinstance(item, dict):
                coerced.append(Document(**item))
            else:
                coerced.append(item)
        return coerced
    return existing or []

@dataclass
class InputState:
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(default_factory=list)

@dataclass
class RetrievalState:
    queries: Sequence[str] = field(default_factory=list)
    final_response: str = field(default="")

@dataclass
class State(InputState, RetrievalState):
    is_last_step: bool = field(default=False)
    
    scripts: List[VideoScript] = field(default_factory=list)
    
    videos: List[VideoMetadata] = field(default_factory=list)
    
    audio_metadata: AudioMetadata = field(default_factory=dict)

    media_result: EditMediaResult = field(default_factory=dict)

    caption_output: CaptionOutput = field(default_factory=dict)