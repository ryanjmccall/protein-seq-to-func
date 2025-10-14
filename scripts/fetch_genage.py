"""
Small CLI utility for fetching and optionally saving the GenAge dataset.
"""

from __future__ import annotations

from pathlib import Path

from scripts.fetch_data import fetch_genage


def main() -> None:
    url = "https://genomics.senescence.info/genes/human_genes.zip"
    genage_data = fetch_genage(url)

    if genage_data is None:
        return

    print("\n--- GenAge Data (First 5 Rows) ---")
    print(genage_data.head())

    output_path = Path("data/raw/genage_human.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    genage_data.to_csv(output_path, index=False)
    print(f"\nData saved to {output_path}")


if __name__ == "__main__":
    main()
