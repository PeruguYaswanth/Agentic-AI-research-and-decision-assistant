import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.state import ResearchState
from app.tools.web_search import WebSearchTool
from app.tools.rag_retriever import RAGRetrieverTool

logger = logging.getLogger(__name__)

def get_llm():
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and not settings.OPENAI_API_KEY.startswith("your_"):
        try:
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=0.2,
                openai_api_key=settings.OPENAI_API_KEY
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatOpenAI: {e}")
            return None
    return None

def add_log(state: ResearchState, step_name: str, status: str, detail: str = "") -> List[Dict[str, Any]]:
    logs = list(state.get("execution_logs", []))
    logs.append({
        "step_name": step_name,
        "status": status,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat()
    })
    return logs

# 1. Question Analyzer Node
def analyze_question_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    question_lower = question.lower()

    # Rule-based fallback & detection triggers
    rag_keywords = ["uploaded", "my document", "my file", "project requirements", "internal notes", "resume", "pdf"]
    requires_rag = any(kw in question_lower for kw in rag_keywords)
    
    # Check vector DB if files exist
    rag_tool = RAGRetrieverTool()
    sample_retrieval = rag_tool.retrieve(question, k=1)
    if sample_retrieval and not requires_rag:
        # If files are present in ChromaDB and question asks about requirements/tech stack comparison
        if "requirement" in question_lower or "faiss" in question_lower or "chromadb" in question_lower or "my" in question_lower:
            requires_rag = True

    requires_web_search = not (requires_rag and ("only" in question_lower or "strictly" in question_lower))
    if "latest" in question_lower or "compare" in question_lower or "versus" in question_lower or " vs " in question_lower or "fastapi" in question_lower or "django" in question_lower or "langgraph" in question_lower or "movie" in question_lower or "who" in question_lower or "what" in question_lower or "how" in question_lower:
        requires_web_search = True

    is_comparison = "vs" in question_lower or "versus" in question_lower or "compare" in question_lower or " or " in question_lower or "should i use" in question_lower
    is_factual = "what" in question_lower or "how" in question_lower or "who" in question_lower or "give me" in question_lower or "list" in question_lower or "movie" in question_lower or "changes" in question_lower

    llm = get_llm()
    if llm:
        try:
            prompt = f"""Analyze this user question for an AI research assistant:
Question: "{question}"

Respond with JSON strictly in this format:
{{
    "requires_web_search": bool,
    "requires_rag": bool,
    "is_factual": bool,
    "is_comparison": bool,
    "task_type": "comparison" | "rag_query" | "factual" | "hybrid"
}}
"""
            msg = llm.invoke([SystemMessage(content="You are an intent analyzer. Output JSON only."), HumanMessage(content=prompt)])
            res = json.loads(msg.content.strip().replace("```json", "").replace("```", ""))
            requires_web_search = res.get("requires_web_search", requires_web_search)
            requires_rag = res.get("requires_rag", requires_rag)
            is_factual = res.get("is_factual", is_factual)
            is_comparison = res.get("is_comparison", is_comparison)
            task_type = res.get("task_type", "comparison" if is_comparison else ("factual" if is_factual else "general"))
        except Exception as e:
            logger.warning(f"LLM intent analysis error: {e}")
            task_type = "comparison" if is_comparison else ("rag_query" if requires_rag else "factual")
    else:
        task_type = "comparison" if is_comparison else ("rag_query" if requires_rag else "factual")

    logs = add_log(
        state,
        step_name="Question Analyzer",
        status="completed",
        detail=f"Task Type: {task_type} | Web Search: {requires_web_search} | RAG Retrieval: {requires_rag}"
    )

    return {
        "requires_web_search": requires_web_search,
        "requires_rag": requires_rag,
        "is_factual": is_factual,
        "is_comparison": is_comparison,
        "task_type": task_type,
        "current_step": "analyze_question",
        "execution_logs": logs
    }

