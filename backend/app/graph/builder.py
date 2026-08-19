import logging
from langgraph.graph import StateGraph, START, END
from app.graph.state import ResearchState
from app.graph.nodes import (
    analyze_question_node,
    create_plan_node,
    orchestrator_node,
    web_research_node,
    rag_retrieval_node,
    analysis_node,
    validator_node,
    final_answer_node
)

logger = logging.getLogger(__name__)

def route_after_orchestrator(state: ResearchState) -> str:
    requires_web = state.get("requires_web_search", True)
    requires_rag = state.get("requires_rag", False)
    current_step = state.get("current_step", "")

    # Check if web research has been executed yet
    has_web_run = any(log.get("step_name") == "Web Research Agent" for log in state.get("execution_logs", []))
    has_rag_run = any(log.get("step_name") == "RAG Retrieval Agent" for log in state.get("execution_logs", []))

    if requires_web and not has_web_run:
        return "web_research"
    elif requires_rag and not has_rag_run:
        return "rag_retrieval"
    else:
        return "analysis"

def route_after_web_research(state: ResearchState) -> str:
    requires_rag = state.get("requires_rag", False)
    has_rag_run = any(log.get("step_name") == "RAG Retrieval Agent" for log in state.get("execution_logs", []))

    if requires_rag and not has_rag_run:
        return "rag_retrieval"
    return "analysis"

def route_after_validator(state: ResearchState) -> str:
    result = state.get("validation_result", "PASS")
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    if result == "FAIL" and iteration < max_iterations:
        logger.info(f"Validator failed on iteration {iteration}. Routing back to Orchestrator for additional research loop.")
        return "orchestrator"
    
    return "final_answer"

def build_research_graph():
    builder = StateGraph(ResearchState)

    # Add Nodes
    builder.add_node("analyze_question", analyze_question_node)
    builder.add_node("create_plan", create_plan_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("web_research", web_research_node)
    builder.add_node("rag_retrieval", rag_retrieval_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("validator", validator_node)
    builder.add_node("final_answer", final_answer_node)

    # Add Edges
    builder.add_edge(START, "analyze_question")
    builder.add_edge("analyze_question", "create_plan")
    builder.add_edge("create_plan", "orchestrator")

    # Conditional edge from Orchestrator
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "web_research": "web_research",
            "rag_retrieval": "rag_retrieval",
            "analysis": "analysis"
        }
    )

    # Conditional edge from Web Research
    builder.add_conditional_edges(
        "web_research",
        route_after_web_research,
        {
            "rag_retrieval": "rag_retrieval",
            "analysis": "analysis"
        }
    )

    # Direct edge from RAG to Analysis
    builder.add_edge("rag_retrieval", "analysis")

    # Direct edge from Analysis to Validator
    builder.add_edge("analysis", "validator")

    # Conditional edge from Validator (Feedback Loop!)
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "orchestrator": "orchestrator",
            "final_answer": "final_answer"
        }
    )

    builder.add_edge("final_answer", END)

    graph = builder.compile()
    return graph
