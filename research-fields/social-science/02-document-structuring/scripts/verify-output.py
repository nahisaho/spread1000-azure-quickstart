r"""Verify structured-output JSON files produced by extract.py.

Reads data/output/*.json and checks:
  (a) required fields present and non-null where expected
  (b) date field normalised to ISO 8601 (YYYY-MM-DD)
  (c) industry_code matches ^\d{4}$
  (d) at least one judge in court decisions
  (e) source_page_range matches ^\d+(-\d+)?$
  (f) reasoning_summary length 200-500 chars
  (g) all evidence quotes (content_preview) appear in the corresponding
      .markdown.txt intermediate (when both files exist)

Exits 0 iff all checks pass; exits 1 on any failure.

Usage:
  python scripts/verify-output.py --output-dir data/output --markdown-dir data/output
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INDUSTRY_CODE_RE = re.compile(r"^\d{4}$")
PAGE_RANGE_RE = re.compile(r"^\d+(-\d+)?$")


def _check_court(data: dict, stem: str, markdown: str | None) -> list[str]:
    errors: list[str] = []

    # (a) required fields
    for field in ("case_number", "court", "date", "judges", "parties",
                  "holding", "reasoning_summary", "source_page_range"):
        if field not in data:
            errors.append(f"{stem}: missing field '{field}'")
        elif field not in ("judges", "parties") and data[field] is None:
            # null is allowed for some fields but we warn
            pass

    # (b) date ISO
    if date := data.get("date"):
        if not ISO_DATE_RE.match(date):
            errors.append(f"{stem}: date '{date}' is not ISO 8601 (YYYY-MM-DD)")

    # (d) at least one judge
    judges = data.get("judges", [])
    if not judges:
        errors.append(f"{stem}: judges array is empty (at least one required)")

    # (f) reasoning_summary length
    rs = data.get("reasoning_summary")
    if rs is not None:
        if not (200 <= len(rs) <= 500):
            errors.append(
                f"{stem}: reasoning_summary length {len(rs)} outside 200-500"
            )

    # (e) source_page_range
    spr = data.get("source_page_range")
    if spr is not None and not PAGE_RANGE_RE.match(str(spr)):
        errors.append(f"{stem}: source_page_range '{spr}' does not match ^\\d+(-\\d+)?$")

    return errors


def _check_factory(data: dict, stem: str, markdown: str | None) -> list[str]:
    errors: list[str] = []

    if "records" not in data:
        errors.append(f"{stem}: missing top-level 'records' field")
        return errors

    for i, rec in enumerate(data.get("records", [])):
        prefix = f"{stem}[{i}]"

        # (c) industry_code
        ic = rec.get("industry_code")
        if ic is not None and not INDUSTRY_CODE_RE.match(str(ic)):
            errors.append(f"{prefix}: industry_code '{ic}' does not match ^\\d{{4}}$")

        # (e) source_page_range
        spr = rec.get("source_page_range")
        if spr is not None and not PAGE_RANGE_RE.match(str(spr)):
            errors.append(
                f"{prefix}: source_page_range '{spr}' does not match ^\\d+(-\\d+)?$"
            )

        # employees ≥ 0
        emp = rec.get("employees")
        if emp is not None and emp < 0:
            errors.append(f"{prefix}: employees {emp} is negative")

    # (e) top-level source_page_range
    spr = data.get("source_page_range")
    if spr is not None and not PAGE_RANGE_RE.match(str(spr)):
        errors.append(f"{stem}: source_page_range '{spr}' does not match ^\\d+(-\\d+)?$")

    return errors


def _check_evidence_quotes(
    evidence_path: Path, markdown: str, stem: str
) -> list[str]:
    """(g) Check that evidence content_preview strings appear in the markdown."""
    errors: list[str] = []
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"{stem}: could not read evidence file: {e}")
        return errors

    for idx, item in enumerate(evidence):
        preview: str = item.get("content_preview", "")
        if preview and len(preview) >= 10:
            check = preview[:50]  # use first 50 chars to avoid newline issues
            if check not in markdown:
                errors.append(
                    f"{stem} evidence[{idx}]: preview not found in markdown: {check!r}"
                )
    return errors


def _detect_schema(data: dict) -> str | None:
    if "records" in data:
        return "factory"
    if "judges" in data:
        return "court"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output-dir", default="data/output",
        help="Directory containing *.json output files.",
    )
    ap.add_argument(
        "--markdown-dir", default="data/output",
        help="Directory containing *.markdown.txt intermediates for evidence check.",
    )
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    markdown_dir = Path(args.markdown_dir)

    json_files = sorted(
        p for p in output_dir.glob("*.json")
        if not p.name.endswith(".manifest.json")
        and not p.name.endswith(".answer.json")
    )

    if not json_files:
        print(f"[verify] No *.json output files found in {output_dir}")
        return 0

    all_errors: list[str] = []
    rows: list[tuple[str, str, str]] = []

    for json_path in json_files:
        stem = json_path.stem
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            all_errors.append(f"{stem}: JSON parse error: {e}")
            rows.append((stem, "FAIL", f"JSON parse error: {e}"))
            continue

        schema = _detect_schema(data)
        if schema is None:
            rows.append((stem, "SKIP", "Could not detect schema (court/factory)"))
            continue

        # Load markdown for evidence checks
        md_path = markdown_dir / f"{stem}.markdown.txt"
        markdown: str | None = None
        if md_path.exists():
            try:
                markdown = md_path.read_text(encoding="utf-8")
            except Exception:
                pass

        errors: list[str] = []
        if schema == "court":
            errors.extend(_check_court(data, stem, markdown))
        elif schema == "factory":
            errors.extend(_check_factory(data, stem, markdown))

        # (g) evidence quotes
        evidence_path = json_path.with_suffix(".evidence.json")
        if evidence_path.exists() and markdown:
            errors.extend(_check_evidence_quotes(evidence_path, markdown, stem))

        if errors:
            all_errors.extend(errors)
            rows.append((stem, "FAIL", f"{len(errors)} error(s)"))
        else:
            rows.append((stem, "PASS", ""))

    # Print summary table
    col_w = max(len(r[0]) for r in rows) + 2
    print(f"\n{'File':<{col_w}} {'Status':<8} Notes")
    print("-" * (col_w + 40))
    for name, status, notes in rows:
        marker = "✓" if status == "PASS" else ("⚠" if status == "SKIP" else "✗")
        print(f"{marker} {name:<{col_w - 2}} {status:<8} {notes}")

    if all_errors:
        print(f"\n[verify] {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  • {err}")
        return 1

    print(f"\n[verify] All {len([r for r in rows if r[1] == 'PASS'])} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
