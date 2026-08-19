'use client';

import React from 'react';
import { ExecutionStep } from '@/lib/api';
import { CheckCircle2, CircleDashed, AlertCircle, RefreshCw, Sparkles, Search, FileText, BrainCircuit, ShieldCheck, FileCheck } from 'lucide-react';

interface AgentTimelineProps {
  logs: ExecutionStep[];
  isResearching: boolean;
  plan?: string[];
}

export default function AgentTimeline({ logs, isResearching, plan }: AgentTimelineProps) {
  const getStepIcon = (name: string, status: string) => {
    if (status === 'retry') return <RefreshCw className="w-4 h-4 text-amber-400 animate-spin" />;
    if (status === 'completed') return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    if (status === 'in_progress') return <CircleDashed className="w-4 h-4 text-blue-400 animate-spin" />;
    if (status === 'failed') return <AlertCircle className="w-4 h-4 text-rose-400" />;

    const lower = name.toLowerCase();
    if (lower.includes('question') || lower.includes('analyzer')) return <Sparkles className="w-4 h-4 text-blue-400" />;
    if (lower.includes('web') || lower.includes('search')) return <Search className="w-4 h-4 text-indigo-400" />;
    if (lower.includes('rag') || lower.includes('document')) return <FileText className="w-4 h-4 text-emerald-400" />;
    if (lower.includes('analysis') || lower.includes('orchestrator')) return <BrainCircuit className="w-4 h-4 text-purple-400" />;
    if (lower.includes('validator')) return <ShieldCheck className="w-4 h-4 text-amber-400" />;
    return <FileCheck className="w-4 h-4 text-blue-400" />;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-blue-400" />
          <span>Agent Execution Timeline</span>
        </h3>
        {isResearching && (
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            Executing Graph...
          </span>
        )}
      </div>

      {logs.length === 0 && !isResearching && (
        <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
          Agent workflow actions and node transitions will appear here once research starts.
        </div>
      )}

      <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-800">
        {logs.map((step, idx) => (
          <div key={idx} className="relative group">
            <div className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center">
              {getStepIcon(step.step_name, step.status)}
            </div>
            <div className="bg-slate-900/70 border border-slate-800/90 rounded-lg p-3 hover:border-slate-700 transition-colors">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-xs font-medium text-slate-200">
                  {step.step_name}
                </span>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  step.status === 'completed'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : step.status === 'retry'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                }`}>
                  {step.status.toUpperCase()}
                </span>
              </div>
              {step.detail && (
                <p className="text-xs text-slate-400 leading-relaxed break-words">
                  {step.detail}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {plan && plan.length > 0 && (
        <div className="mt-4 p-3.5 rounded-lg bg-slate-900/50 border border-slate-800">
          <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
            <span>Formulated Research Plan</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">{plan.length} Steps</span>
          </div>
          <ul className="space-y-1.5 text-xs text-slate-400">
            {plan.map((step, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-300 font-mono text-[10px] flex items-center justify-center shrink-0 mt-0.5">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
