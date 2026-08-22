'use client';

import React from 'react';
import { SourceItem } from '@/lib/api';
import { Globe, FileText, ExternalLink, BookOpen, Calendar, ShieldCheck } from 'lucide-react';

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
          <span>Verified Sources & Evidence</span>
        </h3>
        <span className="text-xs font-mono text-slate-400">
          {sources.length} Total
        </span>
      </div>

      {sources.length === 0 ? (
        <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
          Verified sources from live web pages and internal knowledge bases will appear here.
        </div>
      ) : (
        <div className="space-y-4">
          {webSources.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-blue-400" />
                <span>Live Web Sources ({webSources.length})</span>
              </div>
              <div className="space-y-2.5">
                {webSources.map((src, i) => (
                  <div key={i} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            {src.publisher || 'Web'}
                          </span>
                          {src.published_date && (
                            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                              <Calendar className="w-2.5 h-2.5" />
                              {src.published_date}
                            </span>
                          )}
                          {src.authority_score && (
                            <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-0.5">
                              <ShieldCheck className="w-2.5 h-2.5" />
                              {Math.round(src.authority_score * 100)}% Auth
                            </span>
                          )}
                        </div>
                        <h4 className="text-xs font-semibold text-slate-200 mt-1 leading-snug">
                          {src.title}
                        </h4>
                      </div>
                      {src.url && src.url !== '#' && (
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-blue-400 transition-colors p-1"
                          title="Open live source"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                    {src.snippet && (
                      <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed border-t border-slate-800/60 pt-1.5">
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
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-emerald-400" />
                <span>Internal Knowledge Base Chunks ({ragSources.length})</span>
              </div>
              <div className="space-y-2.5">
                {ragSources.map((src, i) => (
                  <div key={i} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {src.publisher || 'Document'}
                      </span>
                      <h4 className="text-xs font-medium text-emerald-300 flex-1 truncate">
                        {src.title}
                      </h4>
                    </div>
                    {src.snippet && (
                      <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed border-t border-slate-800/60 pt-1.5">
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
