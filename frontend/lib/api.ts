export interface SourceItem {
  title: string;
  url?: string | null;
  snippet?: string | null;
  source: 'web' | 'rag';
}

export interface ExecutionStep {
  step_name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'retry';
  detail?: string | null;
  timestamp?: string;
}

export interface ResearchResponse {
  session_id: string;
  conversation_id: string;
  question: string;
  plan?: string[];
  final_answer: string;
  sources: SourceItem[];
  execution_logs: ExecutionStep[];
  status: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  indexed_status: string;
  uploaded_at: string;
}

export interface HistoryItem {
  session_id: string;
  conversation_id: string;
  question: string;
  final_answer?: string | null;
  created_at: string;
  sources_count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://agentic-ai-research-and-decision.onrender.com/api';

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || 'Upload failed');
  }

  return res.json();
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function getHistory(): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/research/history`);
  if (!res.ok) throw new Error('Failed to fetch research history');
  return res.json();
}

export async function getSession(sessionId: string): Promise<ResearchResponse> {
  const res = await fetch(`${API_BASE}/research/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch session details');
  return res.json();
}

export async function conductResearch(question: string, conversationId?: string): Promise<ResearchResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Research request failed' }));
    throw new Error(errorData.detail || 'Research request failed');
  }

  return res.json();
}

export async function streamResearch(
  question: string,
  conversationId: string | undefined,
  callbacks: {
    onStatus?: (step: ExecutionStep) => void;
    onPlan?: (plan: string[]) => void;
    onSources?: (sources: SourceItem[]) => void;
    onFinalAnswer?: (data: { final_answer: string; sources: SourceItem[]; session_id: string }) => void;
    onError?: (err: Error) => void;
    onComplete?: () => void;
  }
) {
  try {
    const response = await fetch(`${API_BASE}/research/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`Streaming failed: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        if (!block.trim()) continue;
        const blockLines = block.split('\n');
        let eventType = 'message';
        let dataStr = '';

        for (const line of blockLines) {
          if (line.startsWith('event: ')) {
            eventType = line.replace('event: ', '').trim();
          } else if (line.startsWith('data: ')) {
            dataStr = line.replace('data: ', '').trim();
          }
        }

        if (!dataStr) continue;

        try {
          const parsed = JSON.parse(dataStr);
          if (eventType === 'agent_status' && callbacks.onStatus) {
            callbacks.onStatus(parsed);
          } else if (eventType === 'plan_created' && callbacks.onPlan) {
            callbacks.onPlan(parsed.plan);
          } else if (eventType === 'sources_updated' && callbacks.onSources) {
            callbacks.onSources(parsed.sources);
          } else if (eventType === 'final_answer' && callbacks.onFinalAnswer) {
            callbacks.onFinalAnswer(parsed);
          } else if (eventType === 'complete' && callbacks.onComplete) {
            callbacks.onComplete();
          }
        } catch (e) {
          console.warn('Error parsing SSE data line:', e);
        }
      }
    }

    if (callbacks.onComplete) {
      callbacks.onComplete();
    }
  } catch (err: any) {
    if (callbacks.onError) {
      callbacks.onError(err);
    }
  }
}

export interface RAGQueryResponse {
  question: string;
  answer: string;
  document_id?: string | null;
  sources: SourceItem[];
}

export async function queryRAGKnowledgeBase(question: string, documentId?: string): Promise<RAGQueryResponse> {
  const res = await fetch(`${API_BASE}/documents/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, document_id: documentId || null }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'RAG query failed' }));
    throw new Error(errorData.detail || 'RAG query failed');
  }

  return res.json();
}

