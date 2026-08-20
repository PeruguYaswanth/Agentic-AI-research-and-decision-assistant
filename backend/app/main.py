from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.history import router as history_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on startup
    await init_db()
    yield

app = FastAPI(
    title="Agentic AI Research & Decision Assistant API",
    description="Backend API powered by LangGraph, LangChain, ChromaDB, and Tavily for multi-step agentic research.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import APIRouter
from app.schemas.research import RAGQueryResponse
from app.api.documents import query_documents

# Register Routers
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(history_router)

# RAG Knowledge Base router alias
rag_router = APIRouter(prefix="/api/rag", tags=["RAG Knowledge Base"])
rag_router.add_api_route("/query", query_documents, methods=["POST"], response_model=RAGQueryResponse)
app.include_router(rag_router)

@app.get("/health", tags=["Health"])

async def health_check():
    return {
        "status": "healthy",
        "service": "Agentic AI Research & Decision Assistant",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
