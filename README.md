---

# Short Video Generation Project

This project automates the comprehensive workflow for generating short-form videos, suitable for platforms such as YouTube Shorts. It encompasses content ideation, script generation, multimedia asset acquisition, video post-production, and direct platform uploading, leveraging AI models and an integrated LangGraph framework.

This project uses Youtube v3 API, for which we need to create a GCP project.

---

## Key Features

* **AI-Driven Content Generation**: Facilitates the automated creation of psychological short video scripts, including conceptual outlines, detailed explanations, and real-world applications.
* **Text-to-Speech (TTS) Synthesis**: Converts textual script content into natural-sounding audio narration.
* **Dynamic Video Asset Integration**: Acquires and intelligently selects royalty-free stock footage from Pexels, aligning visual elements with specific script segments.
* **Automated Video Production**: Utilizes `ffmpeg` for professional-grade video editing, incorporating scene transitions, background music integration with dynamic audio ducking, and precise timing.
* **Advanced Captioning**: Implements synchronized, highlighted captions to enhance video accessibility and viewer engagement.
* **Platform Upload Automation**: Automates the upload process to YouTube, including comprehensive metadata management (title, description, tags).
* **Configurable Workflow Management**: Employs LangGraph to establish a flexible, stateful video creation pipeline, supporting scalability and iterative development.
* **Qdrant Database Integration**: Manages the storage and retrieval of processed document chunks and maintains a cache of generated psychological topics, ensuring content relevance and topic uniqueness.

---

## 🎬 Example Shorts

