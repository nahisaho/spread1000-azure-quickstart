"""Extract SPReAD-1000 adopted projects using word-level y-coordinates.

This version reconstructs project titles by:
  1. Identifying anchor words (project numbers) with their y-positions.
  2. Defining y-bounds for each anchor as [midpoint(prev), midpoint(next)].
  3. Gathering all words in the TITLE column whose y falls in the anchor's bounds.

Source: docs/source/spread1000-adopted.pdf (pages 0-41)
Output: docs/source/spread1000-adopted.json
"""
import json
import re
from pathlib import Path

import pdfplumber

PDF = Path("docs/source/spread1000-adopted.pdf")
OUT = Path("docs/source/spread1000-adopted.json")
LAST_LIST_PAGE = 41

CANONICAL_FIELDS = [
    "生命科学・薬学",
    "臨床科学",
    "社会科学",
    "芸術・人文科学",
    "化学",
    "電気工学・電子工学・情報科学・コンピューターサイエンス",
    "材料・プロセス・応用医工学",
    "機械・社会基盤・エネルギー工学",
    "数学・物理学・地球科学",
    "農学・環境学・生態学",
]


def canonicalize_field(raw: str) -> str:
    if not raw:
        return ""
    for c in CANONICAL_FIELDS:
        if raw == c or raw.replace(" ", "") == c.replace("・", ""):
            return c
    hits = [c for c in CANONICAL_FIELDS if raw in c or c in raw]
    if hits:
        return max(hits, key=len)
    stripped = raw.replace("・", "").replace(" ", "")
    for c in CANONICAL_FIELDS:
        if stripped and stripped in c.replace("・", ""):
            return c
    return raw


