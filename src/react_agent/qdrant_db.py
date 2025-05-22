import uuid
from uuid import uuid4
import os
import asyncio
import fitz  # PyMuPDF
import tiktoken

from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from typing import List, Dict, Tuple, Optional

from datetime import datetime

from dotenv import load_dotenv

from react_agent.structures import PsychologyShort

from pydantic import BaseModel, Field

from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from tqdm import tqdm
import gc
import psutil
import json

load_dotenv()

# Initialize models
llm = ChatVertexAI(model_name="gemini-2.0-flash", temperature=0)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
tokenizer = tiktoken.get_encoding("cl100k_base")
sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

# Constants
MAX_CONTEXT_TOKENS = 1000000
TARGET_CHUNK_SIZE = 1500  # In tokens
CHUNK_OVERLAP = 150     # In tokens
SAFETY_BUFFER = 0.90

# Qdrant connection
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "shorts-resources"

class BookTags(BaseModel):
    """Model for book tags with validation"""
    tags: List[str] = Field(
        ...,
        description="List of 3-5 relevant tags for the book",
        min_items=2,
        max_items=5,
        example=["behavioralPsychology", "relationships"]
    )

def print_status(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_memory():
    """Check and log memory usage"""
    mem = psutil.virtual_memory()
    print_status(f"Memory usage: {mem.percent}% (Free: {mem.available/1024/1024:.2f}MB)")
    if mem.percent > 90:
        gc.collect()

def initialize_qdrant() -> QdrantVectorStore:
    """Initialize Qdrant with hybrid search support"""
    print_status("Initializing Qdrant connection...")
    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=120
        )
        
        # Check if collection exists, create if not with proper configuration
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if COLLECTION_NAME not in collection_names:
            print_status(f"Creating new collection: {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "dense": VectorParams(
                        size=768,  # Size of Google's embedding-001
                        distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                }
            )
            
            # Create required index for filtering
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.source",
                field_schema="keyword"
            )
            
            print_status(f"Created collection with hybrid search support")
        else:
            print_status(f"Using existing collection: {COLLECTION_NAME}")
        
        # Initialize vector store
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
            sparse_embedding=sparse_embeddings,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="sparse"
        )
        
        print_status("Qdrant initialized with hybrid search support")
        return vector_store
    except Exception as e:
        print_status(f"Failed to initialize Qdrant: {str(e)}")
        raise

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF with memory optimization"""
    print_status(f"Extracting text from {os.path.basename(pdf_path)}...")
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
                # Clear memory after each page
                if psutil.virtual_memory().percent > 85:
                    gc.collect()
        print_status(f"Extracted {len(text.split())} words")
        return text
    except Exception as e:
        print_status(f"Error extracting PDF: {str(e)}")
        raise

def create_text_splitter() -> RecursiveCharacterTextSplitter:
    """Create a text splitter configured for semantic chunking"""
    return RecursiveCharacterTextSplitter(
        chunk_size=TARGET_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=lambda text: len(tokenizer.encode(text)),
        separators=["\n\n", "\n", " ", ""],
        is_separator_regex=False
    )

async def enrich_chunk(full_text: str, chunk_text: str, chunk_num: int, total_chunks: int) -> str:
    """Generate context explanation with token safety"""
    print_status(f"Processing chunk {chunk_num}/{total_chunks}")
    try:
        chunk_tokens = len(tokenizer.encode(chunk_text))
        available_tokens = int(MAX_CONTEXT_TOKENS * SAFETY_BUFFER) - chunk_tokens - 500
        
        truncated_context = safe_truncate(full_text, available_tokens)
        
        prompt = f"""
        DOCUMENT CONTEXT (truncated to {available_tokens} tokens):
        {truncated_context}
        
        ---
        CURRENT CHUNK:
        {chunk_text}
        
        Provide concise context (1-2 sentences):
        1. This chunk's role in the complete work
        2. Key connections to other sections
        3. Important details from adjacent sections

        Output in one concise paragraph.
        """
        response = await llm.ainvoke(prompt)
        return response.content.strip()
    except Exception as e:
        print_status(f"Error enriching chunk: {str(e)}")
        raise

async def process_text_to_chunks(full_text: str, filename: str) -> List[Dict]:
    """Convert text to semantic chunks with memory management"""
    print_status(f"Processing text from {filename}...")
    try:
        text_splitter = create_text_splitter()
        chunks = []
        
        # First split into documents using the text splitter
        documents = text_splitter.create_documents([full_text])
        
        # Process each chunk with context enrichment
        for i, doc in enumerate(tqdm(documents, desc="Processing chunks")):
            chunk_num = i + 1
            chunk_text = doc.page_content
            
            # Process chunks in smaller batches
            if len(chunks) % 10 == 0:
                gc.collect()
                
            context = await enrich_chunk(full_text, chunk_text, chunk_num, len(documents))
            
            chunks.append({
                "text": chunk_text,
                "context": context,
                "token_count": len(tokenizer.encode(chunk_text)),
                "source": filename,
                "chunk_num": chunk_num
            })
        
        print_status(f"Processed {len(chunks)} semantic chunks")
        return chunks
    except Exception as e:
        print_status(f"Error processing chunks: {str(e)}")
        raise

def safe_truncate(text: str, max_tokens: int) -> str:
    """Token-aware truncation preserving sentence boundaries"""
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text
    
    # Decode back to text but only up to max_tokens
    truncated = tokenizer.decode(tokens[:max_tokens])
    
    # Find the last natural boundary in the truncated text
    last_boundary = max(
        truncated.rfind("."),
        truncated.rfind("?"),
        truncated.rfind("!"),
        truncated.rfind("\n\n"),  # Paragraph break
        truncated.rfind("\n"),    # Line break
        truncated.rfind(" "),     # Word boundary
        0  # Fallback to start if no boundaries found
    )
    
    # Return up to the boundary if found, otherwise return truncated
    return truncated[:last_boundary + 1] if last_boundary > 0 else truncated


async def generate_book_metadata(full_text: str, filename: str) -> Tuple[str, List[str]]:
    """Generate summary and validated tags for the book"""
    print_status(f"Generating metadata for {filename}...")
    try:
        summary_prompt = f"""
        Book Content (truncated):
        {safe_truncate(full_text, 1000000)}
        
        Generate a comprehensive 3-4 sentence summary of this book that captures:
        1. The main themes and arguments
        2. The author's perspective
        3. Key takeaways
        """
        summary = (await llm.ainvoke(summary_prompt)).content.strip()

        tag_prompt = f"""
        Analyze this book content and assign 2-3 relevant tags from these domains:
        - Psychology (behavioral, cognitive, social)
        - Relationships (dating, marriage, communication)
        - Self-Improvement (productivity, habits, mindset)
        - Business (leadership, entrepreneurship, management)
        - Health (nutrition, mentalHealth, fitness)
        - Other relevant domains
        
        Book Summary:
        {summary}
        """
        
        tags_result = await llm.with_structured_output(BookTags).ainvoke(tag_prompt)
        print_status(f"Generated metadata for {filename}")
        return summary, tags_result.tags
    except Exception as e:
        print_status(f"Error generating metadata: {str(e)}")
        return "No summary available", []

async def process_book(filepath: str, vector_store: QdrantVectorStore) -> Dict:
    """Process a single book with memory optimization"""
    filename = os.path.basename(filepath)
    print_status(f"\n=== Processing {filename} ===")
    
    try:
        full_text = extract_text_from_pdf(filepath)
        summary, tags = await generate_book_metadata(full_text, filename)
        chunks = await process_text_to_chunks(full_text, filename)
        
        # Process documents in smaller batches
        batch_size = 5
        for i in tqdm(range(0, len(chunks), batch_size), desc="Storing chunks"):
            batch = chunks[i:i + batch_size]
            documents = []
            
            for chunk in batch:
                documents.append(Document(
                    page_content=chunk["text"],
                    metadata={
                        "source": filename,
                        "context": chunk["context"],
                        "book_summary": summary,
                        "tags": tags,
                        "chunk_index": chunk["chunk_num"],
                        "total_chunks": len(chunks),
                        "processed_at": datetime.now().isoformat()
                    }
                ))
            
            # Add documents in batches
            uuids = [str(uuid.uuid4()) for _ in range(len(documents))]
            vector_store.add_documents(documents=documents, ids=uuids)
            
            # Clear memory between batches
            del documents
            gc.collect()
        
        return {
            "filename": filename,
            "summary": summary,
            "tags": tags,
            "total_chunks": len(chunks),
            "processed_at": datetime.now().isoformat()
        }
    except Exception as e:
        print_status(f"Error processing book {filename}: {str(e)}")
        raise

def is_file_processed(directory: str, filename: str) -> bool:
    """Check if a file has already been processed"""
    meta_file = os.path.join(directory, "metadata_json", f"{filename}.meta.json")
    return os.path.exists(meta_file)

async def process_pdf_directory(directory: str = "my_test_files") -> None:
    """Full processing pipeline with error recovery"""
    print_status("Starting pipeline")
    vector_store = initialize_qdrant()
    
    try:
        os.makedirs(os.path.join(directory, "metadata_json"), exist_ok=True)
        pdf_files = [f for f in os.listdir(directory) if f.endswith(".pdf")]
        print_status(f"Found {len(pdf_files)} PDFs to process")
        
        for filename in tqdm(pdf_files, desc="Processing PDFs"):
            if is_file_processed(directory, filename):
                print_status(f"Skipping already processed file: {filename}")
                continue
                
            filepath = os.path.join(directory, filename)
            try:
                check_memory()
                book_data = await process_book(filepath, vector_store)
                
                with open(os.path.join(directory, "metadata_json", f"{filename}.meta.json"), "w") as f:
                    json.dump({
                        "summary": book_data["summary"],
                        "tags": book_data["tags"],
                        "chunk_count": book_data["total_chunks"],
                        "processed_at": book_data["processed_at"]
                    }, f, indent=2)
                
                print_status(f"Successfully processed and stored: {filename}")
            except Exception as e:
                print_status(f"Error processing {filename}: {str(e)}")
                continue
                
    except Exception as e:
        print_status(f"Pipeline error: {str(e)}")
        raise
    finally:
        print_status("Pipeline finished")


class TopicVectorStore:
    def __init__(self, embeddings, qdrant_url: str, api_key: str, collection_name: str = "psychology-topic-cache"):
        self.embeddings = embeddings
        self.collection_name = collection_name
        self.vector_name = "dense"

        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=api_key,
        )

        # Create collection if it doesn't exist
        if not self.qdrant_client.collection_exists(collection_name):
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config={self.vector_name: VectorParams(size=768, distance=Distance.COSINE)}
            )

        # Ensure proper LangChain QdrantVectorStore init with named vector
        self.store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
            vector_name=self.vector_name
        )

    async def add_concept(self, insight: BaseModel):
        content = f"{insight.explanation} | {insight.psychological_effect}"
        doc = Document(
            page_content=content,
            metadata={
                "title": insight.concept_title,
                "timestamp": datetime.now().isoformat(),
                "raw_data": insight.model_dump()
            }
        )
        await self.store.aadd_documents([doc], ids=[str(uuid4())])

    async def is_duplicate(self, insight: BaseModel, threshold: float = 0.85) -> Tuple[bool, Optional[str]]:
        query = f"{insight.explanation.strip()} | {insight.psychological_effect.strip()}"
        result = await self.store.asimilarity_search_with_score(query, k=1)
        if not result:
            return False, None
        doc, score = result[0]
        print(f"\nSIMILARITY WITH PREVIOUS TITLES: {score}\n")
        return score >= threshold, doc.metadata.get("title")


topic_store = TopicVectorStore(
    embeddings=embeddings,
    qdrant_url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    collection_name="psychology-topic-cache"
)

# if __name__ == "__main__":
#     asyncio.run(process_pdf_directory())