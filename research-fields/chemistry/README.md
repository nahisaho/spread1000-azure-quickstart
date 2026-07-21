# 化学（Chemistry）

SPReAD-1000 第1回公募で **22 課題**が採択された分野です。分子生成、反応予測、DFT、GNN などが中心です。

## クイックスタート一覧

| # | シナリオ | 用途 | 計算資源 | 想定コスト (1 回) |
|---:|---|---|---|---:|
| [01](01-molecular-generation-reinvent4/) | **分子生成 (REINVENT4)** | scaffold からの分子設計を Azure ML で回す最短ルート (LibInvent scaffold decoration) | Standard_D4as_v5 (CPU) | $0.10〜0.50 (¥15〜75) |
| [02](02-reaction-prediction-reactiont5/) | **反応予測 (ReactionT5v2)** | 反応物 SMILES → 生成物 SMILES を T5 Seq2Seq で予測 (HF `sagawa/ReactionT5v2-forward`, MIT, 推論のみ) | Standard_NC4as_T4_v3 (T4 GPU) | $0.18〜0.50 (¥30〜75) |
| 03 | **分子物性 GNN (PyG + MoleculeNet)** — 予定 | GraphConv / GIN でトキシシティ/溶解度予測 | T4 GPU | 予定 |

## 学習パス（推奨順）

1. **分子生成 (REINVENT4)** — CPU で完結する最も安価な入門。LibInvent による scaffold decoration を体験
2. **反応予測 (ReactionT5v2)** — T5 Seq2Seq で反応物 → 生成物を予測 (推論のみ、事前学習済み HF モデル)
3. **分子物性 GNN** — Graph Neural Network でトキシシティや溶解度を予測

## 想定される SPReAD-1000 課題例（実データより）

- 「分子設計」「触媒設計」「化合物探索」→ シナリオ 01
- 「反応予測」「反応経路探索」→ シナリオ 02
- 「物性予測」「材料スクリーニング」→ シナリオ 03

一次資料: [`../../docs/source/spread1000-adopted.json`](../../docs/source/spread1000-adopted.json)（化学 22 件）
