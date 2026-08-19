# Agentic AI Research & Decision Assistant

A full-stack, autonomous **Agentic AI Research & Decision Assistant** built with **LangGraph**, **LangChain**, **FastAPI**, **ChromaDB**, **Tavily**, **Next.js 14**, and **Tailwind CSS**.

The system accepts complex technical and strategic questions, autonomously formulates multi-step research plans, queries external web APIs and internal uploaded documents (RAG), synthesizes findings, runs strict self-validation loops, and generates citation-grounded decision reports.

---

## 1. Architecture Overview

```
                          User Question
                                ↓
                        LangGraph Engine
                                ↓
                    [Node 1: Question Analyzer]
                                ↓
                       [Node 2: Planner]
                                ↓
                     [Node 3: Orchestrator]
                                ↓
                 ┌──────────────┴──────────────┐
                 ↓                             ↓
     [Node 4: Web Research]          [Node 5: RAG Retrieval]
          (Tavily API)                 (ChromaDB Local)
                 │                             │
                 └──────────────┬──────────────┘
                                ↓
                      [Node 6: Analysis]
                                ↓
                     [Node 7: QA Validator]
                                ↓
                    Is Evidence Sufficient?
                        /             \
                   [FAIL]             [PASS]
                     ↓                   ↓
             (Increment Loop)    [Node 8: Final Answer]
                     ↓                   ↓
              [Orchestrator]           [END]
```

### Core Architecture Components

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| **Orchestration & State** | **LangGraph** | Cyclic state graphs, conditional routing, loop iterations, self-validation |
| **Agent Integrations** | **LangChain** | LLM wrappers, document loaders, text splitters, retriever tools |
| **Web Research Engine** | **Tavily Search API** | Live search queries, snippet parsing, authoritative external sources |
| **Vector Storage (RAG)** | **ChromaDB** | Local persistence, recursive chunking, cosine similarity search |
| **Relational Database** | **SQLite (Async)** | Sessions, message logs, document metadata, source citations |
| **Backend API** | **FastAPI** | REST API endpoints & Server-Sent Events (SSE) live streaming |
| **Frontend UI** | **Next.js 14 / Tailwind** | Responsive dashboard, real-time agent timeline, sources drawer, RAG upload |

---

## 2. Why LangChain vs. Why LangGraph?

### Why LangChain?
- **Tool Standardizations**: Connects heterogeneous tools (`WebSearchTool`, `RAGRetrieverTool`) with standardized schemas.
- **Document Ingestion**: Provides `PyPDFLoader`, `TextLoader`, and `RecursiveCharacterTextSplitter` out of the box.
- **Provider Abstraction**: Allows seamless swapping between OpenAI, Anthropic, or local LLMs without modifying business logic.

### Why LangGraph?
- **Cyclic Agentic Feedback Loops**: Unlike linear chains (`A -> B -> C`), LangGraph supports cycles (`Validator -> FAIL -> Orchestrator -> Research -> Validator`).
- **Shared State Management**: The entire research journey (`plan`, `web_results`, `retrieved_documents`, `validation_feedback`, `execution_logs`) is preserved in a typed `ResearchState`.
- **Conditional Branching**: The orchestrator dynamically routes to Web Research, RAG, or Hybrid paths based on query analysis.
- **Controlled Iterations**: Enforces `max_iterations` boundaries to eliminate infinite loops.

---

## 3. Web Research vs. Internal Document RAG

| Attribute | Web Research (Tavily) | Internal RAG (ChromaDB) |
| :--- | :--- | :--- |
| **Information Scope** | Public internet, latest framework releases, technical benchmarks | User-uploaded PDFs, internal project specifications, private notes |
| **Trigger Criteria** | Queries asking for recent updates, comparisons, or general facts | Queries referencing "uploaded files", "requirements", "internal docs" |
| **Grounding Citations** | Clickable URLs (`https://...`) with web page titles | Document filenames with exact Page Numbers (`doc.pdf (Page 2)`) |

