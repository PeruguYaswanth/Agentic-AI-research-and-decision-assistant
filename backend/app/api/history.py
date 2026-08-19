from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import ResearchSession, ResearchSource, ExecutionLog
from app.schemas.research import HistorySessionResponse, ResearchResponse, SourceItem, ExecutionStep

router = APIRouter(prefix="/api/research", tags=["Research History"])

@router.get("/history", response_model=List[HistorySessionResponse])
async def get_research_history(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ResearchSession)
        .options(selectinload(ResearchSession.sources))
        .order_by(ResearchSession.created_at.desc())
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    return [
        HistorySessionResponse(
            session_id=s.id,
            conversation_id=s.conversation_id,
            question=s.question,
            final_answer=s.final_answer,
            created_at=s.created_at,
            sources_count=len(s.sources) if s.sources else 0
        )
        for s in sessions
    ]

@router.get("/{session_id}", response_model=ResearchResponse)
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ResearchSession)
        .options(
            selectinload(ResearchSession.sources),
            selectinload(ResearchSession.logs)
        )
        .where(ResearchSession.id == session_id)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    plan_steps = []
    if session.plan and isinstance(session.plan, dict):
        plan_steps = session.plan.get("steps", [])

    return ResearchResponse(
        session_id=session.id,
        conversation_id=session.conversation_id,
        question=session.question,
        plan=plan_steps,
        final_answer=session.final_answer or "",
        sources=[
            SourceItem(
                title=s.title,
                url=s.url,
                snippet=s.snippet,
                source=s.source_type
            )
            for s in (session.sources or [])
        ],
        execution_logs=[
            ExecutionStep(
                step_name=l.step_name,
                status=l.status,
                detail=l.detail,
                timestamp=l.timestamp
            )
            for l in (session.logs or [])
        ],
        status=session.status
    )

@router.get("/{session_id}/sources", response_model=List[SourceItem])
async def get_session_sources(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ResearchSource).where(ResearchSource.session_id == session_id)
    res = await db.execute(stmt)
    sources = res.scalars().all()
    return [
        SourceItem(
            title=s.title,
            url=s.url,
            snippet=s.snippet,
            source=s.source_type
        )
        for s in sources
    ]
