'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bot, ArrowRight, Sparkles, Layers, ShieldCheck, Database, Search, FileText, CheckCircle2 } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();

  const handleLaunchScenario = (query: string) => {
    router.push(`/research?q=${encodeURIComponent(query)}`);
  };

  const scenarios = [
    {
      title: "Framework Architecture Comparison",
      query: "Should I use FastAPI or Django for building an AI-powered resume screening application?",
      tag: "Web Research + Technical Comparison",
      icon: Layers,
      color: "border-blue-500/30 text-blue-400 bg-blue-500/10"
    },
    {
      title: "Internal Document Decision (RAG)",
      query: "Based on my uploaded project requirements, should I use ChromaDB or FAISS for my RAG application?",
      tag: "ChromaDB RAG + Requirement Analysis",
      icon: Database,
      color: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
    },
    {
      title: "Latest Framework Updates",
      query: "What are the latest important changes in LangGraph that I should know before building a production agent?",
      tag: "Fresh External Search + Source Citations",
      icon: Search,
      color: "border-purple-500/30 text-purple-400 bg-purple-500/10"
    }
  ];

  return (
    <div className="space-y-10 py-4">
      {/* Hero Section */}
      <div className="relative rounded-2xl bg-gradient-to-b from-[#111928] to-[#0d131f] border border-slate-800 p-8 md:p-12 overflow-hidden">
        <div className="max-w-3xl space-y-4 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Autonomous StateGraph Multi-Agent Engine</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-white leading-tight">
            Agentic AI Research & <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-emerald-400">
              Decision Assistant
            </span>
          </h1>
          <p className="text-slate-300 text-base md:text-lg leading-relaxed max-w-2xl">
            Accepts complex inquiries, formulates autonomous research plans, queries external web sources and uploaded documents via ChromaDB, synthesizes evidence, and self-validates decisions before answering.
          </p>
          <div className="pt-2 flex flex-wrap gap-4">
            <Link
              href="/research"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-all shadow-lg shadow-blue-600/20"
            >
              <span>Start Research Session</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/documents"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700 text-slate-200 text-sm font-medium transition-all"
            >
              <FileText className="w-4 h-4 text-emerald-400" />
              <span>Manage Documents (RAG)</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Demo Scenarios Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Preset Demonstration Scenarios</h2>
            <p className="text-xs text-slate-400">Click any scenario to immediately trigger autonomous graph execution</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {scenarios.map((sc, i) => {
            const Icon = sc.icon;
            return (
              <div
                key={i}
                onClick={() => handleLaunchScenario(sc.query)}
                className="group cursor-pointer rounded-xl bg-slate-900/70 border border-slate-800 p-5 hover:border-blue-500/40 hover:bg-slate-900/90 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${sc.color}`}>
                      {sc.tag}
                    </span>
                    <Icon className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200 group-hover:text-blue-300 transition-colors mb-2">
                    {sc.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                    "{sc.query}"
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-blue-400 font-medium">
                  <span>Run Autonomous Agent</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Architecture Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-3">
            <Layers className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">LangGraph Cyclic State</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Shared state dictionary across conditional routing edges, dynamic branching, and multi-node execution.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-3">
            <Database className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">Local ChromaDB RAG</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Upload PDFs/documents for text splitting, embedding generation, and metadata-grounded similarity retrieval.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-3">
            <Search className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">Tavily Web Research</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Queries live web sources for up-to-date benchmarks, API specifications, and authoritative technical documentation.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-3">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">Self-Validating Loop</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            QA validation evaluates claims against collected evidence, looping back if information is insufficient.
          </p>
        </div>
      </div>
    </div>
  );
}
