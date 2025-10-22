import fs from "fs";
import path from "path";
import Link from "next/link";

type ProteinSummary = {
  slug: string;
  title: string;
  synopsis: string;
  referenceCount: number;
};

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }

  const truncated = text.slice(0, maxLength).replace(/\s+\S*$/, "");
  return `${truncated}…`;
}

function extractSynopsis(markdown: string): string {
  const withoutHeading = markdown.replace(/^#\s+.*$/m, "").trim();
  const paragraphs = withoutHeading
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.replace(/\s+/g, " ").trim())
    .filter(Boolean);

  return paragraphs[0] ?? "Structured protein intelligence, distilled.";
}

function getProteinSummaries(): ProteinSummary[] {
  const dataDirectory = path.join(process.cwd(), "public", "data");

  let files: string[] = [];
  try {
    files = fs.readdirSync(dataDirectory);
  } catch {
    return [];
  }

  return files
    .filter((file) => file.endsWith(".md") && !file.endsWith("_backup.md"))
    .map((file) => {
      const filePath = path.join(dataDirectory, file);
      const contents = fs.readFileSync(filePath, "utf-8");
      const headingMatch = contents.match(/^#\s+(.*)$/m);
      const title =
        headingMatch?.[1].trim() ?? file.replace(/\.md$/, "").toUpperCase();

      const synopsis = truncate(extractSynopsis(contents), 220);
      const referenceCount = (contents.match(/PMID:/g) ?? []).length;

      return {
        slug: file.replace(/\.md$/, ""),
        title,
        synopsis,
        referenceCount,
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));
}

export default function Home() {
  const proteins = getProteinSummaries();
  const featured = proteins[0];
  const remaining = proteins.slice(1);
  const totalReferences = proteins.reduce(
    (sum, protein) => sum + protein.referenceCount,
    0,
  );

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="border-b border-[var(--border-color)] bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.45em] text-[var(--accent-primary)]">
              protein atlas
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Sequence insights for translational teams.
            </h1>
            <p className="mt-3 max-w-xl text-base text-[var(--foreground-muted)]">
              We turn raw protein knowledge into navigable dossiers linking structure,
              regulation, interactions, and clinical signals.
            </p>
          </div>
          {featured && (
            <Link
              href={`/protein/${featured.slug}`}
              className="inline-flex items-center gap-2 rounded-full border border-[var(--accent-primary)] px-5 py-2 text-sm font-medium text-[var(--accent-primary)] transition-colors hover:bg-[var(--accent-primary)] hover:text-white"
            >
              Browse {featured.title}
              <span aria-hidden>→</span>
            </Link>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-6 py-12">
        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--background-elevated)] p-6 shadow-[var(--shadow-soft)]">
            <p className="text-sm text-[var(--foreground-subtle)]">Catalogue</p>
            <p className="mt-2 text-3xl font-semibold">{proteins.length}</p>
            <p className="mt-2 text-sm text-[var(--foreground-muted)]">
              curated protein monographs
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--background-elevated)] p-6 shadow-[var(--shadow-soft)]">
            <p className="text-sm text-[var(--foreground-subtle)]">Evidence</p>
            <p className="mt-2 text-3xl font-semibold">{totalReferences}</p>
            <p className="mt-2 text-sm text-[var(--foreground-muted)]">
              citations across the library
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--border-color)] bg-gradient-to-br from-white via-white to-[var(--accent-soft)] p-6 shadow-[var(--shadow-soft)]">
            <p className="text-sm text-[var(--foreground-subtle)]">Focus</p>
            <p className="mt-2 text-3xl font-semibold">Sequence → function</p>
            <p className="mt-2 text-sm text-[var(--foreground-muted)]">
              map sequence variation to therapeutic relevance
            </p>
          </div>
        </section>

        {featured && (
          <section className="mt-12">
            <h2 className="text-xs font-semibold uppercase tracking-[0.45em] text-[var(--foreground-subtle)]">
              Featured Article
            </h2>
            <Link
              href={`/protein/${featured.slug}`}
              className="mt-4 block rounded-3xl border border-[var(--border-subtle)] bg-white/80 px-8 py-10 shadow-[var(--shadow-soft)] transition-transform hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-[var(--accent-primary)]">
                    {featured.slug.toUpperCase()}
                  </p>
                  <h3 className="mt-2 text-3xl font-semibold tracking-tight">
                    {featured.title}
                  </h3>
                  <p className="mt-4 max-w-2xl text-base leading-relaxed text-[var(--foreground-muted)]">
                    {featured.synopsis}
                  </p>
                </div>
                <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--background)] px-4 py-2 text-sm font-medium text-[var(--foreground-muted)]">
                  {featured.referenceCount} supporting references
                </div>
              </div>
            </Link>
          </section>
        )}

        <section className="mt-12 space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.45em] text-[var(--foreground-subtle)]">
            Protein Library
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {(featured ? remaining : proteins).map((protein) => (
              <Link
                key={protein.slug}
                href={`/protein/${protein.slug}`}
                className="group block rounded-2xl border border-[var(--border-color)] bg-[var(--background-elevated)] p-6 shadow-[var(--shadow-soft)] transition-transform hover:-translate-y-1 hover:shadow-lg"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.35em] text-[var(--accent-primary)]">
                      {protein.slug.toUpperCase()}
                    </p>
                    <h3 className="mt-2 text-xl font-semibold">{protein.title}</h3>
                  </div>
                  <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent-primary)]">
                    {protein.referenceCount} refs
                  </span>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-[var(--foreground-muted)]">
                  {protein.synopsis}
                </p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-[var(--accent-primary)]">
                  Read article
                  <span aria-hidden className="transition-transform group-hover:translate-x-1">
                    →
                  </span>
                </span>
              </Link>
            ))}
            {proteins.length === 0 && (
              <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--background-elevated)] px-6 py-8 text-[var(--foreground-muted)]">
                No protein articles found yet.
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="mt-12 border-t border-[var(--border-color)] bg-white/70 backdrop-blur">
        <div className="mx-auto max-w-5xl px-6 py-8 text-sm text-[var(--foreground-muted)]">
          Built for focused protein insight by the West Coast Vectors.
        </div>
      </footer>
    </div>
  );
}
