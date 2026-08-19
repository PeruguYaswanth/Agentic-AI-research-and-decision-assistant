'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { History, Bot, BookOpen, Layers, ArrowUpRight, Calendar, Sparkles } from 'lucide-react';
import { getHistory, getSession, HistoryItem, ResearchResponse } from '@/lib/api';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import AgentTimeline from '@/components/AgentTimeline';
import SourceDrawer from '@/components/SourceDrawer';

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedSession, setSelectedSession] = useState<ResearchResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getHistory();
        setHistory(data);
        if (data.length > 0) {
          loadSession(data[0].session_id);
        }
      } catch (e) {
        console.error('Failed to load history', e);
      }
    };
    fetchHistory();
  }, []);

  const loadSession = async (sessionId: string) => {
    setIsLoadingDetail(true);
    try {
      const data = await getSession(sessionId);
      setSelectedSession(data);
    } catch (e) {
      console.error('Failed to load session detail', e);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <History className="w-5 h-5 text-indigo-400" />
          <span>Research Session History</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Review previous multi-agent research runs, execution graphs, evidence sources, and generated decision reports.
        </p>
      </div>

      {history.length === 0 ? (
        <div className="rounded-xl bg-[#0e1420] border border-slate-800 p-12 text-center space-y-3">
          <Bot className="w-10 h-10 mx-auto text-slate-600" />
          <h3 className="text-sm font-semibold text-slate-200">No Research History Yet</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Once you execute research queries in the Research Studio, their execution graphs and reports will be saved here.
          </p>
          <button
            onClick={() => router.push('/research')}
            className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold"
          >
            <span>Start First Session</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Sessions List */}
          <div className="lg:col-span-4 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Past Sessions ({history.length})
            </div>
            <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
              {history.map((item) => {
                const isSelected = selectedSession?.session_id === item.session_id;
                return (
                  <div
                    key={item.session_id}
                    onClick={() => loadSession(item.session_id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-600/10 border-blue-500/30 shadow-sm'
                        : 'bg-slate-900/60 border-slate-800 hover:bg-slate-900 hover:border-slate-700'
                    }`}
                  >
                    <h4 className={`text-xs font-medium line-clamp-2 ${isSelected ? 'text-blue-400' : 'text-slate-200'}`}>
                      {item.question}
                    </h4>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                      <span className="font-mono text-emerald-400">
                        {item.sources_count} Sources
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Session Details View */}
          <div className="lg:col-span-8 space-y-4">
            {isLoadingDetail ? (
              <div className="p-12 rounded-xl bg-[#0e1420] border border-slate-800 text-center text-xs text-slate-500">
                Loading session details...
              </div>
            ) : selectedSession ? (
              <div className="space-y-6">
                {/* Session Header Card */}
                <div className="p-5 rounded-xl bg-[#0e1420] border border-slate-800 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Inquiry</div>
                      <h2 className="text-base font-semibold text-white mt-0.5">{selectedSession.question}</h2>
                    </div>
                    <button
                      onClick={() => router.push(`/research?q=${encodeURIComponent(selectedSession.question)}`)}
                      className="px-3 py-1.5 rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400 hover:bg-blue-600/20 text-xs font-medium flex items-center gap-1 shrink-0 transition-colors"
                    >
                      <span>Re-run in Studio</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Final Answer Report */}
                <div className="p-6 rounded-xl bg-[#0e1420] border border-slate-800">
                  <MarkdownRenderer content={selectedSession.final_answer} />
                </div>

                {/* Timeline & Sources */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#0e1420] border border-slate-800">
                    <AgentTimeline logs={selectedSession.execution_logs} isResearching={false} plan={selectedSession.plan} />
                  </div>
                  <div className="p-4 rounded-xl bg-[#0e1420] border border-slate-800">
                    <SourceDrawer sources={selectedSession.sources} />
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
