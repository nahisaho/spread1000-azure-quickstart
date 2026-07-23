"""Generate CC0 fictional Japanese PDFs for the document-structuring demo.

All content is entirely fabricated — no real persons, cases, companies, or addresses.

Usage:
  python scripts/generate_demo_pdfs.py --output-dir data/
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


# ReportLab's HeiseiKakuGo-W5 is a bundled CID font that supports Japanese
# without requiring OS fonts. It renders as an outline-based CJK font.
JP_FONT = "HeiseiKakuGo-W5"


def _register_font() -> None:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(JP_FONT))
    except Exception as e:
        raise SystemExit(
            f"ERROR: could not register CJK font '{JP_FONT}': {e}\n"
            "Ensure 'reportlab>=4.0.0' is installed."
        )


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, width: float,
                  font_size: float = 10, leading: float = 14) -> float:
    """Wrap Japanese text using actual measured glyph widths."""
    from reportlab.pdfbase import pdfmetrics as _pm

    c.setFont(JP_FONT, font_size)

    def _flush(line: str, y_: float) -> float:
        if line:
            c.drawString(x, y_, line)
        return y_ - leading

    for paragraph in text.split("\n"):
        line = ""
        for ch in paragraph:
            trial = line + ch
            if _pm.stringWidth(trial, JP_FONT, font_size) > width:
                y = _flush(line, y)
                line = ch
            else:
                line = trial
        y = _flush(line, y)
    return y


COURT_TEXT_P1 = (
    "令和8年(ワ)第12345号 損害賠償請求事件\n"
    "令和8年5月15日 東京地方裁判所民事第32部 判決\n"
    "\n"
    "当事者の表示\n"
    "原告 株式会社サンプル商事 (架空)\n"
    "被告 架空製造株式会社 (架空)\n"
    "\n"
    "主文\n"
    "被告は原告に対し、金3000万円及びこれに対する令和8年1月1日から支払済みまで年6分の割合による金員を支払え。\n"
    "訴訟費用は被告の負担とする。\n"
    "\n"
    "事案の概要\n"
    "本件は、原告が被告に対し、令和7年10月に締結した業務委託契約 (以下「本件契約」) の債務不履行に基づき、損害賠償を求めた事案である。"
    "原告は、被告が納期を大幅に遅延させ、契約解除の原因となる重大な違反があったと主張している。"
)

COURT_TEXT_P2 = (
    "理由\n"
    "1. 本件契約の成立\n"
    "当事者間で提出された証拠 (甲第1号証から甲第7号証まで) により、令和7年10月1日に本件契約が有効に成立したことが認められる。\n"
    "\n"
    "2. 債務不履行の存否\n"
    "被告は、本件契約に基づき令和7年12月31日までに納品する義務を負っていたにもかかわらず、令和8年3月末に至るまで一部しか納入していない。"
    "これは本件契約 12 条 3 項の重大な違反に該当する。\n"
    "\n"
    "3. 損害額\n"
    "原告が主張する逸失利益 3000 万円は、原告提出の売上見込資料 (甲第10号証) 等により相当と認められる。\n"
    "\n"
    "よって、主文のとおり判決する。\n"
    "\n"
    "裁判官 山田太郎\n"
    "裁判官 佐藤花子\n"
    "裁判官 鈴木一郎"
)


def make_court_pdf(path: Path) -> dict:
    _register_font()
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4

    # Page 1
    y = h - 25 * mm
    y = _draw_wrapped(c, COURT_TEXT_P1, 20 * mm, y, w - 40 * mm, font_size=11, leading=16)
    c.showPage()

    # Page 2
    y = h - 25 * mm
    y = _draw_wrapped(c, COURT_TEXT_P2, 20 * mm, y, w - 40 * mm, font_size=11, leading=16)
    c.showPage()
    c.save()

    return {
        "case_number": "令和8年(ワ)第12345号",
        "court": "東京地方裁判所民事第32部",
        "date": "2026-05-15",
        "judges": ["山田太郎", "佐藤花子", "鈴木一郎"],
        "parties": ["原告 株式会社サンプル商事", "被告 架空製造株式会社"],
        "holding": (
            "被告は原告に対し、金3000万円及びこれに対する令和8年1月1日から支払済みまで"
            "年6分の割合による金員を支払え。訴訟費用は被告の負担とする。"
        ),
        "reasoning_summary": (
            "令和7年10月1日に本件契約が成立したことは甲第1号証から甲第7号証により認められる。"
            "被告は本件契約に基づき令和7年12月31日までに納品する義務を負っていたが、令和8年3月末に至るまで"
            "一部しか納入せず、これは本件契約12条3項の重大な違反に該当する。原告主張の逸失利益3000万円は"
            "甲第10号証等により相当と認められる。よって主文のとおり判決する。"
        ),
        "source_page_range": "1-2",
    }


FACTORY_HEADER = ["工場名", "所在地", "産業分類コード", "従業員数", "設立"]
FACTORY_ROWS = [
    ["架空製造株式会社 第一工場", "架空県サンプル市1-2-3", "2911", "125", "2018-04"],
    ["ダミー機械工業 中央工場",    "架空県サンプル市4-5-6", "2451", "48",  "2021-09"],
    ["テスト精密工業 東工場",      "架空県モデル町7-8",     "3011", "312", "1995"],
    ["架空電子部品 サンプル工場",  "架空県サンプル市9-10",  "2821", "72",  "2010-03"],
    ["ダミー化学 南工場",          "架空県モデル町11-12",   "1811", "205", "2005-11"],
]


def make_factory_pdf(path: Path) -> dict:
    _register_font()
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4

    def draw_table(start_y: float, rows: list[list[str]]) -> float:
        col_widths = [55 * mm, 55 * mm, 25 * mm, 20 * mm, 25 * mm]
        x0 = 15 * mm
        row_h = 10 * mm

        c.setFont(JP_FONT, 10)
        y = start_y
        # Header
        c.setFillGray(0.9)
        c.rect(x0, y - row_h, sum(col_widths), row_h, stroke=1, fill=1)
        c.setFillGray(0)
        x = x0
        for i, cell in enumerate(FACTORY_HEADER):
            c.drawString(x + 2 * mm, y - row_h + 3 * mm, cell)
            x += col_widths[i]
        y -= row_h
        # Body
        for row in rows:
            c.rect(x0, y - row_h, sum(col_widths), row_h, stroke=1, fill=0)
            x = x0
            for i, cell in enumerate(row):
                c.drawString(x + 2 * mm, y - row_h + 3 * mm, cell)
                x += col_widths[i]
            y -= row_h
        return y

    # Page 1: header + first 3 rows
    c.setFont(JP_FONT, 14)
    c.drawString(15 * mm, h - 20 * mm, "架空県 工場登録名簿 (令和8年度)")
    c.setFont(JP_FONT, 10)
    c.drawString(15 * mm, h - 28 * mm, "※ 本資料は完全に架空の情報です。実在の企業とは一切関係ありません。")
    draw_table(h - 40 * mm, FACTORY_ROWS[:3])
    c.showPage()

    # Page 2: remaining rows
    c.setFont(JP_FONT, 14)
    c.drawString(15 * mm, h - 20 * mm, "架空県 工場登録名簿 (令和8年度) - 続き")
    draw_table(h - 30 * mm, FACTORY_ROWS[3:])
    c.showPage()
    c.save()

    return {
        "records": [
            {
                "factory_name": r[0],
                "address": r[1],
                "industry_code": r[2],
                "employees": int(r[3]),
                "established": r[4],
                "source_page_range": "1" if i < 3 else "2",
            }
            for i, r in enumerate(FACTORY_ROWS)
        ],
        "source_page_range": "1-2",
    }


def make_scanned_pdf(source_pdf: Path, out_pdf: Path, dpi: int = 200) -> None:
    """Rasterize the source PDF to page images and rebuild as image-only PDF."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print(
            "[warn] pdf2image not installed; skipping demo-factory-scanned.pdf.\n"
            "       Install with: pip install pdf2image && sudo apt install poppler-utils",
            file=sys.stderr,
        )
        return

    try:
        pages = convert_from_path(str(source_pdf), dpi=dpi)
    except Exception as e:
        print(f"[warn] pdf2image failed: {e}; skipping scanned PDF.", file=sys.stderr)
        return

    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    w, h = A4
    from reportlab.lib.utils import ImageReader
    for img in pages:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=w, height=h,
                    preserveAspectRatio=True, anchor="c")
        c.showPage()
    c.save()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="data")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    court_pdf = out / "demo-court.pdf"
    court_answer = out / "demo-court.answer.json"
    factory_pdf = out / "demo-factory.pdf"
    factory_answer = out / "demo-factory.answer.json"
    scanned_pdf = out / "demo-factory-scanned.pdf"

    print(f"[gen] {court_pdf}")
    court = make_court_pdf(court_pdf)
    court_answer.write_text(json.dumps(court, ensure_ascii=False, indent=2))
    print(f"[gen] {court_answer}")

    print(f"[gen] {factory_pdf}")
    factory = make_factory_pdf(factory_pdf)
    factory_answer.write_text(json.dumps(factory, ensure_ascii=False, indent=2))
    print(f"[gen] {factory_answer}")

    print(f"[gen] {scanned_pdf} (rasterizing factory PDF)")
    make_scanned_pdf(factory_pdf, scanned_pdf)

    print("[gen] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
