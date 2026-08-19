import pytest
from app.graph.state import ResearchState
from app.graph.builder import route_after_orchestrator, route_after_validator, build_research_graph

def test_route_orchestrator_to_web():
    state: ResearchState = {
        "question": "FastAPI vs Django",
        "conversation_id": "test",
        "session_id": "test",
        "plan": ["Research frameworks"],
        "current_step": "orchestrator",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": True,
        "task_type": "comparison",
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
    next_node = route_after_orchestrator(state)
    assert next_node == "web_research"

def test_route_orchestrator_to_rag_only():
    state: ResearchState = {
        "question": "Analyze uploaded requirements",
        "conversation_id": "test",
        "session_id": "test",
        "plan": ["Retrieve docs"],
        "current_step": "orchestrator",
        "requires_web_search": False,
        "requires_rag": True,
        "is_factual": True,
        "is_comparison": False,
        "task_type": "rag_query",
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
    next_node = route_after_orchestrator(state)
    assert next_node == "rag_retrieval"

def test_route_validator_pass():
    state: ResearchState = {
        "question": "FastAPI vs Django",
        "conversation_id": "test",
        "session_id": "test",
        "plan": [],
        "current_step": "validator",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": True,
        "task_type": "comparison",
        "web_queries": [],
        "web_results": [],
        "retrieved_documents": [],
        "analysis": "Valid comprehensive analysis",
        "validation_result": "PASS",
        "validation_feedback": "Looks good",
        "missing_information": [],
        "sources": [{"title": "FastAPI Docs", "url": "https://fastapi.tiangolo.com", "source": "web"}],
        "iteration_count": 1,
        "max_iterations": 3,
        "final_answer": "",
        "execution_logs": []
    }
    next_node = route_after_validator(state)
    assert next_node == "final_answer"
