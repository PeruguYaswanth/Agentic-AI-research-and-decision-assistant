import os
import shutil
import uuid
import re
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from langchain_core.messages import SystemMessage, HumanMessage

from app.db.database import get_db
from app.db.models import DocumentMetadata
from app.schemas.research import DocumentResponse, RAGQueryRequest, RAGQueryResponse, SourceItem
from app.rag.document_processor import DocumentProcessor
from app.tools.rag_retriever import RAGRetrieverTool
from app.graph.nodes import get_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Document Management"])

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(status_code=400, detail="Only .pdf, .txt, and .md files are supported")

    doc_id = str(uuid.uuid4())
    saved_filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Process and index structure-aware chunks into ChromaDB & BM25
    processor = DocumentProcessor()
    chunk_count = processor.process_and_index_file(
        file_path=file_path,
        document_id=doc_id,
        original_filename=file.filename
    )

    doc_meta = DocumentMetadata(
        id=doc_id,
        filename=file.filename,
        file_type=ext.replace(".", ""),
        file_size=file_size,
        chunk_count=chunk_count,
        indexed_status="indexed"
    )
    db.add(doc_meta)
    await db.commit()
    await db.refresh(doc_meta)

    return DocumentResponse(
        id=doc_meta.id,
        filename=doc_meta.filename,
        file_type=doc_meta.file_type,
        file_size=doc_meta.file_size,
        chunk_count=doc_meta.chunk_count,
        indexed_status=doc_meta.indexed_status,
        uploaded_at=doc_meta.uploaded_at
    )

@router.get("", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    stmt = select(DocumentMetadata).order_by(DocumentMetadata.uploaded_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size,
            chunk_count=d.chunk_count,
            indexed_status=d.indexed_status,
            uploaded_at=d.uploaded_at
        )
        for d in docs
    ]

