"""古文書/歴史資料 PDF/画像を Document Intelligence で OCR、
Azure OpenAI Structured Outputs で書誌情報を抽出する。

- Step 1: Document Intelligence prebuilt-layout で Markdown 化
- Step 2: Azure OpenAI (gpt-4o-mini 等) で JSON 抽出
- Step 3: outputs/<name>.json に保存 (書誌情報 + 全文 + 抽出根拠)
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from openai import AzureOpenAI


class DocumentMetadata(BaseModel):
    """1 件の歴史文書の書誌情報スキーマ"""
    title: str = Field(description="文書の題目 (推定)")
    author: Optional[str] = Field(default=None, description="著者/筆者名 (判読可能な場合)")
    date_estimated: Optional[str] = Field(default=None, description="推定年代 (元号+和暦、または西暦)")
    document_type: str = Field(description="文書種別 (書簡, 判物, 御触書, 日記, 記録等)")
    key_topics: list[str] = Field(default_factory=list, description="主要なトピック (人物・地名・出来事) 最大 5 件")
    summary: str = Field(description="現代日本語 200 字以内の要約")
    difficult_passages: list[str] = Field(default_factory=list, description="判読困難と推定される箇所の抜粋 (最大 3 件)")


def analyze_document(pdf_or_image: Path, docint_client: DocumentIntelligenceClient) -> str:
    """Document Intelligence で OCR + Markdown 化"""
    print(f"[docint] analyzing {pdf_or_image.name}")
    with open(pdf_or_image, "rb") as f:
        poller = docint_client.begin_analyze_document(
            "prebuilt-layout",
            AnalyzeDocumentRequest(bytes_source=f.read()),
            output_content_format=DocumentContentFormat.MARKDOWN,
        )
    result = poller.result()
    md = result.content or ""
    print(f"[docint] extracted {len(md)} chars from {len(result.pages or [])} pages")
    return md


def extract_metadata(markdown: str, aoai: AzureOpenAI, deployment: str) -> DocumentMetadata:
    """Azure OpenAI Structured Outputs で書誌情報を抽出"""
    system = (
        "あなたは日本近世〜近代文書の書誌学研究者です。"
        "与えられた OCR 結果 (誤読を含む可能性あり) から、"
        "文書の書誌情報を Pydantic スキーマに従って抽出してください。"
        "推定に自信がない場合は null または空リストを返してください。"
    )
    print(f"[aoai] extracting metadata with {deployment}")
    resp = aoai.beta.chat.completions.parse(
        model=deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"以下は Document Intelligence の OCR 結果です:\n\n{markdown[:8000]}"},
        ],
        response_format=DocumentMetadata,
        temperature=0.1,
    )
    return resp.choices[0].message.parsed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True, help="PDF or image (.jpg/.png/.pdf)")
    args = ap.parse_args()

    load_dotenv()
    for var in ("AZURE_DOCINT_ENDPOINT", "AZURE_DOCINT_KEY",
                "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", "AZURE_OPENAI_DEPLOYMENT"):
        if not os.environ.get(var):
            sys.exit(f"[error] {var} not set (see .env.example)")

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    docint = DocumentIntelligenceClient(
        endpoint=os.environ["AZURE_DOCINT_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_DOCINT_KEY"]),
    )
    aoai = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )

    markdown = analyze_document(args.input, docint)
    metadata = extract_metadata(markdown, aoai, os.environ["AZURE_OPENAI_DEPLOYMENT"])

    stem = args.input.stem
    (outputs / f"{stem}_ocr.md").write_text(markdown, encoding="utf-8")
    (outputs / f"{stem}_metadata.json").write_text(
        metadata.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )
    print("\n=== extracted metadata ===")
    print(metadata.model_dump_json(indent=2))
    print(f"\n[done] outputs/{stem}_metadata.json, {stem}_ocr.md")


if __name__ == "__main__":
    main()
