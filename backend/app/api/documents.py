import os
import shutil
import uuid
import logging
from typing import List
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

    # Save to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Process and index chunks into ChromaDB
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

    # Remove from ChromaDB
    processor = DocumentProcessor()
    processor.delete_document_chunks(doc_id)

    # Remove file from disk
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(doc_id):
            try:
                os.remove(os.path.join(UPLOAD_DIR, f))
            except Exception:
                pass

    await db.delete(doc)
    await db.commit()

    return {"message": "Document deleted successfully", "id": doc_id}

def synthesize_rag_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Synthesizes a concise, grounded answer from retrieved chunks when external LLM is not configured.
    """
    import re
    q_lower = question.lower()
    full_text = "\n".join([c.get("content", "") for c in chunks])
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # 1. Key-Value / Form Field Matching (Admissions, IDs, Ranks, Application forms)
    field_keywords = {
        'candidate name': ['candidate name'],
        'candidate id': ['candidate id', 'cap00'],
        'father name': ['father name', 'father'],
        'engineering rank': ['engineering rank', 'rank'],
        'entrance marks': ['entrance marks', 'marks'],
        'hall ticket': ['hall ticket', 'eapcet hall ticket'],
        'qualifying exam': ['qualifying exam', 'qualifying exam name'],
        'gender': ['gender'],

        'caste': ['caste'],
        'stream': ['stream'],
        'subject': ['eapcet subject', 'subject'],
        'dob': ['dob', 'date of birth']
    }

    matched_fields = []
    for label, patterns in field_keywords.items():
        if any(p in q_lower for p in patterns):
            for i, line in enumerate(lines):
                line_clean = line.replace("\ufffd", "-").strip()
                if 'candidate id' in label and 'candidate id' in line_clean.lower():
                    m = re.search(r'candidate id\s*([A-Za-z0-9]+)', line_clean, re.I)
                    if m and f'Candidate ID: **{m.group(1)}**' not in matched_fields:
                        matched_fields.append(f'Candidate ID: **{m.group(1)}**')
                if 'candidate name' in label and 'candidate name' in line_clean.lower():
                    m = re.search(r'candidate name\s*([A-Za-z\s]+?)(?:Father|Dob|Gender|Aadhaar|Mobile|$)', line_clean, re.I)
                    if m and f'Candidate Name: **{m.group(1).strip()}**' not in matched_fields:
                        matched_fields.append(f'Candidate Name: **{m.group(1).strip()}**')
                if 'father name' in label and 'father name' in line_clean.lower():
                    m = re.search(r'father name\s*([A-Za-z\s]+?)(?:Dob|Gender|Caste|Aadhaar|Mobile|$)', line_clean, re.I)
                    if m and f'Father Name: **{m.group(1).strip()}**' not in matched_fields:
                        matched_fields.append(f'Father Name: **{m.group(1).strip()}**')
                
                # Check header followed by value
                if any(line_clean.lower() == p or line_clean.lower().startswith(f"{p}:") or line_clean.lower().startswith(f"{p} ") for p in patterns):
                    if i + 1 < len(lines) and len(lines[i+1].split()) <= 4:
                        val = lines[i+1].replace("\ufffd", "-").strip()
                        field_str = f'{line_clean.title()}: **{val}**'
                        if field_str not in matched_fields:
                            matched_fields.append(field_str)


    # 2. Preferences / College Selections
    if any(k in q_lower for k in ['preference', 'college', 'option', 'choice', 'first preference', '1st preference']):
        pref_num = None
        m_num = re.search(r'(\d+)(?:st|nd|rd|th)?\s*preference|preference\s*(\d+)', q_lower)
        if m_num:
            pref_num = m_num.group(1) or m_num.group(2)
        
        pref_lines = []
        for line in lines:
            line_clean = line.replace("\ufffd", "-").strip()
            if pref_num:
                if line_clean.startswith(f'{pref_num} ') or line_clean.startswith(f'{pref_num}.'):
                    pref_lines.append(line_clean)
            else:
                if re.match(r'^\d+\s+[A-Z0-9]', line_clean):
                    pref_lines.append(line_clean)

        if pref_lines:
            if pref_num:
                return f'Based on the document, Preference {pref_num} is:\n- **{pref_lines[0]}**'
            else:
                return 'Based on the document, the college preferences include:\n' + '\n'.join([f'- {p}' for p in pref_lines[:5]])

    if matched_fields:
        return 'Based on the document, here are the requested details:\n' + '\n'.join([f'- {f}' for f in matched_fields])

    # 3. Job title / Company / Most recent role
    if any(k in q_lower for k in ["recent job", "job title", "current job", "company", "work experience", "employer", "position", "role", "internship", "intern"]):
        in_exp = False
        exp_lines = []
        for l in lines:
            if l.strip().upper() in ["PROFESSIONAL EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT HISTORY", "EXPERIENCE"]:
                in_exp = True
                continue
            if in_exp:
                if l.strip().upper() in ["PROJECTS", "EDUCATION", "CERTIFICATIONS", "TECHNICAL SKILLS", "ACADEMIC"]:
                    break
                exp_lines.append(l)
        
        if exp_lines:
            company = exp_lines[0]
            role = exp_lines[1] if len(exp_lines) > 1 else "Intern"
            clean_company = company.replace("\ufffd", "-").strip()
            clean_role = role.replace("\ufffd", "-").strip()
            return f"Based on the document, the most recent role is **{clean_role}** at **{clean_company}**."

    # 4. Education / Degree / College / University / CGPA
    if any(k in q_lower for k in ["education", "degree", "college", "university", "cgpa", "school", "gpa", "study", "b.tech", "graduat"]):
        edu_entries = []
        for i, line in enumerate(lines):
            if any(deg in line.lower() for deg in ["b.tech", "btech", "bachelor", "master", "degree", "college", "institute", "school", "class xii", "class x"]):
                context = line
                if i + 1 < len(lines) and any(d in lines[i+1] for d in ["20", "CGPA", "GPA", "%", "Grade"]):
                    context += f" ({lines[i+1]})"
                clean_entry = context.replace("\ufffd", "-").strip()
                if clean_entry not in edu_entries:
                    edu_entries.append(clean_entry)
        if edu_entries:
            return "Based on the document, the educational background is:\n" + "\n".join([f"- {e}" for e in edu_entries[:3]])

    # 5. Technical Skills
    if any(k in q_lower for k in ["skill", "technolog", "programming", "language", "stack", "framework", "database", "tools"]):
        skill_entries = []
        for line in lines:
            if any(cat in line.lower() for cat in ["languages:", "frontend:", "backend:", "databases:", "testing:", "devops", "tools:"]):
                clean_skill = line.replace("\ufffd", "-").strip()
                if clean_skill not in skill_entries:
                    skill_entries.append(clean_skill)
        if skill_entries:
            return "Based on the document, the key technical skills include:\n" + "\n".join([f"- {s}" for s in skill_entries])

    # 6. Projects
    if any(k in q_lower for k in ["project", "built", "developed", "application", "app", "system"]):
        project_entries = []
        for line in lines:
            if "|" in line and any(t in line for t in ["React", "Python", "FastAPI", "MongoDB", "JavaScript", "Next.js", "OOP", "HTML"]):
                clean_p = line.replace("\ufffd", "-").strip()
                if clean_p not in project_entries:
                    project_entries.append(clean_p)
        if project_entries:
            return "Based on the document, the key projects include:\n" + "\n".join([f"- **{p}**" for p in project_entries[:4]])

    # 7. Semantic keyword sentence extraction
    stop_words = {"what", "when", "where", "which", "who", "how", "this", "that", "person", "document", "file", "tell", "about", "give", "name", "please", "does", "have", "from", "with", "their", "is", "are", "the"}
    query_terms = [w for w in re.findall(r"[a-zA-Z0-9]+", q_lower) if len(w) > 2 and w not in stop_words]
    
    scored_sentences = []
    for chunk in chunks:
        raw = chunk.get("content", "")
        parts = re.split(r"(?<=[.!?\n])\s+", raw)
        for p in parts:
            p_clean = p.strip().replace("\ufffd", "-")
            if len(p_clean) < 15 or len(p_clean) > 350:
                continue
            if any(skip in p_clean.upper() for skip in ["TABLE OF CONTENTS", "PAGE 1", "PAGE 2", "PAGE 3"]):
                continue
            matches = sum(1 for term in query_terms if term in p_clean.lower())
            if matches > 0:
                scored_sentences.append((matches, p_clean))

    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    if scored_sentences:
        chosen = []
        for _, s in scored_sentences:
            if not any(s in existing or existing in s for existing in chosen):
                chosen.append(s)
            if len(chosen) >= 2:
                break
        return " ".join(chosen)

    return "The requested information was not explicitly stated in the document context."


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(request: RAGQueryRequest):
    """
    Answers questions grounded in the uploaded document knowledge base (ChromaDB).
    Optionally scoped to a specific document_id.
    """
    retriever = RAGRetrieverTool()
    chunks = retriever.retrieve(
        query=request.question,
        k=request.top_k,
        document_id=request.document_id
    )

    if not chunks:
        return RAGQueryResponse(
            question=request.question,
            answer="No relevant information was found in the indexed documents to answer this question.",
            document_id=request.document_id,
            sources=[]
        )

    sources = [
        SourceItem(
            title=chunk.get("filename", "Uploaded Document"),
            url=None,
            snippet=chunk.get("content", "")[:250],
            source="rag"
        )
        for chunk in chunks
    ]

    llm = get_llm()
    answer = None
    if llm:
        try:
            context_text = "\n\n".join([
                f"[Chunk from {c.get('filename', 'Document')} (Page {c.get('page_number', 1)})]:\n{c.get('content', '')}"
                for c in chunks
            ])
            prompt = f"""Answer the question based only on the following context:
{context_text}

Question: {request.question}
Answer:"""
            msg = llm.invoke([
                SystemMessage(content="You are a helpful knowledge assistant. Answer the user's question accurately and concisely based strictly on the provided document context."),
                HumanMessage(content=prompt)
            ])
            answer = msg.content.strip()
        except Exception as e:
            logger.warning(f"LLM RAG query error: {e}")

    if not answer:
        answer = synthesize_rag_answer(request.question, chunks)

    return RAGQueryResponse(
        question=request.question,
        answer=answer,
        document_id=request.document_id,
        sources=sources
    )


