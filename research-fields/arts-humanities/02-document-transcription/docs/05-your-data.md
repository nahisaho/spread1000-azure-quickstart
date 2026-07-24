# 05 — 自前古文書への適用

## スキーマ変更

`src/extract.py` の `DocumentMetadata` クラスを研究対象に合わせて編集:

```python
class BukeMonjo(BaseModel):
    """武家文書に特化した抽出スキーマ"""
    差出人: str
    受取人: str
    発給年月日: Optional[str]
    印判の有無: bool
    宛所: Optional[str]
    差出御名: Optional[str]
    key_content: list[str]
```

Structured Outputs は Pydantic モデルを直接受け取るので、フィールド追加/変更だけで OK。

## バッチ処理 (数百点の資料)

```bash
SCENARIO_DIR=$(git rev-parse --show-toplevel)/research-fields/arts-humanities/02-document-transcription
cd "$SCENARIO_DIR"

for pdf in archive/*.pdf; do
    python src/extract.py --input "$pdf" --yes
done
```

コストは 1 点あたり **参考値 (2026-07 時点、eastus S0) ~$0.06** なので、1000 点で ~$60 程度。
最新料金は [Azure AI Document Intelligence 料金](https://azure.microsoft.com/pricing/details/ai-document-intelligence/) と
[Azure OpenAI 料金](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) で確認し、
[Azure 料金計算ツール](https://azure.microsoft.com/pricing/calculator/) で見積もってください。

## 崩し字資料の場合

1. **みを (Miwo)** で崩し字を翻刻: https://miwo.ninjal.ac.jp/
2. 翻刻結果 (JSON) を `extract.py` の `analyze_document` の代わりに読み込み
3. Azure OpenAI で書誌情報を抽出

## 資料の Provenance 管理

抽出結果には必ず以下を併記して保存:
- 原資料の所蔵先、請求番号
- スキャン日、スキャン条件
- Document Intelligence のバージョン (API version)
- LLM モデルとバージョン (deployment name, model version)

**再現性確保** + **後日 LLM 更新時の再抽出比較**のため。

## 応用例

| ドメイン | スキーマ例 |
|---|---|
| 書簡研究 | 差出人, 宛先, 日付, 内容分類, 感情タグ |
| 判物・下知状 | 発給主体, 対象者, 給付内容, 給付理由 |
| 検地帳 | 年次, 村名, 石高, 名請人一覧 |
| 日記 | 記主, 日付, 天候, 出来事タグ |
| 系図 | 人物リスト, 関係 (親子/兄弟), 生没年 |

## 参考文献

- 石橋知也ほか (2024). *"AI OCR による古典籍翻刻の実践"*, 情報処理学会 CH 研究会
- 国立情報学研究所「古典籍 OCR 総合支援ツールキット」
