'use client';

import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Upload, 
  Trash2, 
  Database, 
  CheckCircle2, 
  AlertCircle, 
  FileCode, 
  HardDrive, 
  MessageSquare, 
  Send, 
  Sparkles,
  BookOpen
} from 'lucide-react';
import { listDocuments, uploadDocument, deleteDocument, queryRAGKnowledgeBase, DocumentItem, RAGQueryResponse } from '@/lib/api';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Q&A State
  const [question, setQuestion] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<string>('all');
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<RAGQueryResponse | null>(null);

  const fetchDocs = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (e) {
      console.error('Failed to load documents', e);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const newDoc = await uploadDocument(file);
      setUploadSuccess(`Successfully indexed "${newDoc.filename}" into ${newDoc.chunk_count} vector chunks.`);
      await fetchDocs();
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      if (selectedDocId === id) {
        setSelectedDocId('all');
      }
      await fetchDocs();
    } catch (err: any) {
      alert('Failed to delete document: ' + err.message);
    }
  };

  const handleAskQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsQuerying(true);
    setQueryError(null);

    try {
      const docFilter = selectedDocId === 'all' ? undefined : selectedDocId;
      const res = await queryRAGKnowledgeBase(question.trim(), docFilter);
      setQueryResult(res);
    } catch (err: any) {
      setQueryError(err.message || 'Failed to query knowledge base');
    } finally {
      setIsQuerying(false);
    }
  };

  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Database className="w-5 h-5 text-emerald-400" />
          <span>Knowledge Base & Document Index (ChromaDB)</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Upload PDF, TXT, or MD specification documents and ask questions grounded strictly in their content.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Uploaded Documents</div>
            <div className="text-lg font-bold text-white">{documents.length}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <FileCode className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Total Vector Chunks</div>
            <div className="text-lg font-bold text-white">{totalChunks}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Vector Store Status</div>
            <div className="text-sm font-semibold text-emerald-400 flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              ChromaDB Ready
            </div>
          </div>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="p-6 rounded-xl bg-[#0e1420] border-2 border-dashed border-slate-800 hover:border-blue-500/50 transition-colors text-center space-y-3">
        <div className="w-12 h-12 mx-auto rounded-full bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
          <Upload className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Upload documents for RAG indexing</h3>
          <p className="text-xs text-slate-400 mt-1">Supports .pdf, .txt, and .md files (e.g. project requirements, technical notes)</p>
        </div>

        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold cursor-pointer transition-all">
          <span>{isUploading ? 'Splitting & Indexing...' : 'Select File'}</span>
          <input
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="hidden"
          />
        </label>
      </div>

      {uploadSuccess && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {uploadError && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Document Q&A Section */}
      <div className="p-5 rounded-xl bg-[#0e1420] border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-white">Ask Questions on Uploaded Documents</h2>
          </div>
          <span className="text-xs text-slate-400">Grounded Semantic RAG</span>
        </div>

        <form onSubmit={handleAskQuestion} className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Indexed Documents ({documents.length})</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
            </select>

            <div className="relative flex-1">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={documents.length > 0 ? "Ask a question about the uploaded document..." : "Upload a document first to start asking questions..."}
                disabled={documents.length === 0 || isQuerying}
                className="w-full pl-3 pr-24 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={documents.length === 0 || !question.trim() || isQuerying}
                className="absolute right-1 top-1 bottom-1 px-3 rounded-md bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:text-slate-500"
              >
                {isQuerying ? (
                  <span>Querying...</span>
                ) : (
                  <>
                    <span>Ask</span>
                    <Send className="w-3 h-3" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {queryError && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{queryError}</span>
          </div>
        )}

        {queryResult && (
          <div className="p-4 rounded-lg bg-slate-900/90 border border-blue-500/30 space-y-2 animate-in fade-in">
            <div className="flex items-center gap-2 text-xs font-semibold text-blue-400">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Grounded Document Answer</span>
            </div>
            
            <div className="text-xs leading-relaxed text-slate-200 whitespace-pre-line bg-slate-950/60 p-3.5 rounded border border-slate-800">
              {queryResult.answer}
            </div>
          </div>
        )}
      </div>

      {/* Documents Table */}
      <div className="rounded-xl bg-[#0e1420] border border-slate-800 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Indexed Documents</h3>
          <span className="text-xs text-slate-500 font-mono">{documents.length} Files</span>
        </div>

        {documents.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No documents uploaded yet. Upload project requirements or notes to test the RAG agent workflow.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {documents.map((doc) => (
              <div key={doc.id} className="p-4 flex items-center justify-between hover:bg-slate-900/50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                    <FileText className="w-4 h-4 text-blue-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-slate-200">{doc.filename}</h4>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                      <span>•</span>
                      <span className="text-emerald-400 font-mono">{doc.chunk_count} Chunks</span>
                      <span>•</span>
                      <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-2 rounded-lg hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition-colors"
                  title="Delete Document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

