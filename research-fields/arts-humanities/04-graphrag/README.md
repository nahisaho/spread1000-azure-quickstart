# 04 — Microsoft GraphRAG ナレッジグラフ + QA

**分野**: 歴史学、書誌学、法学、社会学、化学文献解析、生命科学文献ネットワーク  
**手法**: Microsoft GraphRAG 2.4 で文書コーパスからエンティティ・関係・コミュニティを抽出、Leiden クラスタリングでコミュニティ検出、階層要約 → local/global search で QA  
**時間**: ~10-20 分 (リソース準備 + インデックス構築)  
**コスト**: 初期インデックス構築で **$1〜$5** (LLM 呼び出しが数百回発生)

## 何が学べるか

- **GraphRAG** の考え方: 素の RAG (chunk → embedding) では捉えにくい**エンティティ間の関係**を明示的にグラフ化
- 3 種の検索方法
  - **local search** — 特定エンティティ周辺の詳細質問 ("福澤諭吉の教育活動は?")
  - **global search** — コーパス全体を横断する集約的質問 ("Meiji 期の主要人物とその関係は?")
  - **drift search** — local と global の中間、探索的質問
- コミュニティ検出 (Leiden アルゴリズム) と階層要約

## リソース準備

1. **Azure OpenAI** リソース (japaneast, Standard S0)
2. 以下の 2 デプロイを作成 (Azure OpenAI Studio):
   - Chat: `gpt-4o-mini` (安価、日本語 OK) or `gpt-4o` (高精度、高コスト)
   - Embedding: `text-embedding-3-small`
3. `.env` を作成:

```bash
cp .env.example .env
# .env を編集 (GRAPHRAG_API_BASE, GRAPHRAG_API_KEY, デプロイ名)
```

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate   # WSL/macOS/Linux。Windows は WSL2 か Git Bash 推奨
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# エンドツーエンド (init → dry-run → index → sample queries)
# 実行前に推定コスト表示 + 予算上限確認 (デフォルト $10、GRAPHRAG_BUDGET_USD で変更可)
bash src/run.sh

# 追加クエリ (インデックス構築後、プロジェクトルート .env を自動読み込み)
python src/query.py --method global --query "明治維新に関わった中心人物は誰で、どう繋がっていたか?"
python src/query.py --method local  --query "Sugita Genpaku が翻訳した書物は?"
```

## サンプルコーパス

`data/input/` に 3 つの英語テキスト (Wikipedia 由来、CC-BY-SA):
- `01_rangaku.txt` — 蘭学と杉田玄白、解体新書
- `02_meiji_restoration.txt` — 明治維新、薩長同盟、岩倉使節団
- `03_fukuzawa.txt` — 福澤諭吉、慶應義塾、学問のすすめ

これら 3 文書には**意図的にエンティティが交差**しています (蘭学 → 明治維新、福澤 → 蘭学修業)。GraphRAG が交差関係を復元できるかを確認できます。

## 期待される抽出結果

**エンティティ (例)**:
- 人物: Sugita Genpaku, Fukuzawa Yukichi, Iwakura Tomomi, Saigō Takamori, ...
- 組織: Tokugawa shogunate, Satsuma domain, Keio University, ...
- 場所: Dejima, Nagasaki, Yokohama, ...
- 事件: Meiji Restoration, Boshin War, Iwakura Mission, ...
- 著作: Kaitai Shinsho, Gakumon no Susume, ...

**関係 (例)**:
- Sugita Genpaku — translated — Kaitai Shinsho
- Fukuzawa Yukichi — founded — Keio University
- Satsuma domain — allied with — Chōshū domain

**コミュニティ (例)**:
- クラスタ 0: 蘭学関連 (杉田玄白、Dejima、Kaitai Shinsho)
- クラスタ 1: 明治維新関連 (岩倉、大久保、伊藤博文)

## コスト内訳 (gpt-4o-mini, 3 文書 ~5000 words)

| 段階 | 呼び出し数 | 目安 |
|---|---|---|
| Extract entities/relations | ~10-30 | $0.05 |
| Summarize descriptions | ~50-100 | $0.10 |
| Community reports | ~5-15 | $0.10 |
| Embedding (エンティティ + text units) | ~100-300 | $0.01 |
| 単発 local/global query | 1-10 | $0.01-0.10 |
| **合計 (index 構築 + 数クエリ)** |  | **$0.30〜$0.50** |

大規模コーパス (数百万 word) では **$100+** になり得る。詳細は [docs/06-cleanup.md](docs/06-cleanup.md) 参照。

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 GraphRAG の考え方](docs/02-concepts.md)
- [03 Azure リソース準備](docs/03-provision.md)
- [04 インデックス構築と検索](docs/04-run.md)
- [05 自前コーパスへの適用](docs/05-your-data.md)
- [06 片付けとコスト管理](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
