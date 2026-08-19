import pytest
from app.graph.state import ResearchState
from app.graph.nodes import analyze_question_node

def test_analyze_comparison_question():
    state: ResearchState = {
        "question": "Should I use FastAPI or Django for building an AI-powered resume screening application?",
        "conversation_id": "test-conv-1",
        "session_id": "test-sess-1",
        "plan": [],
        "current_step": "init",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": False,
        "task_type": "",
        "web_queries": [],
        "web_results": [],
        "retrieved_documents": [],
        "analysis": "",
        "validation_result": "",
        "validation_feedback": "",
        "missing_information": [],
        "sources": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "final_answer": "",
        "execution_logs": []
    }
    
    result = analyze_question_node(state)
    assert result["requires_web_search"] is True
    assert result["is_comparison"] is True
    assert result["task_type"] == "comparison"
    assert len(result["execution_logs"]) == 1

def test_analyze_rag_question():
    state: ResearchState = {
        "question": "Based on my uploaded project requirements, should I use ChromaDB or FAISS for my RAG application?",
        "conversation_id": "test-conv-2",
        "session_id": "test-sess-2",
        "plan": [],
        "current_step": "init",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": False,
        "task_type": "",
        "web_queries": [],
        "web_results": [],
        "retrieved_documents": [],
        "analysis": "",
        "validation_result": "",
        "validation_feedback": "",
        "missing_information": [],
        "sources": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "final_answer": "",
        "execution_logs": []
    }
    
    result = analyze_question_node(state)
    assert result["requires_rag"] is True
