import json
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Conversation, Message, ResearchSession, ResearchSource, ExecutionLog
from app.schemas.research import ChatRequest, ResearchResponse, SourceItem, ExecutionStep
from app.graph.builder import build_research_graph
from app.graph.state import ResearchState

router = APIRouter(prefix="/api", tags=["Research & Chat"])

@router.post("/chat", response_model=ResearchResponse)
async def conduct_research(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = Conversation(title=request.question[:60])
        db.add(conversation)
        await db.flush()
        conversation_id = conversation.id
    else:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        res = await db.execute(stmt)
        conversation = res.scalar_one_or_none()
        if not conversation:
            conversation = Conversation(id=conversation_id, title=request.question[:60])
            db.add(conversation)
            await db.flush()

    session_id = str(uuid.uuid4())

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.question
    )
    db.add(user_msg)

    # Initialize LangGraph
    graph = build_research_graph()

    initial_state: ResearchState = {
        "question": request.question,
        "conversation_id": conversation_id,
        "session_id": session_id,
        "plan": [],
        "current_step": "init",
        "requires_web_search": True,
        "requires_rag": False,
        "is_factual": True,
        "is_comparison": False,
        "task_type": "general",
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

    # Execute LangGraph
    final_state = graph.invoke(initial_state)

    # Save Research Session
    research_session = ResearchSession(
        id=session_id,
        conversation_id=conversation_id,
        question=request.question,
        plan={"steps": final_state.get("plan", [])},
        final_answer=final_state.get("final_answer", ""),
        status="completed"
    )
    db.add(research_session)

    # Save Assistant Message
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=final_state.get("final_answer", "")
    )
    db.add(assistant_msg)

    # Save Sources
    for src in final_state.get("sources", []):
        db_source = ResearchSource(
            session_id=session_id,
            title=src.get("title", "Source"),
            url=src.get("url"),
            snippet=src.get("snippet"),
            source_type=src.get("source", "web")
        )
        db.add(db_source)

    # Save Execution Logs
    for log in final_state.get("execution_logs", []):
        db_log = ExecutionLog(
            session_id=session_id,
            step_name=log.get("step_name", "Step"),
            status=log.get("status", "completed"),
            detail=log.get("detail", "")
        )
        db.add(db_log)

    await db.commit()

    return ResearchResponse(
        session_id=session_id,
        conversation_id=conversation_id,
        question=request.question,
        plan=final_state.get("plan", []),
        final_answer=final_state.get("final_answer", ""),
        sources=[SourceItem(**s) for s in final_state.get("sources", [])],
        execution_logs=[
            ExecutionStep(
                step_name=l["step_name"],
                status=l["status"],
                detail=l.get("detail"),
                timestamp=datetime.fromisoformat(l["timestamp"]) if isinstance(l.get("timestamp"), str) else datetime.utcnow()
            )
            for l in final_state.get("execution_logs", [])
        ],
        status="completed"
    )

@router.post("/research/stream")
async def stream_research(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Streams LangGraph step-by-step events to the frontend via Server-Sent Events (SSE).
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    async def event_generator():
        # Yield init event
        yield f"event: session_info\ndata: {json.dumps({'session_id': session_id, 'conversation_id': conversation_id})}\n\n"

        graph = build_research_graph()

        initial_state: ResearchState = {
            "question": request.question,
            "conversation_id": conversation_id,
            "session_id": session_id,
            "plan": [],
            "current_step": "init",
            "requires_web_search": True,
            "requires_rag": False,
            "is_factual": True,
            "is_comparison": False,
            "task_type": "general",
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

        # Stream node-by-node updates from LangGraph
        accumulated_state = initial_state
        for output in graph.stream(initial_state):
            for node_name, node_state in output.items():
                if isinstance(node_state, dict):
                    accumulated_state.update(node_state)
                    latest_logs = node_state.get("execution_logs", [])
                    if latest_logs:
                        latest_log = latest_logs[-1]
                        yield f"event: agent_status\ndata: {json.dumps(latest_log)}\n\n"
                    
                    if "plan" in node_state and node_state["plan"]:
                        yield f"event: plan_created\ndata: {json.dumps({'plan': node_state['plan']})}\n\n"

                    if "sources" in node_state and node_state["sources"]:
                        yield f"event: sources_updated\ndata: {json.dumps({'sources': node_state['sources']})}\n\n"

        # Final answer event
        final_answer = accumulated_state.get("final_answer", "")
        sources = accumulated_state.get("sources", [])
        yield f"event: final_answer\ndata: {json.dumps({'final_answer': final_answer, 'sources': sources, 'session_id': session_id})}\n\n"
        yield f"event: complete\ndata: {json.dumps({'status': 'completed'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
