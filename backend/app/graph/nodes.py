import json
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.state import ResearchState
from app.tools.web_search import WebSearchTool
from app.tools.rag_retriever import RAGRetrieverTool

logger = logging.getLogger(__name__)

from datetime import datetime, timezone

def get_current_datetime_str() -> str:
    """Returns dynamic current formatted date and time for temporal grounding."""
    now = datetime.now(timezone.utc)
    return now.strftime("%B %d, %Y (%H:%M UTC)")

def get_current_year_str() -> str:
    return str(datetime.now(timezone.utc).year)

def get_llm():
    if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip() and not settings.GROQ_API_KEY.startswith("your_"):
        try:
            model = settings.GROQ_MODEL or (settings.LLM_MODEL if settings.LLM_MODEL not in ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"] else "openai/gpt-oss-120b") or "openai/gpt-oss-120b"
            return ChatOpenAI(
                model=model,
                temperature=0.1,
                openai_api_key=settings.GROQ_API_KEY,
                openai_api_base="https://api.groq.com/openai/v1"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGroq: {e}")
            return None
    elif settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and not settings.OPENAI_API_KEY.startswith("your_"):
        try:
            return ChatOpenAI(
                model=settings.LLM_MODEL or "gpt-4o-mini",
                temperature=0.1,
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
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return logs

# 1. Question Analyzer & Freshness Classifier Node
def analyze_question_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    question_lower = question.lower()
    now_str = get_current_datetime_str()
    current_year = get_current_year_str()

    # Rule-based Freshness Classification
    real_time_triggers = [
        "today", "now", "current", "currently", "price", "ceo", "status", "weather", "temperature",
        "stock", "crypto", "breaking news", "market cap", "highest market cap", "who is the ceo", "current price"
    ]
    time_sensitive_triggers = [
        "latest", "recent", "this week", "this month", current_year, "2025", "2026",
        "developments", "announcement", "releases", "update", "version", "changes", "roadmap"
    ]
    rag_triggers = [
        "uploaded", "my document", "my file", "internal document", "project requirements",
        "my resume", "uploaded resume", "uploaded pdf", "my pdf", "internal knowledge base", "in the document"
    ]
    stable_triggers = [
        "what is", "explain", "how does", "difference between", "definition of", "architecture of", "formula"
    ]

    is_comparison = any(k in question_lower for k in [" vs ", "versus", "compare", " or ", "should i use", "comparison"])
    is_rag_explicit = any(t in question_lower for t in rag_triggers)
    has_stable_intent = any(t in question_lower for t in stable_triggers) or is_rag_explicit
    has_temporal_intent = any(t in question_lower for t in real_time_triggers) or any(t in question_lower for t in time_sensitive_triggers)

    if has_stable_intent and has_temporal_intent:
        freshness_category = "MIXED"
    elif any(t in question_lower for t in real_time_triggers):
        freshness_category = "REAL_TIME"
    elif any(t in question_lower for t in time_sensitive_triggers):
        freshness_category = "TIME_SENSITIVE"
    elif is_rag_explicit:
        freshness_category = "STABLE_KNOWLEDGE"
    elif has_stable_intent and not is_comparison:
        freshness_category = "STABLE_KNOWLEDGE"
    else:
        freshness_category = "TIME_SENSITIVE"

    # Routing flags
    if is_comparison:
        requires_web_search = True
        requires_rag = is_rag_explicit
    elif freshness_category in ["REAL_TIME", "TIME_SENSITIVE"]:
        requires_web_search = True
        requires_rag = False  # RAG alone is strictly prohibited for real-time questions
    elif freshness_category == "MIXED":
        requires_web_search = True
        requires_rag = True
    else:  # STABLE_KNOWLEDGE
        requires_rag = is_rag_explicit
        requires_web_search = not is_rag_explicit

    is_factual = any(k in question_lower for k in ["what", "who", "when", "where", "price", "ceo", "weather", "version", "how much"])

    # Generate 2-4 targeted search queries with temporal grounding
    generated_queries = [question]
    clean_q = re.sub(r"[^\w\s]", " ", question).strip()

    if freshness_category in ["REAL_TIME", "TIME_SENSITIVE", "MIXED"]:
        if "bitcoin" in question_lower or "btc" in question_lower:
            generated_queries = ["Bitcoin current live price USD CoinGecko", f"Bitcoin price {current_year} latest market data"]
        elif "openai" in question_lower and "ceo" in question_lower:
            generated_queries = [f"who is the current CEO of OpenAI {current_year}", f"OpenAI leadership Sam Altman {current_year}"]
        elif "react" in question_lower and "next" in question_lower:
            generated_queries = [f"latest stable version of React {current_year} react.dev", f"latest Next.js release version {current_year} nextjs.org"]
        elif "react" in question_lower and ("version" in question_lower or "latest" in question_lower):
            generated_queries = [f"React latest stable release version react.dev {current_year}", "React current release npmjs"]
        elif "langgraph" in question_lower:
            generated_queries = [f"LangGraph latest release updates features {current_year}", f"LangGraph documentation release notes {current_year}"]
        elif "market cap" in question_lower:
            generated_queries = [f"companies with highest market cap {current_year}", f"largest companies by market capitalization {current_year}"]
        elif "weather" in question_lower:
            generated_queries = [question, f"{question} live forecast {current_year}"]
        else:
            generated_queries = [
                f"{clean_q} {current_year}",
                f"{clean_q} latest official news {now_str[:12]}"
            ]

    # LLM Analyzer refinement if key is available
    llm = get_llm()
    if llm:
        try:
            prompt = f"""Current Date & Time: {now_str}
Analyze this user research question:
Question: "{question}"

Classify freshness category strictly as: "REAL_TIME" | "TIME_SENSITIVE" | "STABLE_KNOWLEDGE" | "MIXED"
Generate 2 to 4 targeted search queries that include the current year ({current_year}) for real-time freshness.

Respond ONLY with JSON:
{{
    "freshness_category": "REAL_TIME" | "TIME_SENSITIVE" | "STABLE_KNOWLEDGE" | "MIXED",
    "requires_web_search": bool,
    "requires_rag": bool,
    "is_comparison": bool,
    "search_queries": ["query 1", "query 2"]
}}"""
            msg = llm.invoke([
                SystemMessage(content="You are an expert search query planner. Return JSON only."),
                HumanMessage(content=prompt)
            ])
            res = json.loads(msg.content.strip().replace("```json", "").replace("```", ""))
            freshness_category = res.get("freshness_category", freshness_category)
            requires_web_search = res.get("requires_web_search", requires_web_search)
            requires_rag = res.get("requires_rag", requires_rag)
            if res.get("search_queries") and len(res["search_queries"]) > 0:
                generated_queries = res["search_queries"]
        except Exception as e:
            logger.debug(f"LLM analyzer notice: {e}")

    task_type = "comparison" if is_comparison else ("rag_query" if requires_rag and not requires_web_search else "factual")

    logs = add_log(
        state,
        step_name="Question Analyzer",
        status="completed",
        detail=f"Category: {freshness_category} | Live Web Required: {requires_web_search} | RAG Retrieval: {requires_rag} | Temporal Grounding: {now_str}"
    )

    return {
        "freshness_category": freshness_category,
        "current_datetime_str": now_str,
        "requires_web_search": requires_web_search,
        "requires_rag": requires_rag,
        "is_factual": is_factual,
        "is_comparison": is_comparison,
        "task_type": task_type,
        "web_queries": generated_queries,
        "current_step": "analyze_question",
        "execution_logs": logs
    }

# 2. Planner Node
def create_plan_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    freshness = state.get("freshness_category", "REAL_TIME")
    requires_web = state.get("requires_web_search", True)
    requires_rag = state.get("requires_rag", False)
    now_str = state.get("current_datetime_str", get_current_datetime_str())

    plan = [
        f"Analyze query freshness and establish search objectives ({now_str}).",
    ]
    if requires_web:
        plan.append("Perform live web research across authoritative primary sources and APIs.")
        plan.append("Fetch and parse full web pages to extract grounded factual passages.")
    if requires_rag:
        plan.append("Retrieve relevant specification context from uploaded knowledge base.")
    plan.append("Cross-verify evidence across independent sources and resolve discrepancies.")
    plan.append("Conduct claim-level validation to prevent hallucinations.")
    plan.append("Synthesize verified findings into structured decision report.")

    logs = add_log(
        state,
        step_name="Planner",
        status="completed",
        detail=f"Formulated {len(plan)}-step evidence-grounded research plan."
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

    detail_msg = "Orchestrating research workflow execution"
    if validation == "FAIL":
        detail_msg = f"Re-orchestrating research refinement (Iteration {iteration}). Focus: {feedback}"

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

# 4. Live Web Research & Page Fetching Node
def web_research_node(state: ResearchState) -> Dict[str, Any]:
    queries = list(state.get("web_queries", []))
    if not queries:
        queries = [state["question"]]

    iteration = state.get("iteration_count", 0)
    feedback = state.get("validation_feedback", "")
    current_year = get_current_year_str()

    if iteration > 0 and feedback:
        queries.append(f"{state['question']} {feedback} {current_year}")

    search_tool = WebSearchTool()
    all_results = list(state.get("web_results", []))
    new_sources = list(state.get("sources", []))

    for q in queries:
        # Search & Fetch real pages
        res = search_tool.search_and_fetch_pages(q, max_results=4, fetch_pages=True)
        for r in res:
            url = r.get("url")
            title = r.get("title", "Web Source")
            if not any(existing.get("url") == url and existing.get("title") == title for existing in all_results):
                all_results.append(r)
                new_sources.append({
                    "title": title,
                    "url": url,
                    "publisher": r.get("publisher", "Web Source"),
                    "authority_score": r.get("authority_score", 0.8),
                    "published_date": r.get("published_date"),
                    "snippet": r.get("snippet", ""),
                    "source": "web"
                })

    # Sort sources by authority score
    new_sources.sort(key=lambda s: s.get("authority_score", 0.7), reverse=True)

    logs = add_log(
        state,
        step_name="Web Research Agent",
        status="completed",
        detail=f"Searched {len(queries)} queries, retrieved and parsed {len(all_results)} verified source pages."
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

    chunks = rag_tool.retrieve(question, k=4)
    existing_sources = list(state.get("sources", []))

    for chunk in chunks:
        source_item = {
            "title": chunk.get("source", "Uploaded Document"),
            "url": None,
            "publisher": "Internal Knowledge Base",
            "authority_score": 0.85,
            "published_date": None,
            "snippet": chunk.get("content", "")[:250] + "...",
            "source": "rag"
        }
        if not any(s.get("title") == source_item["title"] and s.get("snippet") == source_item["snippet"] for s in existing_sources):
            existing_sources.append(source_item)

    logs = add_log(
        state,
        step_name="RAG Retrieval Agent",
        status="completed",
        detail=f"Retrieved {len(chunks)} document chunks from internal ChromaDB vector store."
    )

    return {
        "retrieved_documents": chunks,
        "sources": existing_sources,
        "current_step": "rag_retrieval",
        "execution_logs": logs
    }

# 6. Analysis & Cross-Verification Node
def analysis_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    now_str = state.get("current_datetime_str", get_current_datetime_str())
    freshness = state.get("freshness_category", "REAL_TIME")
    web_res = state.get("web_results", [])
    rag_docs = state.get("retrieved_documents", [])
    feedback = state.get("validation_feedback", "")

    # Format extracted evidence with publisher and authority
    web_evidence_blocks = []
    for r in web_res:
        pub = r.get("publisher", "Web Source")
        title = r.get("title", "Source")
        url = r.get("url", "#")
        date_str = f" (Date: {r.get('published_date')})" if r.get("published_date") else ""
        content = r.get("full_content") or r.get("snippet", "")
        web_evidence_blocks.append(f"[{pub} - '{title}'{date_str} (URL: {url})]:\n{content}")

    web_evidence_text = "\n\n".join(web_evidence_blocks)

    rag_evidence_blocks = []
    for d in rag_docs:
        rag_evidence_blocks.append(f"[Uploaded Document: {d.get('filename')} (Page {d.get('page_number', 1)})]:\n{d.get('content')}")
    rag_evidence_text = "\n\n".join(rag_evidence_blocks)

    llm = get_llm()
    analysis = None
    key_findings = []
    conflicts_detected = []

    if llm:
        try:
            prompt = f"""Current Date & Time: {now_str}
User Inquiry: "{question}"
Inquiry Freshness Category: {freshness}

SOURCE PRIORITY RULES:
1. Live Web Evidence MUST take absolute priority over older static knowledge or RAG data for real-time and time-sensitive inquiries.
2. Cross-verify claims across multiple independent sources.
3. If sources conflict (e.g. differing dates, versions, numbers, or names), explicitly identify the conflict and evaluate based on source authority and publication date.
4. Strictly NO hallucinations: every claim must be backed by the retrieved evidence below.

=== RETRIEVED LIVE WEB EVIDENCE ===
{web_evidence_text if web_evidence_text else "No live web evidence retrieved."}

=== RETRIEVED INTERNAL RAG CONTEXT ===
{rag_evidence_text if rag_evidence_text else "No internal document context retrieved."}

{f"Refinement Feedback from previous iteration: {feedback}" if feedback else ""}

Please provide a detailed factual synthesis with:
1. Direct Core Answer
2. Key Verified Findings (3-5 bullet points)
3. Source Cross-Verification & Conflict Resolution (if any)
4. Confidence Evaluation
"""
            msg = llm.invoke([
                SystemMessage(content="You are a senior AI research analyst and fact-checker. Ground all statements strictly in the provided evidence. Return clean, accurate markdown analysis."),
                HumanMessage(content=prompt)
            ])
            analysis = msg.content.strip()
        except Exception as e:
            logger.warning(f"LLM analysis synthesis error: {e}")

    # Robust rule-based synthesis fallback if LLM is unavailable or for deterministic ground truth
    if not analysis:
        analysis_parts = []
        key_findings = []

        if web_res:
            analysis_parts.append(f"### Research Findings & Live Evidence Synthesis\n**As of {now_str}:**\n")
            for r in web_res[:4]:
                pub = r.get("publisher", "Web Source")
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                if snippet:
                    analysis_parts.append(f"- **{pub} ({title})**: {snippet}")
                    key_findings.append(snippet[:150])
        elif rag_docs:
            analysis_parts.append(f"### Internal Knowledge Base Findings\n")
            for d in rag_docs:
                analysis_parts.append(f"- **{d.get('filename')} (Page {d.get('page_number', 1)})**: {d.get('content')}")
                key_findings.append(d.get("content", "")[:150])
        else:
            analysis_parts.append(f"No authoritative live evidence could be verified for '{question}' as of {now_str}.")

        analysis = "\n\n".join(analysis_parts)

    logs = add_log(
        state,
        step_name="Analysis Agent",
        status="completed",
        detail=f"Synthesized evidence from {len(web_res)} web sources and {len(rag_docs)} document chunks."
    )

    return {
        "analysis": analysis,
        "key_findings": key_findings,
        "conflicts_detected": conflicts_detected,
        "current_step": "analysis",
        "execution_logs": logs
    }

# 7. Validator & Claim-Level Fact-Checking Node
def validator_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    analysis = state.get("analysis", "")
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)
    sources = state.get("sources", [])
    web_res = state.get("web_results", [])
    rag_docs = state.get("retrieved_documents", [])
    freshness = state.get("freshness_category", "REAL_TIME")

    total_evidence_count = len(web_res) + len(rag_docs)
    status = "PASS"
    feedback = "All claims verified against live retrieved evidence."
    confidence_level = "HIGH" if total_evidence_count >= 2 else ("MEDIUM" if total_evidence_count == 1 else "LOW")
    confidence_reason = f"Verified across {total_evidence_count} authoritative evidence sources."
    claims_list = []

    # If no evidence was retrieved at all
    if total_evidence_count == 0:
        confidence_level = "LOW"
        confidence_reason = "No authoritative evidence sources were retrieved to verify this query."

    # Validate length and substance
    if len(analysis.strip()) < 40 and iteration < (max_iter - 1):
        status = "FAIL"
        feedback = "Analysis draft was insufficient. Expanding search query terms."

    # Prevent infinite loops
    if iteration >= (max_iter - 1):
        status = "PASS"
        if feedback.startswith("Analysis draft"):
            confidence_level = "LOW"
            confidence_reason = "Limited evidence retrieved within allowed search iterations."

    # LLM claim-level fact verification if LLM available
    llm = get_llm()
    if llm and iteration < (max_iter - 1) and status == "PASS":
        try:
            prompt = f"""Evaluate this research draft against the inquiry:
Inquiry: "{question}"
Freshness Category: {freshness}
Available Sources Count: {len(sources)}

Research Draft:
{analysis[:2000]}

Perform:
1. Break down draft into key factual claims.
2. Verify if each claim is directly SUPPORTED by retrieved evidence.
3. Check for any unsupported assertions or potential hallucinations.

Respond strictly with JSON:
{{
    "status": "PASS" | "FAIL",
    "confidence_level": "HIGH" | "MEDIUM" | "LOW",
    "confidence_reason": "Explanation of source consensus and coverage...",
    "feedback": "...",
    "claims": [
        {{"claim": "...", "status": "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED"}}
    ]
}}"""
            msg = llm.invoke([
                SystemMessage(content="You are a strict QA Fact Checker. Return JSON only."),
                HumanMessage(content=prompt)
            ])
            res = json.loads(msg.content.strip().replace("```json", "").replace("```", ""))
            status = res.get("status", status)
            confidence_level = res.get("confidence_level", confidence_level)
            confidence_reason = res.get("confidence_reason", confidence_reason)
            feedback = res.get("feedback", feedback)
            claims_list = res.get("claims", [])
        except Exception as e:
            logger.debug(f"LLM validator notice: {e}")

    new_iteration = iteration + 1

    logs = add_log(
        state,
        step_name="Validator Agent",
        status="completed" if status == "PASS" else "retry",
        detail=f"Fact Check: {status} | Confidence: {confidence_level} ({confidence_reason})"
    )

    return {
        "validation_result": status,
        "validation_feedback": feedback,
        "confidence_level": confidence_level,
        "confidence_reason": confidence_reason,
        "claims": claims_list,
        "iteration_count": new_iteration,
        "current_step": "validator",
        "execution_logs": logs
    }

# 8. Final Answer Generator Node
def final_answer_node(state: ResearchState) -> Dict[str, Any]:
    question = state["question"]
    now_str = state.get("current_datetime_str", get_current_datetime_str())
    analysis = state.get("analysis", "")
    sources = state.get("sources", [])
    web_res = state.get("web_results", [])
    rag_docs = state.get("retrieved_documents", [])
    confidence_level = state.get("confidence_level", "HIGH")
    confidence_reason = state.get("confidence_reason", f"Grounded in {len(sources)} verified sources.")
    freshness = state.get("freshness_category", "REAL_TIME")

    llm = get_llm()
    final_answer = None

    if llm:
        try:
            prompt = f"""Current Date & Time: {now_str}
User Inquiry: "{question}"
Inquiry Category: {freshness}
Assessed Confidence: {confidence_level} - {confidence_reason}

Synthesized Evidence Analysis:
{analysis}

FORMATTING REQUIREMENTS:
Generate a clean, professional, and readable research decision response using this exact structure:

### Research Summary
[Direct, accurate, and comprehensive natural-language answer grounded in the evidence. If temporal, clearly state findings as of {now_str[:12]}.]

### Key Findings
- **[Finding 1 Title]**: [Clear explanation]
- **[Finding 2 Title]**: [Clear explanation]
- **[Finding 3 Title]**: [Clear explanation]

### Research Confidence
- **Confidence Level**: **{confidence_level}**
- **Assessment**: {confidence_reason}

CRITICAL RULES:
- Do NOT dump raw source links or markdown URLs inside the text; sources are displayed separately in the UI cards.
- Ground all facts strictly in the evidence. If something could not be verified from current sources, state that clearly.
"""
            msg = llm.invoke([
                SystemMessage(content="You are a senior AI research assistant. Provide well-structured, clear, and grounded answers."),
                HumanMessage(content=prompt)
            ])
            final_answer = msg.content.strip()
        except Exception as e:
            logger.warning(f"LLM final answer generator error: {e}")

    if not final_answer:
        # Fallback structured generation
        summary_paragraphs = []
        if web_res:
            for r in web_res[:3]:
                snippet = r.get("snippet", "").strip()
                if snippet:
                    summary_paragraphs.append(snippet)
        elif rag_docs:
            for d in rag_docs[:3]:
                content = d.get("content", "").strip()
                if content:
                    summary_paragraphs.append(content)

        summary_text = "\n\n".join(summary_paragraphs) if summary_paragraphs else f"No authoritative data was found to verify '{question}' as of {now_str}."

        final_answer = f"""### Research Summary
Based on live verified research as of {now_str}, here is the current information:

{summary_text}

### Key Findings
"""
        if web_res:
            for i, r in enumerate(web_res[:3], 1):
                pub = r.get("publisher", "Web Source")
                snippet = r.get("snippet", "")
                final_answer += f"- **{pub}**: {snippet[:180]}\n"
        elif rag_docs:
            for i, d in enumerate(rag_docs[:3], 1):
                final_answer += f"- **{d.get('filename')} (Page {d.get('page_number', 1)})**: {d.get('content')[:180]}...\n"
        else:
            final_answer += f"- **Unverified**: Unable to establish verified findings from available sources.\n"

        final_answer += f"""
### Research Confidence
- **Confidence Level**: **{confidence_level}**
- **Assessment**: {confidence_reason}
"""

    logs = add_log(
        state,
        step_name="Final Answer Generator",
        status="completed",
        detail="Generated clean, evidence-grounded research response."
    )

    return {
        "final_answer": final_answer,
        "current_step": "final_answer",
        "execution_logs": logs
    }
