import pytest
from app.graph.builder import build_research_graph
from app.graph.state import ResearchState

def test_e2e_langgraph_workflow():
    graph = build_research_graph()

    initial_state: ResearchState = {
        "question": "What are the latest important changes in LangGraph that I should know before building a production agent?",
        "conversation_id": "test-e2e-conv",
        "session_id": "test-e2e-sess",
        "plan": [],
        "current_step": "init",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": False,
        "task_type": "factual",
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

    final_state = graph.invoke(initial_state)

    assert final_state["current_step"] == "final_answer"
    assert len(final_state["plan"]) > 0
    assert len(final_state["web_results"]) > 0
    assert len(final_state["sources"]) > 0
    assert final_state["validation_result"] == "PASS"
    assert len(final_state["final_answer"]) > 100
    assert len(final_state["execution_logs"]) >= 6
