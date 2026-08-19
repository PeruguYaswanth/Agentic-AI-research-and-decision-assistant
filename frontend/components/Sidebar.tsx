'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, MessageSquareText, FileText, History, HelpCircle } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Overview', icon: LayoutDashboard },
    { href: '/research', label: 'Research Studio', icon: MessageSquareText },
    { href: '/documents', label: 'Knowledge Base (RAG)', icon: FileText },
    { href: '/history', label: 'Research History', icon: History },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-[#0d131f] flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t border-slate-800/80 m-4 rounded-xl bg-slate-900/60 border">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-1">
          <HelpCircle className="w-3.5 h-3.5 text-blue-400" />
          <span>Agent Capabilities</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          Autonomously plans, retrieves web & RAG evidence, synthesizes, and self-validates decisions.
        </p>
      </div>
    </aside>
  );
}