### 🧠 The Empath Trap  
[![Watch the video](https://img.youtube.com/vi/XTygk1vQ-FQ/0.jpg)](https://youtube.com/shorts/XTygk1vQ-FQ?si=HiOvHXto6hF8cdpg)

### 🕳️ The Void Gambit  
[![Watch the video](https://img.youtube.com/vi/_q7XlsYr-uw/0.jpg)](https://youtube.com/shorts/_q7XlsYr-uw?si=TNJ3wBEXxirtnoR_)

➡️ **[See all videos on our YouTube Shorts channel](https://www.youtube.com/@the_inner_lab/shorts)**


---

## Project Architecture

The project's functionality is distributed across several Python modules, each serving a distinct purpose:

* **`main.py`**: Acts as the central orchestrator, initializing the LangGraph workflow, global components (e.g., `VideoCaptioner`, AI models), defining the graph's nodes and edges, and managing persistent state via a PostgreSQL checkpointer.
* **`configuration.py`**: Centralizes all configurable parameters pertaining to AI agents and the media pipeline, including settings for embedding models, reranking models, language models, and prompt definitions.
* **`state.py`**: Defines the data structures that collectively represent the comprehensive state of the LangGraph workflow, facilitating information flow between different processing nodes.
* **`structures.py`**: Contains **Pydantic models** that enforce data integrity and validation for various data types, such as `VideoScript`, `VideoMetadata`, `AudioMetadata`, `FinalOutput`, and `PsychologyShort`.
* **`utils.py`**: Provides a collection of utility functions supporting common operations, including message parsing, chat model loading, script conversion, Pexels data extraction, video duration retrieval, and filename sanitization.
* **`handle_kokoro.py`**: Manages **Text-to-Speech (TTS) generation** using the `kokoro_onnx` and `misaki` libraries, producing WAV audio files for narration.
* **`pexels_handler.py`**: Interfaces with the **Pexels API** to search for and download relevant stock videos, incorporating retry mechanisms and relevance validation.
* **`video_editor.py`**: Contains the core **video editing logic**, leveraging `ffmpeg` to assemble video segments, apply transitions, synchronize with audio, and prepare final video reels.
* **`handle_captions.py`**: Responsible for **generating and embedding captions** into videos, utilizing `faster_whisper` for transcription and `moviepy` for visual integration.
* **`handle_bensound_free.py`**: Implements a **web scraper for Bensound.com** to acquire royalty-free background music and integrates audio ducking functionalities via `ffmpeg`.
* **`handle_shorts_upload.py`**: Manages the **YouTube video upload process**, including OAuth2 authentication, metadata submission, and error handling with retry logic.
* **`qdrant_db.py`**: Manages the **Qdrant vector database**, facilitating the indexing of PDF documents into semantic chunks, metadata generation, and supporting hybrid retrieval. It also maintains a cache for generated topics to prevent redundancy.
* **`retrievel.py`**: Configures and operates the **hybrid retrieval system** from the Qdrant database, employing both dense and sparse embeddings (BM25) and supporting Maximal Marginal Relevance (MMR) for diverse and relevant search results.

---

## Environment Variables

The project relies on the following environment variables for configuration. These should be defined in a `.env` file located in the project's root directory, with placeholder values replaced by actual credentials and paths.

```env
# LangSmith Tracing for observability
LANGSMITH_PROJECT='short-creation'
LANGSMITH_TRACING='true'
LANGSMITH_API_KEY='your_langsmith_api_key'

## Large Language Model (LLM) Service API Keys
DEEPSEEK_API_KEY='your_deepseek_api_key'

## Vector Database Configuration (Qdrant)
QDRANT_API_KEY='your_qdrant_api_key'
QDRANT_URL='your_qdrant_url'

PEXELS_API_KEY='your_pexels_api_key'

# Base Paths for Video Assets and Outputs
BASE_VIDEOS_PATH="/path/to/your/my_test_files/videos/"
OUTPUT_DIR_BASE="/path/to/your/my_test_files/output_reels_fades_ordered_v3"
BASE_SCRIPT_PATH= "/path/to/your/my_test_files/script_texts"

# Font Path for Captions
CAPTIONS_FONT_PATH = '/path/to/your/fonts/Cal_Sans,Inter/Inter/static/Inter_28pt-ExtraBold.ttf'

# General Project Base Path
BASE_PATH = "/path/to/your/my_test_files"

# Kokoro TTS Model Paths
KOKORO_VOICES_PATH = "/path/to/your/kokoro_files/voices-v1.0.bin"
KOKORO_MODEL_PATH = "/path/to/your/kokoro_files/kokoro.onnx"

# Background Music Path
BACKGROUND_MUSIC_PATH = '/path/to/your/my_test_files/background_music'

# Tavily API Key for External Search
TAVILY_API_KEY="your_tavily_api_key"

# PostgreSQL Checkpointer URI for LangGraph State Management
DB_URI_CHECKPOINTER = "postgresql://user:password@localhost:5432/short_creation_checkpointer?sslmode=disable"

# YouTube API Credentials for Video Upload
YOUTUBE_API_KEY = 'your_youtube_api_key'
GOOGLE_CLIENT_SECRET = 'your_google_client_secret_value'
GOOGLE_CLIENT_ID = 'your_google_client_id'
GOOGLE_CLIENT_SECRET_PATH = '/path/to/your/google_client_secret.json'

# YouTube Authentication and Cookies Paths
PROJECT_BASE_PATH = '/path/to/your/project_base_directory'
YOUTUBE_COOKIES_PATH = '/path/to/your/channel_kit/youtube_cookies.json'
YOUTUBE_AUTH_JSON = '/path/to/your/youtube-oauth2.json'
```


## Future Development

* **Research Graph Integration**: Future enhancements include integrating a dedicated "research graph" to autonomously gather and synthesize information from the Qdrant database, thereby informing and enriching the topic and script generation processes.
* **Expanded Transition Effects**: Diversification of video transition effects beyond basic fades.
* **Advanced Audio Engineering**: Implementation of more sophisticated audio effects and mixing capabilities.
* **Modular Asset Management**: Improvements to asset management systems for streamlined updating and interchangeability of multimedia components.
* **User Interface Development**: Introduction of a user-friendly interface (e.g., web-based or command-line) for enhanced interaction and workflow monitoring.
* **Scalability Optimizations**: Further optimization for high-volume, concurrent video processing.

