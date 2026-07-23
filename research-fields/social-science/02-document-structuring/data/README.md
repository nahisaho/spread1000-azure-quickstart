# data/

This directory holds:

- **Generated demo PDFs** (`demo-court.pdf`, `demo-factory.pdf`, `demo-factory-scanned.pdf`) — created by [`../scripts/generate_demo_pdfs.py`](../scripts/generate_demo_pdfs.py). All **completely fictional** (CC0), do NOT contain real persons, companies, cases, or addresses.
- **Expected extractions** (`*.answer.json`) — hand-authored ground truth used to validate your pipeline.
- **`output/`** — Written by [`../src/extract.py`](../src/extract.py). Contains:
  - `<name>.json` — Extracted structured JSON
  - `<name>.markdown.txt` — Document Intelligence Markdown intermediate (debugging)
  - `<name>.manifest.json` — Reproducibility metadata (model, fingerprint, tokens, cost)

`*.pdf`, `output/`, and `.env` are `.gitignore`d.

## Bring your own document

Place your PDF in `data/` and run:

```bash
python src/extract.py --input data/my.pdf --schema court --output data/output/my.json
```

**Before uploading real documents**, read [`../docs/06-ethics-and-limits.md`](../docs/06-ethics-and-limits.md) about copyright and PII masking.
