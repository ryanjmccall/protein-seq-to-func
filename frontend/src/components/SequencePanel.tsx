'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState } from 'react';

const SeqViz = dynamic(async () => {
  const mod = await import('seqviz');
  return mod.SeqViz;
}, {
  ssr: false,
  loading: () => (
    <div className="flex h-[320px] w-full items-center justify-center rounded-2xl border border-[var(--border-subtle)] bg-white text-sm text-[var(--foreground-muted)] shadow-[var(--shadow-soft)]">
      Initializing viewer…
    </div>
  ),
});

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
  const [viewMode, setViewMode] = useState<'viz' | 'text'>('viz');

  const normalizedSequence = useMemo(() => sequence?.replace(/[^A-Za-z]/g, '').toUpperCase() ?? '', [sequence]);

  const formattedLines = useMemo(() => {
    if (!sequence) {
      return [];
    }
    return chunkSequence(sequence);
  }, [sequence]);

  const residueCount = normalizedSequence.length;

  async function handleCopy() {
    const textToCopy = normalizedSequence || onCopyFallbackText;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  const sequenceUnavailable = !isLoading && !error && residueCount === 0;

  const canShowViz = residueCount > 0;

  return (
    <div className="flex h-full flex-col rounded-3xl border border-[var(--border-subtle)] bg-white/85 p-6 shadow-[var(--shadow-soft)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
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
        <div className="flex items-center gap-2">
          {canShowViz && (
            <div className="flex rounded-full bg-[var(--accent-soft)] p-1 text-xs font-medium text-[var(--accent-primary)]">
              <button
                type="button"
                onClick={() => setViewMode('viz')}
                className={`rounded-full px-3 py-1 transition-colors ${
                  viewMode === 'viz'
                    ? 'bg-[var(--accent-primary)] text-white'
                    : 'text-[var(--accent-primary)]'
                }`}
              >
                Viewer
              </button>
              <button
                type="button"
                onClick={() => setViewMode('text')}
                className={`rounded-full px-3 py-1 transition-colors ${
                  viewMode === 'text'
                    ? 'bg-[var(--accent-primary)] text-white'
                    : 'text-[var(--accent-primary)]'
                }`}
              >
                Text
              </button>
            </div>
          )}
          <button
            type="button"
            className="rounded-full border border-[var(--accent-primary)] px-3 py-1 text-xs font-medium text-[var(--accent-primary)] transition-colors hover:bg-[var(--accent-primary)] hover:text-white"
            onClick={handleCopy}
            disabled={isLoading}
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
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

      {sequenceUnavailable && (
        <div className="mt-6 rounded-2xl border border-dashed border-[var(--border-subtle)] bg-white px-4 py-6 text-center text-sm text-[var(--foreground-muted)]">
          Sequence not available.
        </div>
      )}

      {!isLoading && !error && residueCount > 0 && (
        <div className="mt-6 flex flex-1 flex-col space-y-4">
          <div className="flex items-center justify-between text-xs uppercase tracking-[0.25em] text-[var(--foreground-subtle)]">
            <span>Residues</span>
            <span>{residueCount}</span>
          </div>

          {viewMode === 'viz' && (
            <div className="relative flex-1 min-h-[360px] w-full overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-white shadow-[var(--shadow-soft)]">
              <SeqViz
                name={title}
                primers={[]}
                seq={normalizedSequence}
                viewer="linear"
                style={{ height: '100%', width: '100%' }}
                showComplement={false}
                disableExternalFonts
                zoom={{ linear: residueCount > 400 ? 50 : 80 }}
              />
            </div>
          )}

          {viewMode === 'text' && (
            <pre className="flex-1 overflow-auto rounded-2xl border border-[var(--border-subtle)] bg-white px-4 py-5 text-sm font-mono leading-relaxed text-[var(--foreground)]">
              {formattedLines.map((line, index) => (
                <div key={index} className="tabular-nums">
                  {line}
                </div>
              ))}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
