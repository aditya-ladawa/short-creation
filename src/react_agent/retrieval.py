from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse
from FlagEmbedding import FlagReranker
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
import os
import torch
from dotenv import load_dotenv
import json
load_dotenv()

# class HybridRerankerRetriever(BaseRetriever, BaseModel):
#     """Enhanced hybrid retriever with Qdrant (BM25 + dense) and reranking"""
    
#     vector_store: QdrantVectorStore
#     reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3")
#     top_n: int = Field(default=5)  # Increased from 3 to get more context
#     normalize_scores: bool = Field(default=True)
#     _reranker: FlagReranker = PrivateAttr()
    
#     def __init__(self, **data):
#         super().__init__(**data)
#         device = "cuda" if torch.cuda.is_available() else "cpu"
#         print(f"Using device: {device} for reranker")
#         self._reranker = FlagReranker(
#             self.reranker_model,
#             device=device
#         )

#     def _get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
#         """Enhanced retrieval with hybrid search and reranking"""
#         # First-stage retrieval with more candidates
#         results_with_scores = self.vector_store.similarity_search_with_score(
#             query,
#             k=self.top_n * 5,  # Get more candidates for better recall
#         )
        
#         hybrid_results = [doc for doc, _ in results_with_scores]
#         hybrid_scores = [score for _, score in results_with_scores]
        
#         # Normalize hybrid scores
#         if hybrid_scores and self.normalize_scores:
#             max_score = max(hybrid_scores)
#             min_score = min(hybrid_scores)
#             if max_score != min_score:
#                 hybrid_scores = [(s - min_score)/(max_score - min_score) for s in hybrid_scores]
        
#         # Rerank with cross-encoder
#         query_doc_pairs = [[query, doc.page_content] for doc in hybrid_results]
#         reranker_scores = self._reranker.compute_score(
#             query_doc_pairs,
#             normalize=self.normalize_scores
#         )
        
#         # Combine and score documents
#         scored_docs = []
#         for doc, hybrid_score, reranker_score in zip(hybrid_results, hybrid_scores, reranker_scores):
#             combined_score = self._combine_scores(hybrid_score, reranker_score)
#             scored_docs.append(Document(
#                 page_content=doc.page_content,
#                 metadata={
#                     **doc.metadata,
#                     "hybrid_score": float(hybrid_score),
#                     "reranker_score": float(reranker_score),
#                     "combined_score": float(combined_score)
#                 }
#             ))
        
#         # Return top documents by combined score
#         return sorted(scored_docs, key=lambda x: x.metadata["combined_score"], reverse=True)[:self.top_n]
    
#     def _combine_scores(self, hybrid_score: float, reranker_score: float) -> float:
#         """Weighted combination of scores favoring reranker"""
#         return (0.3 * hybrid_score) + (0.7 * reranker_score)  # Give more weight to reranker

def initialize_hybrid_retriever():
    """Initialize and return a properly configured hybrid retriever"""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=120
    )
    
    vector_store = QdrantVectorStore(
        client=client,
        collection_name='shorts-resources',
        embedding=embeddings,
        sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
        retrieval_mode="hybrid",
        vector_name="dense",
        sparse_vector_name="sparse"
    )
    
    return vector_store.as_retriever(
        search_type="mmr",  # Maximal Marginal Relevance
        search_kwargs={
            'k': 4,
            'lambda_mult': 0.5  # Balance between diversity and relevance
        }
    )
# if __name__ == "__main__":
#     retriever = initialize_hybrid_retriever()
    
#     while True:
#         query = input("\nEnter your query (or 'quit' to exit): ")
#         if query.lower() == 'quit':
#             break
            
#         print(f"\nSearching for: '{query}'")
#         results = retriever.invoke(query)
        
#         if not results:
#             print("No relevant documents found")
#             continue
            
#         print(f"\nFound {len(results)} relevant documents:")
#         for i, doc in enumerate(results, 1):
#             print(f"\nDocument {i}:")
#             print(f"Source: {doc.metadata.get('source', 'Unknown')}")
#             print(f"Content: {doc.page_content[:300]}...")  # Show first 300 chars
#             print("-" * 80)