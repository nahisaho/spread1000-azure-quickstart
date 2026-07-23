# 04 — インデックス構築と検索

## エンドツーエンド実行

```bash
bash src/run.sh
```

`run.sh` の内訳:
1. `graphrag init --root ./ragtest` — 設定雛形 + prompt テンプレートを生成
2. `data/input/*.txt` を `ragtest/input/` にコピー
3. `src/settings.yaml` で `ragtest/settings.yaml` を上書き (Azure OpenAI 設定)
4. `graphrag index --root ./ragtest` — インデックス構築
5. サンプル global/local クエリを実行

## インデックス構築の進行 (期待)

```
✅ create_base_text_units
✅ create_final_documents
✅ extract_graph
✅ finalize_graph
✅ create_communities
✅ create_final_text_units
✅ create_community_reports
✅ generate_text_embeddings
🚀 All workflows completed successfully.
```

所要時間: 3 文書で 3〜10 分程度 (LLM 応答待ち)。

## 出力ファイル

`ragtest/output/` に parquet 形式で保存:
- `entities.parquet` — 抽出したエンティティ (id, title, type, description, ...)
- `relationships.parquet` — エンティティ間関係
- `communities.parquet` — Leiden クラスタ結果
- `community_reports.parquet` — 各コミュニティの LLM 要約
- `text_units.parquet` — chunk 単位のテキスト
- `documents.parquet` — 元文書メタデータ
- `lancedb/` — エンベディング格納の Lance DB

## 抽出結果を確認 (pandas)

```python
import pandas as pd
ents = pd.read_parquet("ragtest/output/entities.parquet")
print(ents[["title", "type"]].head(20))

rels = pd.read_parquet("ragtest/output/relationships.parquet")
print(rels[["source", "target", "description"]].head(10))

reports = pd.read_parquet("ragtest/output/community_reports.parquet")
print(reports[["title", "summary"]].head())
```

## サンプルクエリ

### Global search (集約質問)

```bash
python src/query.py --method global \
  --query "Who were the main intellectuals connecting Rangaku and the Meiji Restoration, and how were they related?"
```

期待出力 (要旨):
> The transition from Rangaku (Dutch Learning) to the Meiji Restoration was
> shaped by intellectuals who bridged Edo-period scholarship and Meiji-era
> reform. Key figures include Sugita Genpaku, whose translation of Kaitai
> Shinsho established Western medicine, and Fukuzawa Yukichi, who studied
> Rangaku before transitioning to English and founded Keio University.
> The Iwakura Mission (Iwakura Tomomi, Ōkubo Toshimichi, Itō Hirobumi) then
> institutionalized Western learning at scale... [Data: Community Reports (1, 3)]

### Local search (特定エンティティ)

```bash
python src/query.py --method local \
  --query "What did Sugita Genpaku translate and who were his collaborators?"
```

期待出力:
> Sugita Genpaku translated the Dutch anatomical text Ontleedkundige Tafelen
> into Japanese, publishing it as Kaitai Shinsho in 1774. His collaborators
> included Maeno Ryotaku and Nakagawa Jun'an. [Data: Entities (5, 12);
> Relationships (7, 9)]

## クエリの選び方

| 質問の種類 | 使う method |
|---|---|
| "X について教えて" | local |
| "X と Y の関係は?" | local |
| "全体の主要テーマは?" | global |
| "登場する組織の一覧は?" | global |
| "X について調べつつ関連を探索したい" | drift |