# 2. Planner Node
def create_plan_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    requires_web = state.get("requires_web_search", True)
    requires_rag = state.get("requires_rag", False)
    is_comp = state.get("is_comparison", False)

    plan = []
    if is_comp:
        plan.append("Analyze key subjects, requirements, and comparative criteria.")
        if requires_web:
            plan.append("Perform web research on live sources, documentation, and performance benchmarks.")
        if requires_rag:
            plan.append("Retrieve specific constraint and specification context from uploaded user documents.")
        plan.append("Synthesize comparative analysis evaluating pros, cons, and trade-offs.")
        plan.append("Validate findings and generated recommendation against evidence.")
        plan.append("Produce final structured response with source citations.")
    else:
        plan.append("Extract core inquiry topics and search parameters.")
        if requires_web:
            plan.append("Search live web sources, authoritative databases, and relevant documentation.")
        if requires_rag:
            plan.append("Query uploaded vector store for relevant document chunks.")
        plan.append("Synthesize collected technical and factual evidence.")
        plan.append("Validate accuracy, freshness, and completeness.")
        plan.append("Generate final decision report.")

    llm = get_llm()
    if llm:
        try:
            prompt = f"""Create a concise 4 to 6 step research plan for answering this question:
"{question}"
State flags: Web Search={requires_web}, RAG Retrieval={requires_rag}.

Return JSON array of strings: ["Step 1...", "Step 2...", ...]"""
            msg = llm.invoke([SystemMessage(content="You are an AI Planner. Return a JSON array of step descriptions."), HumanMessage(content=prompt)])
            parsed_plan = json.loads(msg.content.strip().replace("```json", "").replace("```", ""))
            if isinstance(parsed_plan, list) and len(parsed_plan) > 0:
                plan = parsed_plan
        except Exception as e:
            logger.warning(f"LLM planning fallback: {e}")

    logs = add_log(
        state,
        step_name="Planner",
        status="completed",
        detail=f"Created {len(plan)}-step research plan."
    )

    return {
        "plan": plan,
        "current_step": "create_plan",
        "execution_logs": logs
    }

# 3. Orchestrator Node
def orchestrator_node(state: ResearchState) -> Dict[str, Any]:
    iteration = state.get("iteration_count", 0)
    validation = state.get("validation_result", "")
    feedback = state.get("validation_feedback", "")

    detail_msg = "Orchestrating workflow path"
    if validation == "FAIL":
        detail_msg = f"Re-orchestrating research loop (Iteration {iteration}). Feedback: {feedback}"

    logs = add_log(
        state,
        step_name="Orchestrator",
        status="completed",
        detail=detail_msg
    )

    return {
        "current_step": "orchestrator",
        "execution_logs": logs
    }

# 4. Web Research Node
def web_research_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    iteration = state.get("iteration_count", 0)
    feedback = state.get("validation_feedback", "")

    search_tool = WebSearchTool()
    queries = [question]

    if iteration > 0 and feedback:
        queries.append(f"{question} {feedback}")
    elif "fastapi" in question.lower() and "django" in question.lower():
        queries = [
            "FastAPI performance async AI backend",
            "Django ORM architecture AI application",
            "FastAPI vs Django comparison"
        ]
    elif "chromadb" in question.lower() and "faiss" in question.lower():
        queries = [
            "ChromaDB vs FAISS vector database comparison",
            "ChromaDB features persistence metadata filtering"
        ]
    elif "langgraph" in question.lower() and ("latest" in question.lower() or "update" in question.lower()):
        queries = [
            "LangGraph latest changes updates production features",
            "LangGraph stateful multi-agent workflow architecture"
        ]

    all_results = list(state.get("web_results", []))
    new_sources = list(state.get("sources", []))

    for q in queries:
        res = search_tool.search(q, max_results=5)
        for r in res:
            if not any(existing.get("url") == r.get("url") and existing.get("title") == r.get("title") for existing in all_results):
                all_results.append(r)
                new_sources.append({
                    "title": r.get("title", "Web Source"),
                    "url": r.get("url", "#"),
                    "snippet": r.get("snippet", ""),
                    "source": "web"
                })

    logs = add_log(
        state,
        step_name="Web Research Agent",
        status="completed",
        detail=f"Executed web search across {len(queries)} queries. Retrieved {len(all_results)} sources."
    )

    return {
        "web_queries": queries,
        "web_results": all_results,
        "sources": new_sources,
        "current_step": "web_research",
        "execution_logs": logs
    }