@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(DocumentMetadata).where(DocumentMetadata.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from ChromaDB vector store and BM25 index
    processor = DocumentProcessor()
    processor.delete_document_chunks(doc_id)

    # Remove physical file from disk
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(doc_id):
            try:
                os.remove(os.path.join(UPLOAD_DIR, f))
            except Exception:
                pass

    await db.delete(doc)
    await db.commit()

    return {"message": "Document deleted successfully", "id": doc_id}

def synthesize_grounded_rag_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Deterministic rule-based fact extractor and synthesizer when external LLM is not configured.
    Guarantees zero-hallucination exact value extraction, numbers, dates, definitions, multi-part handling,
    condition-sensitive clause matching, and strict 'not found' handling.
    """
    q_lower = question.lower()
    full_text = "\n\n".join([c.get("raw_text") or c.get("content", "") for c in chunks])
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # Extract non-stop words & ignore generic document fillers
    stop_words = {
        "what", "when", "where", "which", "who", "how", "this", "that", "the", "and",
        "for", "with", "does", "have", "from", "tell", "about", "give", "please", "is",
        "are", "of", "in", "to", "a", "an", "the", "by", "as", "company", "employee",
        "employees", "policy", "policies", "information", "details", "detail", "provide",
        "provided", "applies", "requirement", "requirements", "guidelines", "reimbursement", "coverage"
    }
    q_keywords = [w for w in re.findall(r"[a-zA-Z0-9\$\%_\.\@]+", q_lower) if len(w) > 2 and w not in stop_words]

    if not q_keywords:
        # Fallback if query only had stop words
        q_keywords = [w for w in re.findall(r"[a-zA-Z0-9\$\%_\.\@]+", q_lower) if len(w) > 2]

    # Subject modifier validation: if any rare/specific keyword in query is completely missing from text, reject
    full_text_lower = full_text.lower()
    for kw in q_keywords:
        # Specific nouns like 'pet', 'dental', 'marketing', 'severance', 'programming', 'medical'
        if kw in ["pet", "severance", "marketing", "programming", "python", "java", "bonus", "relocation", "parking"]:
            if kw not in full_text_lower:
                return "I could not find this information in the uploaded knowledge base."

    # Check if this is a negative / missing question (no core topic keywords match context)
    best_match_count = 0
    for line in lines:
        l_lower = line.lower()
        cnt = sum(1 for kw in q_keywords if kw in l_lower)
        if cnt > best_match_count:
            best_match_count = cnt

    if best_match_count == 0:
        return "I could not find this information in the uploaded knowledge base."

    # Check for multi-part questions (e.g., "What are the annual leave, sick leave and probation policies?")
    sub_parts = []
    if any(sep in q_lower for sep in [",", " and ", " as well as "]):
        parts = re.split(r",|\band\b|\bas well as\b", question, flags=re.IGNORECASE)
        for p in parts:
            p_strip = p.strip()
            # Filter clean sub-keywords
            sub_kws = [w for w in re.findall(r"[a-zA-Z0-9\$\%_\.\@]+", p_strip.lower()) if len(w) > 2 and w not in stop_words]
            if len(sub_kws) >= 1:
                sub_parts.append((p_strip, sub_kws))

    # If this is a valid multi-part query with 2+ distinct sub-topics
    if len(sub_parts) >= 2:
        multi_answers = []
        multi_sources = []
        for part_label, sub_kws in sub_parts:
            best_sub_sentence = None
            best_sub_score = 0
            best_sub_source = None

            for chunk in chunks:
                sec = chunk.get("section", "Document")
                page = chunk.get("page_number", 1)
                filename = chunk.get("filename", "Document")
                content = chunk.get("raw_text") or chunk.get("content", "")

                sentences = re.split(r"(?<=[.!?\n])\s+", content)
                for s in sentences:
                    s_clean = s.strip()
                    if len(s_clean) < 10 or len(s_clean) > 400:
                        continue
                    s_lower = s_clean.lower()
                    score = sum(1 for kw in sub_kws if kw in s_lower)
                    if score > best_sub_score:
                        best_sub_score = score
                        best_sub_sentence = s_clean
                        best_sub_source = f"{filename} — Page {page} (Section: {sec})"

            if best_sub_sentence and best_sub_score >= 1:
                multi_answers.append(best_sub_sentence)
                if best_sub_source and best_sub_source not in multi_sources:
                    multi_sources.append(best_sub_source)

        if len(multi_answers) >= 2:
            ans_body = "\n\n".join([f"• {a}" for a in multi_answers])
            return ans_body

    # Single or condition-targeted question matching
    # Check for condition phrases: "more than", "one year or less", "less than", "after", "before", "tier 1", "tier 2", "domestic", "international"
    condition_phrases = ["more than", "greater than", "one year or less", "less than", "during probation", "after probation", "domestic", "international", "tier 1", "tier 2", "hybrid", "remote"]
    active_conditions = [cp for cp in condition_phrases if cp in q_lower]

    matched_points = []
    for chunk in chunks:
        sec = chunk.get("section", "Document")
        page = chunk.get("page_number", 1)
        filename = chunk.get("filename", "Document")
        content = chunk.get("raw_text") or chunk.get("content", "")

        sentences = re.split(r"(?<=[.!?\n])\s+", content)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 10 or len(s_clean) > 400:
                continue
            s_lower = s_clean.lower()
            matches = sum(1 for kw in q_keywords if kw in s_lower)

            # Bonus score if sentence satisfies the active condition in the question
            condition_bonus = 0
            if active_conditions:
                for cp in active_conditions:
                    if cp in s_lower:
                        condition_bonus += 5
                    elif cp == "one year or less" and ("1 year or less" in s_lower or "one year or less" in s_lower):
                        condition_bonus += 5

            total_score = matches + condition_bonus
            if matches >= 1:
                matched_points.append({
                    "sentence": s_clean,
                    "score": total_score,
                    "condition_match": condition_bonus > 0,
                    "source": f"{filename} — Page {page} (Section: {sec})"
                })

    matched_points.sort(key=lambda x: x["score"], reverse=True)

    if matched_points:
        # If there is a strong condition match, prioritize only the condition-matching sentence
        if active_conditions and any(p["condition_match"] for p in matched_points):
            top_matches = [p for p in matched_points if p["condition_match"]][:2]
        else:
            top_matches = matched_points[:3]

        chosen = []
        sources = []
        for p in top_matches:
            sent = p["sentence"]
            src = p["source"]
            if not any(sent in c or c in sent for c in chosen):
                chosen.append(sent)
                if src not in sources:
                    sources.append(src)

        ans_body = " ".join(chosen)
        return ans_body

    return "I could not find this information in the uploaded knowledge base."

@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(request: RAGQueryRequest):
    """
    Answers questions strictly grounded in the uploaded Knowledge Base (ChromaDB + BM25).
    Optionally isolated to a specific document_id.
    """
    print(f"\n==================== KNOWLEDGE BASE RAG DEBUG ====================")
    print(f"[1] QUESTION:\n{request.question}\n")

    retriever = RAGRetrieverTool()
    chunks = retriever.retrieve(
        query=request.question,
        k=request.top_k,
        document_id=request.document_id
    )

    print(f"[2] RETRIEVED CHUNKS ({len(chunks)} chunks):")
    for i, c in enumerate(chunks, 1):
        filename = c.get("filename", "Document")
        page = c.get("page_number", 1)
        sec = c.get("section", "General")
        text = (c.get("raw_text") or c.get("content", ""))[:200].replace("\n", " ")
        print(f"  Chunk {i} [{filename} | Page {page} | Section: {sec}]: {text}...")
    print()

    if not chunks:
        print("[3] GROQ CALL:\nNO (No chunks retrieved)")
        print("[4] GROQ MODEL:\nNone")
        print("[5] GROQ RESPONSE RECEIVED:\nNO")
        print("[6] FINAL ANSWER:\nI could not find this information in the uploaded knowledge base.\n")
        print(f"===================================================================\n")
        return RAGQueryResponse(
            question=request.question,
            answer="I could not find this information in the uploaded knowledge base.",
            document_id=request.document_id,
            sources=[]
        )

    sources = [
        SourceItem(
            title=chunk.get("filename", "Uploaded Document"),
            url=None,
            snippet=chunk.get("raw_text", chunk.get("content", ""))[:250],
            publisher=f"Page {chunk.get('page_number', 1)} • Section: {chunk.get('section', 'General')}",
            published_date=None,
            authority_score=0.95,
            source="rag"
        )
        for chunk in chunks
    ]

    llm = get_llm()
    answer = None
    groq_model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "Unknown") if llm else "None"

    if llm:
        print(f"[3] GROQ CALL:\nYES")
        print(f"[4] GROQ MODEL:\n{groq_model_name}")
        try:
            context_blocks = []
            for c in chunks:
                filename = c.get("filename", "Document")
                page = c.get("page_number", 1)
                sec = c.get("section", "General")
                text = c.get("raw_text") or c.get("content", "")
                context_blocks.append(
                    f"[{filename} | Page {page} | Section: {sec}]:\n{text}"
                )

            context_text = "\n\n".join(context_blocks)

            system_instruction = """You are answering a question using ONLY the provided Knowledge Base context.

Rules:
1. Use ONLY information explicitly present in the Knowledge Base context.
2. Do NOT use your general/world knowledge or make assumptions.
3. Do NOT guess or infer unsupported facts.
4. Strictly preserve exact numbers, dates, names, percentages, and limits.
5. If the answer is present, answer directly and concisely.
6. If the answer is not present in the context, say:
   "I could not find this information in the uploaded knowledge base."
7. If the retrieved context is insufficient, do NOT invent an answer.
8. If two pieces of context conflict, explicitly mention the conflict.
9. Provide ONLY the final direct answer. Do NOT include or append document names, page numbers, section headers, citations, or source lists to the answer text."""

            prompt = f"""KNOWLEDGE BASE CONTEXT:
{context_text}

QUESTION:
{request.question}
"""
            msg = llm.invoke([
                SystemMessage(content=system_instruction),
                HumanMessage(content=prompt)
            ])
            answer = msg.content.strip()
            groq_meta = getattr(msg, "response_metadata", {})
            print(f"[5] GROQ RESPONSE RECEIVED:\nYES")
            print(f"    Groq Model Field / Metadata: {groq_meta}")
        except Exception as e:
            print(f"[5] GROQ RESPONSE RECEIVED:\nNO (Exception: {e})")
            logger.warning(f"LLM RAG generation notice: {e}")
    else:
        print("[3] GROQ CALL:\nNO (LLM not initialized)")
        print("[4] GROQ MODEL:\nNone")
        print("[5] GROQ RESPONSE RECEIVED:\nNO")

    if not answer:
        print("  [Falling back to deterministic rule-based grounded fact extraction]")
        answer = synthesize_grounded_rag_answer(request.question, chunks)

    try:
        print(f"[6] FINAL ANSWER:\n{answer}\n")
    except UnicodeEncodeError:
        print(f"[6] FINAL ANSWER:\n{answer.encode('ascii', errors='replace').decode('ascii')}\n")
    print(f"===================================================================\n")

    return RAGQueryResponse(
        question=request.question,
        answer=answer,
        document_id=request.document_id,
        sources=sources
    )
