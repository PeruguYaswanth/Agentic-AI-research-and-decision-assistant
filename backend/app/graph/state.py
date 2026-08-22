from typing import TypedDict, List, Dict, Any, Optional

class ResearchState(TypedDict):
    question: str
    conversation_id: str
    session_id: str
    plan: List[str]
    current_step: str

    freshness_category: str  # REAL_TIME, TIME_SENSITIVE, STABLE_KNOWLEDGE, MIXED
    current_datetime_str: str

    requires_web_search: bool
    requires_rag: bool
    is_factual: bool
    is_comparison: bool
    task_type: str  # comparison, factual, rag_only, hybrid, direct

    web_queries: List[str]
    web_results: List[Dict[str, Any]]

    retrieved_documents: List[Dict[str, Any]]

    analysis: str
    key_findings: List[str]
    claims: List[Dict[str, Any]]
    conflicts_detected: List[str]

    confidence_level: str  # HIGH, MEDIUM, LOW
    confidence_reason: str

    validation_result: str  # "PASS" or "FAIL"
    validation_feedback: str
    missing_information: List[str]

    sources: List[Dict[str, Any]]

    iteration_count: int
    max_iterations: int

    final_answer: str
    execution_logs: List[Dict[str, Any]]