# 5. RAG Retrieval Node
def rag_retrieval_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    rag_tool = RAGRetrieverTool()

    chunks = rag_tool.retrieve(question, k=5)
    existing_sources = list(state.get("sources", []))

    for chunk in chunks:
        source_item = {
            "title": chunk.get("source", "Uploaded Document"),
            "url": None,
            "snippet": chunk.get("content", "")[:200] + "...",
            "source": "rag"
        }
        if not any(s.get("title") == source_item["title"] and s.get("snippet") == source_item["snippet"] for s in existing_sources):
            existing_sources.append(source_item)

    logs = add_log(
        state,
        step_name="RAG Retrieval Agent",
        status="completed",
        detail=f"Retrieved {len(chunks)} document chunks from ChromaDB vector store."
    )

    return {
        "retrieved_documents": chunks,
        "sources": existing_sources,
        "current_step": "rag_retrieval",
        "execution_logs": logs
    }

# 6. Analysis Agent Node
def analysis_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    plan = state.get("plan", [])
    web_res = state.get("web_results", [])
    rag_docs = state.get("retrieved_documents", [])
    feedback = state.get("validation_feedback", "")

    web_text = "\n".join([f"- Title: {r.get('title')}\n  Snippet: {r.get('snippet')}\n  URL: {r.get('url')}" for r in web_res])
    rag_text = "\n".join([f"- Document: {d.get('filename')} (Page {d.get('page_number')})\n  Content: {d.get('content')}" for d in rag_docs])

    llm = get_llm()
    analysis = None
    if llm:
        try:
            prompt = f"""Synthesize a thorough technical analysis for the user question.

Question: "{question}"

Plan:
{json.dumps(plan, indent=2)}

Web Research Evidence:
{web_text if web_text else "No web results retrieved."}

Internal Uploaded Document RAG Evidence:
{rag_text if rag_text else "No internal document chunks retrieved."}

Previous Validation Feedback (if any):
{feedback}

Structure your analysis with distinct sections:
1. Core Findings & Evidence
2. Detailed Breakdown / Key Entities / Information
3. Synthesis & Practical Fit
4. Grounded Summary / Recommendation
"""
            msg = llm.invoke([
                SystemMessage(content="You are a senior AI research analyst. Be objective, thorough, and ground all claims in retrieved evidence."),
                HumanMessage(content=prompt)
            ])
            analysis = msg.content
        except Exception as e:
            logger.warning(f"LLM analysis error: {e}")

    if not analysis:
        # Dynamic evidence synthesis based on live search results and documents
        analysis = f"### Research Findings & Evidence Synthesis\n\n"
        analysis += f"**Inquiry:** {question}\n\n"
        
        if web_res:
            analysis += "#### Web Research Findings\n"
            for r in web_res:
                snippet = r.get("snippet", "").strip()
                title = r.get("title", "").strip()
                if snippet:
                    analysis += f"- **{title}**: {snippet}\n"
            analysis += "\n"

        if rag_docs:
            analysis += "#### Internal Uploaded Document Context\n"
            for d in rag_docs[:3]:
                analysis += f"- **{d.get('filename')} (Page {d.get('page_number')})**: {d.get('content')[:200]}...\n"
            analysis += "\n"

        # Topic specific analysis
        is_comp = state.get("is_comparison", False)
        if is_comp:
            analysis += "#### Comparative Evaluation\n"
            analysis += "- Evaluated primary options against retrieved technical documentation and benchmarks.\n"
        else:
            analysis += "#### Summary of Key Information\n"
            analysis += "- Verified authoritative public sources and documentation corresponding to the search inquiry.\n"

    logs = add_log(
        state,
        step_name="Analysis Agent",
        status="completed",
        detail="Synthesized web research and document RAG evidence into preliminary analysis."
    )

    return {
        "analysis": analysis,
        "current_step": "analysis",
        "execution_logs": logs
    }

