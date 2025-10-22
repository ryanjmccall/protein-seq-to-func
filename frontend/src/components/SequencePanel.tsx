'use client';

import { useMemo, useState } from 'react';

interface SequencePanelProps {
  title?: string;
  subtitle?: string;
  sequence?: string;
  isLoading?: boolean;
  error?: string | null;
  onCopyFallbackText?: string;
}

const GROUP_SIZE = 10;
const LINE_GROUPS = 6;

function chunkSequence(sequence: string): string[] {
  const normalized = sequence.replace(/[^A-Za-z]/g, '').toUpperCase();
  if (!normalized) {
    return [];
  }

  const grouped = normalized.match(new RegExp(`.{1,${GROUP_SIZE}}`, 'g')) ?? [];
  const lines: string[] = [];

  for (let i = 0; i < grouped.length; i += LINE_GROUPS) {
    lines.push(grouped.slice(i, i + LINE_GROUPS).join(' '));
  }

  return lines;
}

export default function SequencePanel({
  title = 'Sequence',
  subtitle,
  sequence,
  isLoading = false,
  error = null,
  onCopyFallbackText = 'Sequence unavailable',
}: SequencePanelProps) {
  const [copied, setCopied] = useState(false);

  const formattedLines = useMemo(() => {
    if (!sequence) {
      return [];
    }
    return chunkSequence(sequence);
  }, [sequence]);

  const residueCount = sequence ? sequence.replace(/[^A-Za-z]/g, '').length : 0;

  async function handleCopy() {
    const textToCopy = sequence?.replace(/\s+/g, '') || onCopyFallbackText;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="rounded-3xl border border-[var(--border-subtle)] bg-white/85 p-6 shadow-[var(--shadow-soft)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--accent-primary)]">
            {title}
          </p>
          {subtitle && (
            <p className="mt-1 text-sm font-medium text-[var(--foreground-muted)]">
              {subtitle}
            </p>
          )}
        </div>
        <button
          type="button"
          className="rounded-full border border-[var(--accent-primary)] px-3 py-1 text-xs font-medium text-[var(--accent-primary)] transition-colors hover:bg-[var(--accent-primary)] hover:text-white"
          onClick={handleCopy}
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      {isLoading && (
        <div className="mt-6 rounded-2xl border border-dashed border-[var(--border-subtle)] bg-white px-4 py-6 text-center text-sm text-[var(--foreground-muted)]">
          Fetching sequence…
        </div>
      )}

      {!isLoading && error && (
        <div className="mt-6 rounded-2xl border border-[var(--border-color)] bg-white px-4 py-6 text-center text-sm text-[var(--error)]">
          {error}
        </div>
      )}

      {!isLoading && !error && formattedLines.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-[var(--border-subtle)] bg-white px-4 py-6 text-center text-sm text-[var(--foreground-muted)]">
          Sequence not available.
        </div>
      )}

      {!isLoading && !error && formattedLines.length > 0 && (
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between text-xs uppercase tracking-[0.25em] text-[var(--foreground-subtle)]">
            <span>Residues</span>
            <span>{residueCount}</span>
          </div>
          <pre className="max-h-[360px] overflow-auto rounded-2xl border border-[var(--border-subtle)] bg-white px-4 py-5 text-sm font-mono leading-relaxed text-[var(--foreground)]">
            {formattedLines.map((line, index) => (
              <div key={index} className="tabular-nums">
                {line}
              </div>
            ))}
          </pre>
        </div>
      )}
    </div>
  );
}
