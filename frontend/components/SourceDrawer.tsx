'use client';

import React from 'react';
import { SourceItem } from '@/lib/api';
import { Globe, FileText, ExternalLink, BookOpen } from 'lucide-react';

interface SourceDrawerProps {
  sources: SourceItem[];
}

export default function SourceDrawer({ sources }: SourceDrawerProps) {
  const webSources = sources.filter((s) => s.source === 'web');
  const ragSources = sources.filter((s) => s.source === 'rag');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-emerald-400" />
          <span>Retrieved Sources & Evidence</span>
        </h3>
        <span className="text-xs font-mono text-slate-400">
          {sources.length} Total
        </span>
      </div>

      {sources.length === 0 ? (
        <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
          Sources from web search and uploaded document RAG will appear here.
        </div>
      ) : (
        <div className="space-y-3">
          {webSources.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Globe className="w-3 h-3 text-blue-400" />
                <span>Web Sources ({webSources.length})</span>
              </div>
              <div className="space-y-2">
                {webSources.map((src, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-xs font-medium text-blue-400 line-clamp-1">
                        {src.title}
                      </h4>
                      {src.url && src.url !== '#' && (
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-500 hover:text-slate-300"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                    {src.snippet && (
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        {src.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {ragSources.length > 0 && (
            <div className="pt-2">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <FileText className="w-3 h-3 text-emerald-400" />
                <span>Internal Document Chunks ({ragSources.length})</span>
              </div>
              <div className="space-y-2">
                {ragSources.map((src, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-colors">
                    <h4 className="text-xs font-medium text-emerald-400 line-clamp-1">
                      {src.title}
                    </h4>
                    {src.snippet && (
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-3 leading-relaxed">
                        {src.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
