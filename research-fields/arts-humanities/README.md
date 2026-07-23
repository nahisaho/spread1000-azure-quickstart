# 芸術・人文学 (Arts / Humanities)

**分野規模**: SPReAD-1000 のうち **21 課題**

## 4 つのクイックスタート

| # | シナリオ | ワークロード | Azure リソース |
|---|---|---|---|
| [01](01-speech-transcription/) | 音声書き起こし (日本語 STT) | Azure Speech continuous recognition + TTS デモ | Speech S0 (japaneast) |
| [02](02-document-transcription/) | 古文書翻刻 + 書誌抽出 | Document Intelligence Layout OCR → AOAI Structured Outputs で Pydantic JSON | Doc Intelligence + AOAI |
| [03](03-multilingual-embedding-search/) | 多言語エンベディング検索 | text-embedding-3-large で日/英/仏/独/中 コーパスを FAISS 検索 | AOAI Embeddings |
| [04](04-graphrag/) | GraphRAG によるナレッジグラフ + QA | Microsoft GraphRAG で史料/科学文献からエンティティ・関係を抽出、Leiden コミュニティ検出 → local/global search | AOAI GPT + Embeddings |

いずれも Azure OpenAI 系リソースが必要ですが、コストは 01-03 は 1 デモあたり **$0.01〜$0.10**、04 GraphRAG は初期インデックス構築で **$1〜$5** 程度です。

## 応用ドメイン

- 民俗学、口述史、談話分析 (01)
- 歴史学、書誌学、古文書学、デジタルアーカイブ (02)
- 比較文学、翻訳研究、宗教学、多言語アーカイブ (03)
- 歴史学 (人物ネットワーク)、化学文献 (反応・化合物 KG)、法学 (判例関係抽出)、社会学 (制度・組織関係) (04)