The **Orchestrator** dynamically selects:
1. `Web Only`: For general comparisons and latest framework news.
2. `RAG Only`: For questions strictly referencing uploaded project files.
3. `Hybrid (Web + RAG)`: For questions comparing external technologies against internal constraints.

---

## 4. Preset Demonstration Scenarios

### Scenario 1: Architecture Comparison (FastAPI vs Django)
- **Query**: *"Should I use FastAPI or Django for building an AI-powered resume screening application?"*
- **Execution**: Analyzer triggers comparison mode → Planner formulates benchmarks → Web research queries async performance and AI integration → Analysis compares concurrency & Pydantic vs Django ORM → Validator verifies evidence → Final recommendation produced.

### Scenario 2: Internal Document Decision (ChromaDB vs FAISS)
- **Query**: *"Based on my uploaded project requirements, should I use ChromaDB or FAISS for my RAG application?"*
- **Execution**: Analyzer detects uploaded document dependency → RAG agent retrieves requirement chunks from ChromaDB → Analysis compares metadata filtering and persistence constraints → Validator checks alignment → Grounded decision produced.

### Scenario 3: Latest Framework Updates (LangGraph Changes)
- **Query**: *"What are the latest important changes in LangGraph that I should know before building a production agent?"*
- **Execution**: Web research agent retrieves release features → Validator checks freshness → Final answer provides structured changelog with source URLs.

---

## 5. Getting Started

### Prerequisites
- Python 3.10+ (Python 3.11 / 3.12 / 3.14 supported)
- Node.js 18+ & npm
- (Optional) Docker & Docker Compose

### 1. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Edit `backend/.env` with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./research_assistant.db
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

> **Note on API Keys**: If `OPENAI_API_KEY` or `TAVILY_API_KEY` are not set, the system seamlessly uses high-quality offline simulation engines and deterministic mock embeddings so development and testing can proceed without interruption.

Run the FastAPI backend server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend will run on `http://127.0.0.1:8000` with Swagger docs available at `http://127.0.0.1:8000/docs`.

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## 6. Running with Docker Compose

To launch the full application with a single command:

```bash
docker-compose up --build
```

---

## 7. Running Backend Tests

The backend includes a comprehensive `pytest` test suite:

```bash
cd backend
.venv\Scripts\pytest tests/ -v
```

### Test Coverage:
- `test_question_analyzer.py`: Query classification (comparison, factual, RAG vs Web).
- `test_graph_routing.py`: Conditional edge routing and orchestrator branching.
- `test_validator_loop.py`: Self-validation failure loops and max iteration guardrails.
- `test_rag_pipeline.py`: File ingestion, chunking, ChromaDB vector indexing, and similarity retrieval.
- `test_api_endpoints.py`: REST `/api/chat`, `/health`, and `/api/research/history` endpoints.
- `test_e2e_research.py`: Full end-to-end LangGraph StateGraph execution.

---

## 8. API Reference

- `POST /api/chat`: Runs research graph and returns full JSON response.
- `POST /api/research/stream`: Server-Sent Events (SSE) real-time agent status streaming.
- `POST /api/documents/upload`: Uploads and indexes PDF/TXT/MD into ChromaDB.
- `GET /api/documents`: Lists indexed documents with chunk metadata.
- `DELETE /api/documents/{id}`: Deletes document metadata and ChromaDB vector chunks.
- `GET /api/research/history`: Lists all past research sessions.
- `GET /api/research/{session_id}`: Returns complete session details, plan, execution logs, and citations.

---

## 9. Known Limitations & Future Improvements

1. **Multi-Modal Document Parsing**: Current RAG processes text and PDFs; future versions can incorporate OCR for scanned handwritten tables and images.
2. **Multi-Model Orchestration**: Support mixing different models (e.g. Claude 3.5 Sonnet for analysis, GPT-4o-mini for routing).
3. **Persistent User Auth**: Integrate JWT authentication / PostgreSQL multi-tenant tenancy.
