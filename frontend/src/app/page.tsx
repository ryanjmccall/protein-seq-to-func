import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-[var(--background)] flex flex-col">
      {/* Header */}
      <header className="border-b border-[var(--border-color)] bg-[var(--background-elevated)]">
        <div className="max-w-[1200px] mx-auto px-8 py-4">
          <h1 className="text-3xl font-bold text-[var(--foreground)]">WCVikiCrow (tesitng CI)</h1>
          <p className="text-[var(--foreground-muted)] text-sm mt-1">
            Protein Sequence-to-Function Explorer
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-[1200px] mx-auto px-8 py-16">
        <div className="space-y-12">
          {/* Hero Section */}
          <div className="text-center space-y-4">
            <h2 className="text-5xl font-bold text-[var(--foreground)]">
              Explore Protein Sequence-to-Function Relationships
            </h2>
            <p className="text-xl text-[var(--foreground-muted)] max-w-3xl mx-auto">
              A comprehensive database mapping protein modifications to their functional
              consequences, with a focus on aging-related proteins and therapeutic targets.
            </p>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 mt-12">
            <div className="border border-[var(--border-color)] rounded-lg p-6 bg-[var(--background-card)]">
              <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
                Sequence-to-Function
              </h3>
              <p className="text-[var(--foreground-muted)]">
                Detailed mappings of protein modifications to their functional impacts,
                backed by scientific literature.
              </p>
            </div>

            <div className="border border-[var(--border-color)] rounded-lg p-6 bg-[var(--background-card)]">
              <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
                Small Molecule Interactions
              </h3>
              <p className="text-[var(--foreground-muted)]">
                Comprehensive data on drug and compound interactions with target proteins.
              </p>
            </div>

            <div className="border border-[var(--border-color)] rounded-lg p-6 bg-[var(--background-card)]">
              <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
                Clinical Significance
              </h3>
              <p className="text-[var(--foreground-muted)]">
                Disease associations and age-related phenotypes linked to protein variants.
              </p>
            </div>
          </div>

          {/* Demo Protein */}
          <div className="border border-[var(--border-color)] rounded-lg p-8 bg-[var(--background-elevated)] text-center">
            <h3 className="text-2xl font-semibold text-[var(--foreground)] mb-4">
              Example Protein Article
            </h3>
            <p className="text-[var(--foreground-muted)] mb-6">
              Explore GANAB (Glucosidase II Alpha Subunit), a protein involved in polycystic
              kidney disease and aging-related processes.
            </p>
            <Link
              href="/protein/GANAB"
              className="inline-block px-6 py-3 bg-[var(--accent-primary)] hover:bg-[var(--accent-primary-hover)] text-white font-semibold rounded-lg transition-colors"
            >
              View GANAB Protein Page
            </Link>
          </div>

          {/* Project Info */}
          <div className="border border-[var(--border-color)] rounded-lg p-6 bg-[var(--background-card)]">
            <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
              About This Project
            </h3>
            <p className="text-[var(--foreground-muted)] mb-4">
              This is a WikiCrow-inspired protein explorer built for the HackAging
              Sequence-to-Function challenge. The platform integrates data from multiple
              sources to provide comprehensive insights into protein function and its role
              in aging.
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-1 bg-[var(--accent-secondary)] text-white rounded text-sm">
                UniProt
              </span>
              <span className="px-3 py-1 bg-[var(--accent-secondary)] text-white rounded text-sm">
                GenAge
              </span>
              <span className="px-3 py-1 bg-[var(--accent-secondary)] text-white rounded text-sm">
                PubChem
              </span>
              <span className="px-3 py-1 bg-[var(--accent-secondary)] text-white rounded text-sm">
                PubMed
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border-color)] bg-[var(--background-elevated)] mt-16">
        <div className="max-w-[1200px] mx-auto px-8 py-6 text-center text-[var(--foreground-muted)] text-sm">
          <p>Built for HackAging 2025 - Sequence-to-Function Challenge</p>
        </div>
      </footer>
    </div>
  );
}
