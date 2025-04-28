"""This "graph" simply exposes an endpoint for a user to upload docs to be indexed."""

from typing_extensions import Optional, Sequence

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

from react_agent.retrieval import make_retriever
from react_agent.configuration import BaseConfiguration
from react_agent.state import IndexState


def ensure_docs_have_user_id(
    docs: Sequence[Document], config: RunnableConfig
) -> list[Document]:
    """Ensure that all documents have a user_id in their metadata.

        docs (Sequence[Document]): A sequence of Document objects to process.
        config (RunnableConfig): A configuration object containing the user_id.

    Returns:
        list[Document]: A new list of Document objects with updated metadata.
    """
    user_id = config["configurable"]["user_id"]
    return [
        Document(
            page_content=doc.page_content, metadata={**doc.metadata, "user_id": user_id}
        )
        for doc in docs
    ]


async def index_docs(
    state: IndexState, *, config: Optional[RunnableConfig] = None
) -> dict[str, str]:
    """Asynchronously index documents in the given state using the configured retriever.

    This function takes the documents from the state, ensures they have a user ID,
    adds them to the retriever's index, and then signals for the documents to be
    deleted from the state.

    Args:
        state (IndexState): The current state containing documents and retriever.
        config (Optional[RunnableConfig]): Configuration for the indexing process.r
    """
    if not config:
        raise ValueError("Configuration required to run index_docs.")
    with retrieval.make_retriever(config) as retriever:
        stamped_docs = ensure_docs_have_user_id(state.docs, config)

        await retriever.aadd_documents(stamped_docs)
    return {"docs": "delete"}


builder = StateGraph(IndexState, config_schema=BaseConfiguration)
builder.add_node(index_docs)
builder.add_edge("__start__", "index_docs")
index_graph = builder.compile()

