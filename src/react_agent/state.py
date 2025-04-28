"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, List, Optional
import operator

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated
from langchain_core.documents import Document


from react_agent.structures import VideoScript

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
    """Defines the input state for the agent, representing a narrower interface to the outside world.
    
    Contains only the messages that will be processed by the agent.
    """
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    """
    Messages tracking the primary execution state of the agent.
    
    The `add_messages` annotation ensures that new messages are merged with existing ones,
    updating by ID to maintain an "append-only" state unless a message with the same ID is provided.
    """


@dataclass
class State(InputState):
    """Complete agent state."""
    
    is_last_step: IsLastStep = field(default=False)

    scripts: Annotated[Sequence[VideoScript], operator.add] = field(default_factory=list)
    queries: Annotated[Sequence[str], add_queries] = field(default_factory=list)
    docs: Annotated[Sequence[Document], reduce_docs] = field(default_factory=list)

@dataclass
class IndexState:
    """Represents the state for document indexing and retrieval.

    This class defines the structure of the index state, which includes
    the documents to be indexed and the retriever used for searching
    these documents.
    """

    docs: Annotated[Sequence[Document], reduce_docs]
    """A list of documents that the agent can index."""