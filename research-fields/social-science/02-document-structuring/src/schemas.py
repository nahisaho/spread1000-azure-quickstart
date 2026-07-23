"""Pydantic schemas for extractable document types.

All fields are required + nullable (str | None) rather than optional
(Optional[str] = None) because Azure OpenAI Structured Outputs strict mode
requires every property in `required` with `additionalProperties: false`.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CourtDecision(BaseModel):
    """判決文の主要フィールド。"""

    case_number: str | None = Field(..., description="事件番号 (例: 令和8年(ワ)第12345号)")
    court: str | None = Field(..., description="裁判所名 (例: 東京地方裁判所民事第32部)")
    date: str | None = Field(..., description="判決日 (ISO 8601, 例: 2026-05-15)")
    judges: list[str] = Field(..., description="裁判官氏名の配列")
    parties: list[str] = Field(..., description="当事者 (原告・被告) の配列")
    holding: str | None = Field(..., description="主文")
    reasoning_summary: str | None = Field(..., description="理由の要旨 (200-500 字)")
    source_page_range: str = Field(..., description="抽出元ページ範囲 (例: 1-2)")


class FactoryRecord(BaseModel):
    """工場名簿の1レコード。"""

    factory_name: str | None
    address: str | None
    industry_code: str | None = Field(..., description="日本標準産業分類コード (4桁)")
    employees: int | None = Field(..., description="従業員数")
    established: str | None = Field(..., description="設立年月 (YYYY または YYYY-MM)")
    source_page_range: str = Field(..., description="このレコードの抽出元ページ範囲 (例: 2 または 2-3)")


class FactoryRegistry(BaseModel):
    """工場名簿全体。"""

    records: list[FactoryRecord]
    source_page_range: str = Field(..., description="抽出元ページ範囲")


SCHEMAS: dict[str, type[BaseModel]] = {
    "court": CourtDecision,
    "factory": FactoryRegistry,
}


SYSTEM_PROMPTS: dict[str, str] = {
    "court": (
        "以下は Document Intelligence が PDF から抽出した判決文の Markdown です。"
        "スキーマに従って抽出してください。\n\n"
        "重要:\n"
        "- 文書に明記された値だけを抽出してください。\n"
        "- 不明な値は null にし、絶対に推測しないでください。\n"
        "- 日付は ISO 8601 (YYYY-MM-DD) で正規化してください。元号表記は保持しつつ変換してください。\n"
        "- judges / parties は箇条書きから抽出。人数不明なら空配列 []。\n"
        "- reasoning_summary は 200-500 字で要約。文書外の解釈を加えないでください。\n"
        "- source_page_range は元文書の Markdown 内の <!-- PageBreak --> を参照して決定。\n"
    ),
    "factory": (
        "以下は Document Intelligence が PDF から抽出した工場名簿の Markdown です。"
        "各行を FactoryRecord として構造化してください。\n\n"
        "重要:\n"
        "- HTML <table> のセル値のみを使い、ヘッダ行はスキップしてください。\n"
        "- 不明な値は null。従業員数の欠損は int:None ではなく null に。\n"
        "- industry_code は日本標準産業分類 (4桁数字文字列)。数字以外の記号を除去。\n"
        "- established は元表記に合わせて YYYY または YYYY-MM。\n"
        "- 各 FactoryRecord.source_page_range と親 FactoryRegistry.source_page_range は"
        " 元文書の Markdown 内の <!-- PageBreak --> を参照して決定。"
        "レコードが単一ページ由来なら `2` のように単一ページ番号、複数ページに跨るなら `2-3` の形式で記入。\n"
    ),
}
