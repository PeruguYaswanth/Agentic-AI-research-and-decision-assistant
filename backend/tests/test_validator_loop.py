import pytest
from app.graph.state import ResearchState
from app.graph.builder import route_after_validator
from app.graph.nodes import validator_node

def test_validator_retry_loop():
    # Iteration 0 with FAIL status should loop back to orchestrator
    state: ResearchState = {
        "question": "FastAPI vs Django for AI",
        "conversation_id": "test",
        "session_id": "test",
        "plan": [],
        "current_step": "analysis",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": True,
        "task_type": "comparison",
        "web_queries": [],
        "web_results": [],
        "retrieved_documents": [],
        "analysis": "Too short",  # triggers failure rule
        "validation_result": "",
        "validation_feedback": "",
        "missing_information": [],
        "sources": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "final_answer": "",
        "execution_logs": []
    }
    
    val_result = validator_node(state)
    assert val_result["validation_result"] == "FAIL"
    assert val_result["iteration_count"] == 1
    
    state.update(val_result)
    next_step = route_after_validator(state)
    assert next_step == "orchestrator"

def test_validator_max_iterations_prevention():
    # When reaching max iterations, validator should gracefully proceed to final answer
    state: ResearchState = {
        "question": "FastAPI vs Django",
        "conversation_id": "test",
        "session_id": "test",
        "plan": [],
        "current_step": "analysis",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": True,
        "task_type": "comparison",
        "web_queries": [],
        "web_results": [],
        "retrieved_documents": [],
        "analysis": "Short",
        "validation_result": "",
        "validation_feedback": "",
        "missing_information": [],
        "sources": [],
        "iteration_count": 2,  # 3rd iteration
        "max_iterations": 3,
        "final_answer": "",
        "execution_logs": []
    }
    
    val_result = validator_node(state)
    assert val_result["validation_result"] == "PASS"
    
    state.update(val_result)
    next_step = route_after_validator(state)
    assert next_step == "final_answer"
