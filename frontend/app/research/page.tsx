'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, Bot, Sparkles, BookOpen, Layers, Copy, Check, RotateCcw, AlertCircle, ShieldCheck, ShieldAlert } from 'lucide-react';
import AgentTimeline from '@/components/AgentTimeline';
import SourceDrawer from '@/components/SourceDrawer';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import { streamResearch, ExecutionStep, SourceItem } from '@/lib/api';

function ResearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';

  const [question, setQuestion] = useState(initialQuery);
  const [activeQuestion, setActiveQuestion] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [logs, setLogs] = useState<ExecutionStep[]>([]);
  const [plan, setPlan] = useState<string[]>([]);
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [finalAnswer, setFinalAnswer] = useState<string>('');
  const [confidenceLevel, setConfidenceLevel] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'sources'>('timeline');
  const [copied, setCopied] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const initialRan = useRef(false);

  const handleStartResearch = async (customQuery?: string) => {
    const q = customQuery || question;
    if (!q.trim() || isResearching) return;

    setActiveQuestion(q);
    setIsResearching(true);
    setErrorMsg(null);
    setLogs([]);
    setPlan([]);
    setSources([]);
    setFinalAnswer('');
    setConfidenceLevel(null);

    await streamResearch(q, undefined, {
      onStatus: (step) => {
        setLogs((prev) => [...prev, step]);
      },
      onPlan: (newPlan) => {
        setPlan(newPlan);
      },
      onSources: (newSources) => {
        setSources(newSources);
      },
      onFinalAnswer: (data) => {
        setFinalAnswer(data.final_answer);
        if (data.confidence_level) {
          setConfidenceLevel(data.confidence_level);
        }
        if (data.sources && data.sources.length > 0) {
          setSources(data.sources);
        }
      },
      onError: (err) => {
        setErrorMsg(err.message || 'An error occurred during research graph execution.');
        setIsResearching(false);
      },
      onComplete: () => {
        setIsResearching(false);
      },
    });
  };

  useEffect(() => {
    if (initialQuery && !initialRan.current) {
      initialRan.current = true;
      handleStartResearch(initialQuery);
    }
  }, [initialQuery]);

  const handleCopyReport = () => {
    if (!finalAnswer) return;
    navigator.clipboard.writeText(finalAnswer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bot className="w-5 h-5 text-blue-400" />
            <span>Research & Decision Studio</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Autonomous multi-agent research with live web page parsing, evidence cross-verification, and claim-level validation.
          </p>
        </div>

        {finalAnswer && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyReport}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-xs font-medium text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Report'}</span>
            </button>
            <button
              onClick={() => {
                setFinalAnswer('');
                setLogs([]);
                setPlan([]);
                setSources([]);
                setActiveQuestion('');
                setConfidenceLevel(null);
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-xs font-medium text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>
        )}
      </div>

      {/* Input Query Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleStartResearch();
        }}
        className="relative"
      >
        <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/90 border border-slate-800 focus-within:border-blue-500/50 shadow-lg">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What is the current price of Bitcoin? Or: Who is the current CEO of OpenAI?"
            className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
            disabled={isResearching}
          />
          <button
            type="submit"
            disabled={!question.trim() || isResearching}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold flex items-center gap-2 transition-all shrink-0"
          >
            {isResearching ? (
              <>
                <Sparkles className="w-3.5 h-3.5 animate-spin" />
                <span>Researching...</span>
              </>
            ) : (
              <>
                <span>Run Agent</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </form>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Studio Viewport */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Final Report / Response Output */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-xl bg-[#0e1420] border border-slate-800 p-5 min-h-[480px]">
            {activeQuestion && (
              <div className="mb-4 pb-3 border-b border-slate-800 flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Active Inquiry</div>
                  <div className="text-sm font-medium text-slate-200 mt-1">{activeQuestion}</div>
                </div>
                {confidenceLevel && (
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border ${
                    confidenceLevel === 'HIGH'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : confidenceLevel === 'MEDIUM'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                    <ShieldCheck className="w-3 h-3" />
                    {confidenceLevel} CONFIDENCE
                  </span>
                )}
              </div>
            )}

            {finalAnswer ? (
              <MarkdownRenderer content={finalAnswer} />
            ) : isResearching ? (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400 animate-pulse">
                  <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-semibold text-slate-200">Autonomous Evidence Research in Progress</h3>
                <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                  The LangGraph multi-agent orchestrator is querying live sources, scraping web pages, cross-verifying evidence, and validating factual claims.
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-2 text-slate-500">
                <Bot className="w-10 h-10 text-slate-600" />
                <p className="text-xs">Enter a research query above to begin real-time evidence retrieval.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Dynamic Agent Timeline & Sources Tabs */}
        <div className="lg:col-span-5 space-y-4">
          {/* Tab Switcher */}
          <div className="flex rounded-lg bg-slate-900/80 p-1 border border-slate-800">
            <button
              onClick={() => setActiveTab('timeline')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md flex items-center justify-center gap-1.5 transition-colors ${
                activeTab === 'timeline'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Execution Timeline ({logs.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('sources')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md flex items-center justify-center gap-1.5 transition-colors ${
                activeTab === 'sources'
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Verified Sources ({sources.length})</span>
            </button>
          </div>

          <div className="rounded-xl bg-[#0e1420] border border-slate-800 p-4 max-h-[640px] overflow-y-auto">
            {activeTab === 'timeline' ? (
              <AgentTimeline logs={logs} isResearching={isResearching} plan={plan} />
            ) : (
              <SourceDrawer sources={sources} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ResearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading Research Studio...</div>}>
      <ResearchContent />
    </Suspense>
  );
}
