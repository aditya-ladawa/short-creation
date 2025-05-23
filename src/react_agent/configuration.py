# configuration.py

"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Annotated, Any, Literal, Optional, Type, TypeVar

from langchain_core.runnables import RunnableConfig, ensure_config
from langgraph.config import get_config

from react_agent import prompts


# Generic Base Configuration
@dataclass
class BaseConfiguration:
    """Base configuration class for indexing, retrieval, and agent operations."""

    user_id: str = field(metadata={"description": "Unique identifier for the user."})

    embedding_model: Annotated[
        str,
        {"__template_metadata__": {"kind": "embeddings"}},
    ] = field(
        default="google_vertexai/text-embedding-large-exp-03-07",
        metadata={
            "description": "Name of the embedding model to use. Must be a valid embedding model name."
        },
    )

    retriever_search_kwargs: dict[str, Any] = field(
        default_factory=lambda: {"k": 10, "alpha": 0.5}, # Increased k for reranking
        metadata={
            "description": "Keyword arguments for the base retriever search (e.g., k for number of results, alpha for hybrid search weighting)."
        },
    )

    reranker_model: Annotated[
        Optional[str],
        {"__template_metadata__": {"kind": "reranker"}},
    ] = field(
        # Updated default to BGE reranker
        default="BAAI/bge-reranker-v2-m3",
        metadata={
            "description": "The Hugging Face cross-encoder model name to use for reranking (e.g., 'BAAI/bge-reranker-v2-m3'). Set to None to disable reranking."
        },
    )
    reranker_top_n: int = field(
        default=3, # Keep top 3 after reranking
        metadata={"description": "Number of documents to return after reranking."}
    )

    @classmethod
    def from_runnable_config(
        cls: Type[T], config: Optional[RunnableConfig] = None
    ) -> T:
        """Create a BaseConfiguration instance from a RunnableConfig object."""
        if config is None:
            try:
                config = get_config()
            except RuntimeError:
                config = None
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})


T = TypeVar("T", bound=BaseConfiguration)


# Specific Agent Configuration
@dataclass
class Configuration(BaseConfiguration):
    """The full configuration for the agent."""
    
    thread_id: str = field(
        default="short-creator-test",
        metadata={"description": "Thread identifier for the current workflow/process."},
    )

    script_gen_prompt: str = field(
        default=prompts.SCRIPT_GEN_PROMPT,
        metadata={
            "description": "The system prompt for script generation by the agent."
        },
    )

    psych_gen_prompt: str = field(
        default=prompts.PSYCH_GEN_PROMPT,
        metadata={
            "description": "The system prompt for topic generation for a short video on psychological concepts"
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="deepseek/deepseek-chat",
        metadata={
            "description": "The language model used for main interactions. Should be in the form: provider/model-name."
        },
    )

    response_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="deepseek/deepseek-chat",
        metadata={
            "description": "The language model used for generating responses. Should be in the form: provider/model-name."
        },
    )

    query_system_prompt: str = field(
        default=prompts.QUERY_SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt used for processing and refining queries."
        },
    )

    query_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="deepseek/deepseek-chat",
        metadata={
            "description": "The language model used for processing and refining queries. Should be in the form: provider/model-name."
        },
    )