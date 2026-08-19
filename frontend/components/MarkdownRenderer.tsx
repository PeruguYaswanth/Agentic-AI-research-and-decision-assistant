'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed space-y-4">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-xl font-bold text-slate-100 border-b border-slate-800 pb-2 mt-4 mb-3" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-base font-semibold text-slate-100 mt-5 mb-2 flex items-center gap-2" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-sm font-semibold text-blue-400 mt-4 mb-1.5" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mt-3 mb-1" {...props} />
          ),
          p: ({ node, ...props }) => <p className="text-slate-300 leading-relaxed mb-3" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-1 text-slate-300 mb-3" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal pl-5 space-y-1 text-slate-300 mb-3" {...props} />,
          li: ({ node, ...props }) => <li className="pl-1" {...props} />,
          strong: ({ node, ...props }) => <strong className="font-semibold text-slate-100" {...props} />,
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-2 border-blue-500/50 pl-3 italic text-slate-400 my-2" {...props} />
          ),
          code: ({ node, className, children, ...props }) => {
            const isInline = !className;
            return isInline ? (
              <code className="bg-slate-800/80 text-blue-300 font-mono text-xs px-1.5 py-0.5 rounded border border-slate-700/50" {...props}>
                {children}
              </code>
            ) : (
              <pre className="bg-[#0b0f17] border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-300 overflow-x-auto my-3">
                <code {...props}>{children}</code>
              </pre>
            );
          },
          a: ({ node, ...props }) => (
            <a
              className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors font-medium"
              target="_blank"
              rel="noreferrer"
              {...props}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