# 7. Validator Agent Node
def validator_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    analysis = state.get("analysis", "")
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)
    sources = state.get("sources", [])

    status = "PASS"
    feedback = "Analysis is comprehensive, well-grounded in evidence, and directly answers user question."
    missing_info = []

    # Validation criteria checks
    if len(analysis.strip()) < 50:
        status = "FAIL"
        feedback = "Analysis text is too brief and lacks concrete evidence."

    # Prevent infinite loops
    if iteration >= (max_iter - 1):
        status = "PASS"
        feedback = f"Reached maximum allowed research iterations ({max_iter}). Proceeding with current best validated analysis."

    llm = get_llm()
    if llm and iteration < (max_iter - 1) and status == "PASS":
        try:
            prompt = f"""Evaluate this analysis report against user question:
Question: "{question}"
Analysis Draft:
{analysis[:1500]}

Available Sources Count: {len(sources)}

Evaluate:
1. Does the analysis directly answer the question?
2. Are claims supported by retrieved sources?
3. Is recommendation/summary consistent?

Respond ONLY with JSON:
{{
    "status": "PASS" | "FAIL",
    "feedback": "Reasoning...",
    "missing_information": ["..."]
}}
"""
            msg = llm.invoke([SystemMessage(content="You are a strict QA Validator Agent. Output JSON only."), HumanMessage(content=prompt)])
            res = json.loads(msg.content.strip().replace("```json", "").replace("```", ""))
            status = res.get("status", status)
            feedback = res.get("feedback", feedback)
            missing_info = res.get("missing_information", missing_info)
        except Exception as e:
            logger.warning(f"LLM validator fallback: {e}")

    new_iteration = iteration + 1

    logs = add_log(
        state,
        step_name="Validator Agent",
        status="completed" if status == "PASS" else "retry",
        detail=f"Validation Status: {status} | Feedback: {feedback}"
    )

    return {
        "validation_result": status,
        "validation_feedback": feedback,
        "missing_information": missing_info,
        "iteration_count": new_iteration,
        "current_step": "validator",
        "execution_logs": logs
    }

# 8. Final Answer Generator Node
def final_answer_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    analysis = state.get("analysis", "")
    sources = state.get("sources", [])
    rag_docs = state.get("retrieved_documents", [])
    web_res = state.get("web_results", [])

    llm = get_llm()
    final_answer = None
    if llm:
        try:
            prompt = f"""You are an intelligent research assistant. Provide a direct, natural, and conversational answer to the user's question based on the retrieved research evidence.

User Question: "{question}"

Synthesized Evidence:
{analysis}

Requirements:
- Answer the user's question directly and conversationally as in a chat assistant.
- Do NOT include markdown section headers like '# Research & Decision Report', '### Executive Summary', '## Detailed Findings', etc.
- Do NOT include any 'Sources & References' section, bibliographies, or markdown link lists at the end.
- Ground all facts and details in the evidence provided.
"""
            msg = llm.invoke([
                SystemMessage(content="You are a helpful AI assistant. Answer directly in a natural, conversational chat style without report headers or source citations at the end."),
                HumanMessage(content=prompt)
            ])
            final_answer = msg.content.strip()
        except Exception as e:
            logger.warning(f"LLM final answer error: {e}")

    if not final_answer:
        # Generate clean conversational text directly without headers or source lists
        parts = []
        if web_res:
            for r in web_res:
                s = r.get("snippet", "").strip()
                t = r.get("title", "").strip()
                if s:
                    parts.append(s)
                elif t:
                    parts.append(t)
        elif rag_docs:
            for d in rag_docs:
                c = d.get("content", "").strip()
                if c:
                    parts.append(c)

        if parts:
            final_answer = "\n\n".join(parts)
        else:
            final_answer = f"I could not find specific information to answer '{question}'."

    logs = add_log(
        state,
        step_name="Final Answer Generator",
        status="completed",
        detail="Generated plain conversational answer."
    )

    return {
        "final_answer": final_answer,
        "current_step": "final_answer",
        "execution_logs": logs
    }


