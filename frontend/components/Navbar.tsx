'use client';

import React from 'react';
import Link from 'next/link';
import { Bot, Sparkles, Layers, Cpu } from 'lucide-react';

export default function Navbar() {
  return (
    <header className="h-16 border-b border-slate-800 bg-[#0d131f]/90 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <Link href="/" className="font-semibold text-slate-100 hover:text-blue-400 transition-colors flex items-center gap-2">
            <span>Agentic AI Research</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-mono">
              Decision Assistant
            </span>
          </Link>
        </div>
      </div>

      <div className="hidden md:flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>LangGraph Cyclic Engine</span>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Self-Validating Loop</span>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          <span>Dual Web + RAG</span>
        </div>
      </div>
    </header>
  );
}
