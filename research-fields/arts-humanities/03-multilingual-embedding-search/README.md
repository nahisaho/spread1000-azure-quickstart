# 03 — 多言語エンベディング検索 (Azure OpenAI + FAISS)

**分野**: 比較文学、翻訳研究、書誌学、多言語アーカイブ、宗教学  
**手法**: Azure OpenAI `text-embedding-3-large` で 5 言語 (日/英/仏/独/中) を単一ベクトル空間に、FAISS で類似検索  
**時間**: ~5 分 (リソース作成含む)

## 何が学べるか

- 多言語埋め込みモデルによる **言語横断検索** (日本語クエリで英語文献ヒット)
- FAISS Flat Index の基本 (Inner Product + L2 normalize = cosine sim)
- Azure OpenAI Embeddings API の使い方
- コーパスメタデータ (id, lang, text) の管理

## リソース準備

1. **Azure OpenAI** リソース (japaneast, Standard S0)
2. `text-embedding-3-large` をデプロイ (Azure OpenAI Studio)
3. `.env` を作成:

```bash
cp .env.example .env
# .env を編集
```

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 1) 15 文の多言語コーパスを埋め込み + FAISS インデックス作成
python src/build_index.py

# 2) 任意言語でクエリ
python src/search.py --query "紫式部の物語"
python src/search.py --query "Japanese poetry"
python src/search.py --query "Impressionismus"
```

## 期待出力 (「紫式部の物語」で検索)

```
順位  類似度  ID    言語  テキスト
------------------------------------------
  1  0.7412  ja01  ja  源氏物語は平安時代中期に紫式部によって書かれた長編物語で、...
  2  0.6588  en01  en  The Tale of Genji, written by Murasaki Shikibu in the Heian period, ...
  3  0.6203  fr01  fr  Le Genji Monogatari, écrit par Murasaki Shikibu à l'époque de Heian, ...
  4  0.6091  zh01  zh  《源氏物語》是日本平安時代紫式部所著的長篇小說，...
  5  0.5322  ja02  ja  枕草子は清少納言による随筆で、...
```

日本語クエリで英語・仏語・中国語の関連文がヒットする様子が確認できます。

## コスト

| 項目 | 単価 | 本デモ (15 doc + 数クエリ) |
|---|---|---|
| text-embedding-3-large | $0.13 / 1M tokens | **< $0.001** |

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 Azure リソース準備](docs/02-provision.md)
- [03 実行](docs/03-run.md)
- [04 結果の解釈](docs/04-understand-results.md)
- [05 自前コーパスへの適用](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