def group_words_by_line(words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
    """Group words into lines by y-coordinate proximity."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines: list[list[dict]] = [[words[0]]]
    for w in words[1:]:
        if abs(w["top"] - lines[-1][0]["top"]) <= y_tol:
            lines[-1].append(w)
        else:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def process_page(page, page_num: int) -> list[dict]:
    words = page.extract_words(x_tolerance=1.5, y_tolerance=1.5, keep_blank_chars=False)
    if not words:
        return []
    lines = group_words_by_line(words)

    # Find header line to determine column x-boundaries
    header_line = None
    for ln in lines:
        text_joined = "".join(w["text"] for w in ln)
        if "No." in text_joined and "研究課題名" in text_joined and "所属機関" in text_joined:
            header_line = ln
            break
    if not header_line:
        return []

    # Column x-ranges from header words (x0, x1)
    col_ranges: dict[str, tuple[float, float]] = {}
    for w in header_line:
        for key in ("No.", "研究領域", "研究課題名", "研究代表者", "所属機関"):
            if w["text"] == key:
                col_ranges[key] = (w["x0"], w["x1"])

    if not all(k in col_ranges for k in ("No.", "研究領域", "研究課題名", "研究代表者", "所属機関")):
        return []

    # Column boundaries: each column extends from its own left edge to the left
    # edge of the NEXT column. This gives the title column room for English
    # words that extend beyond the "研究課題名" header width.
    order = ["No.", "研究領域", "研究課題名", "研究代表者", "所属機関"]
    bounds: list[tuple[float, float]] = []
    for i, k in enumerate(order):
        lo = 0 if i == 0 else col_ranges[k][0] - 2
        # Use the next column's left edge as the upper bound
        hi = 10000 if i == len(order) - 1 else col_ranges[order[i + 1]][0] - 2
        bounds.append((lo, hi))
    col_bounds = dict(zip(order, bounds))

    header_bottom = max(w["bottom"] for w in header_line)

    # Find anchor words (project numbers) in the No. column, below header
    def in_col(w: dict, col: str) -> bool:
        cx = (w["x0"] + w["x1"]) / 2
        lo, hi = col_bounds[col]
        return lo <= cx < hi

    anchors: list[dict] = []
    for w in words:
        if w["top"] < header_bottom + 1:
            continue
        if not in_col(w, "No."):
            continue
        if re.fullmatch(r"\d{1,3}", w["text"]):
            anchors.append(w)
    anchors.sort(key=lambda w: w["top"])

    if not anchors:
        return []

    # Pre-compute all title-column lines and greedy-assign to anchors
    # (title lines cluster around each anchor with small line gaps; the
    # boundary between projects is signaled by a larger vertical gap).
    title_words_all = [
        w for w in words
        if in_col(w, "研究課題名") and w["top"] > header_bottom
    ]
    title_lines = group_words_by_line(title_words_all)
    # Cluster title lines into "blocks" by vertical proximity (small gap =
    # same title continuation, larger gap = new project's title).
    # Threshold tuned to line spacing ~14 px + small tolerance; larger gaps
    # (≥19 px) reliably separate adjacent projects.
    BLOCK_GAP = 18.0
    blocks: list[list[list[dict]]] = []
    for ln in title_lines:
        if blocks and (ln[0]["top"] - blocks[-1][-1][0]["top"]) <= BLOCK_GAP:
            blocks[-1].append(ln)
        else:
            blocks.append([ln])

    # If a block spans multiple anchors, split it at each anchor's top y-position
    split_blocks: list[list[list[dict]]] = []
    for blk in blocks:
        blk_top = blk[0][0]["top"]
        blk_bottom = blk[-1][0]["top"]
        # anchors whose top falls within (blk_top, blk_bottom]
        interior_splits = sorted(
            a["top"] for a in anchors if blk_top < a["top"] <= blk_bottom
        )
        if not interior_splits:
            split_blocks.append(blk)
            continue
        cur: list[list[dict]] = []
        idx = 0
        for ln in blk:
            while idx < len(interior_splits) and ln[0]["top"] >= interior_splits[idx]:
                if cur:
                    split_blocks.append(cur)
                    cur = []
                idx += 1
            cur.append(ln)
        if cur:
            split_blocks.append(cur)

    anchor_title_lines: dict[int, list[list[dict]]] = {i: [] for i in range(len(anchors))}
    for blk in split_blocks:
        blk_top = blk[0][0]["top"]
        blk_bottom = blk[-1][0]["top"]
        contained = [
            i for i, a in enumerate(anchors)
            if blk_top - 6 <= a["top"] <= blk_bottom + 6
        ]
        if contained:
            owner = contained[0]
        else:
            blk_mid = (blk_top + blk_bottom) / 2
            owner = min(range(len(anchors)), key=lambda i: abs(anchors[i]["top"] - blk_mid))
        anchor_title_lines[owner].extend(blk)

    # For each anchor, define y-range
    projects: list[dict] = []
    for i, a in enumerate(anchors):
        a_y = (a["top"] + a["bottom"]) / 2
        prev_y = (anchors[i - 1]["top"] + anchors[i - 1]["bottom"]) / 2 if i > 0 else None
        next_top = anchors[i + 1]["top"] if i < len(anchors) - 1 else None
        # For non-title columns use symmetric midpoints
        y_lo = header_bottom if prev_y is None else (a_y + prev_y) / 2
        y_hi = 10000 if next_top is None else (a_y + next_top) / 2

        def format_lines(selected_lines: list[list[dict]]) -> str:
            line_texts = []
            for ln in selected_lines:
                text = ""
                for wi, w in enumerate(ln):
                    if wi > 0:
                        prev = ln[wi - 1]
                        gap = w["x0"] - prev["x1"]
                        prev_ascii = prev["text"][-1].isascii() and prev["text"][-1].isalnum()
                        cur_ascii = w["text"][0].isascii() and w["text"][0].isalnum()
                        text += (" " if (prev_ascii and cur_ascii) or gap > 3 else "") + w["text"]
                    else:
                        text += w["text"]
                line_texts.append(text)
            out = ""
            for lt in line_texts:
                if not lt.strip():
                    continue
                if not out:
                    out = lt
                    continue
                prev_ascii = out[-1].isascii() and (out[-1].isalnum() or out[-1] in "-,;:")
                cur_ascii = lt[0].isascii() and (lt[0].isalnum() or lt[0] in "-'\"")
                sep = " " if prev_ascii and cur_ascii else ""
                out += sep + lt
            return out.strip()

        def collect_nontitle(col: str) -> str:
            selected = [
                w for w in words
                if in_col(w, col) and y_lo <= (w["top"] + w["bottom"]) / 2 < y_hi
            ]
            return format_lines(group_words_by_line(selected))

        title = format_lines(sorted(anchor_title_lines[i], key=lambda ln: ln[0]["top"]))
        # Clean hyphenation joins ("Pre- Screening" → "Pre-Screening")
        title = re.sub(r"(\w)-\s+(\w)", r"\1-\2", title)
        # Strip trailing page number (may be attached to the last title word
        # without a word boundary, e.g. "解析3"). Only strip 1–3 trailing digits.
        title = re.sub(r"\s*\d{1,3}\s*$", "", title).strip()
        field_raw = collect_nontitle("研究領域").replace(" ", "")
        pi = collect_nontitle("研究代表者")
        affil = collect_nontitle("所属機関")

        projects.append(
            {
                "no": int(a["text"]),
                "field": canonicalize_field(field_raw),
                "title": title,
                "pi": pi,
                "affiliation": affil,
                "page": page_num,
            }
        )
    return projects


def main() -> None:
    all_projects: dict[int, dict] = {}
    with pdfplumber.open(PDF) as pdf:
        for pn in range(min(LAST_LIST_PAGE + 1, len(pdf.pages))):
            for p in process_page(pdf.pages[pn], pn + 1):
                all_projects[p["no"]] = p

    result = [all_projects[k] for k in sorted(all_projects)]
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"Extracted {len(result)} projects to {OUT}")
    from collections import Counter

    fields = Counter(p["field"] for p in result)
    print("\nField counts:")
    for f, c in fields.most_common():
        print(f"  {c:4d}  {f}")


if __name__ == "__main__":
    main()
