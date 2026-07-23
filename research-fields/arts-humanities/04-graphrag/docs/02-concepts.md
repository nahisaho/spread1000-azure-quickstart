# 02 — GraphRAG の考え方

## 素の RAG の限界

**RAG (Retrieval-Augmented Generation)** の一般形:
```
Query → chunk 検索 (embedding cosine) → 上位 k chunks を LLM に投入 → 回答
```

限界:
- **横断的質問に弱い**: "この文書全体で扱われる主要な対立軸は?" のような集約質問は、単一 chunk では答えられない
- **多段関係の欠落**: A → B → C の関係を追う質問で、A と C が同じ chunk にないと失敗
- **エンティティの解決不足**: "Sugita Genpaku" と "杉田玄白" が同一人物とわからない

## GraphRAG が加える 3 つの層

### 1. エンティティ・関係の明示化

LLM に prompt を投げて文書からエンティティ (person, place, event, ...) と関係を JSON で抽出:
```
Sugita Genpaku [PERSON] --- translated ---> Kaitai Shinsho [WORK]
Kaitai Shinsho [WORK] --- based on ---> Ontleedkundige Tafelen [WORK]
```

**Extract graph** ステップで実施。1 文書につき数回の LLM 呼び出しが発生。

### 2. コミュニティ検出 (階層クラスタリング)

エンティティ関係グラフに **Leiden アルゴリズム**を適用:
- 密に繋がっているエンティティ群を同じ**コミュニティ**にまとめる
- 階層的 (community 0 の中に community 0.1, 0.2, ...)

コミュニティごとに LLM が要約を生成:
```
Community 0: 蘭学ネットワーク
  - 主要人物: Sugita Genpaku, Maeno Ryotaku, Nakagawa Jun'an
  - 主要著作: Kaitai Shinsho
  - 舞台: Dejima, Nagasaki
```

### 3. 2 種類の検索

| 種類 | 用途 | 動作 |
|---|---|---|
| **local search** | 特定エンティティ周辺の詳細質問 | 関連エンティティ + text unit + community report を LLM に投入 |
| **global search** | コーパス全体を横断する集約質問 | 全 community report を map-reduce で LLM に投入 |
| **drift search** | 探索的質問 | community から entity への drift (発展) |

## 論文

Edge et al. (2024). *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"*, arXiv:2404.16130

Microsoft の実装: https://github.com/microsoft/graphrag

## GraphRAG が向く/向かないケース

**向く**:
- 歴史文書 (人物・組織のネットワーク解析)
- 化学文献 (化合物・反応の関係抽出)
- 法学 (判例・法令・当事者の関係)
- 医学文献 (薬・症状・遺伝子の関係)
- 複雑な報告書の要約

**向かない**:
- 単純な事実検索 (FAQ)
- 数式・コードの検索
- 画像・音声データ
- 小規模コーパス (< 数千 word) — オーバーヘッドが大きすぎる
