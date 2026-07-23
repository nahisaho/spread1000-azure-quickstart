# 05. クラスタリングとラベル生成

## 目的

ラベルが付いていないテキスト集合に対して:

1. KMeans でクラスタを作る
2. silhouette score で最適な k を選ぶ
3. 各クラスタの代表テキストを `gpt-5.4-mini` に渡し、**日本語ラベル**を Structured Outputs で得る

## 手順

### 1. 埋め込みを生成 (04 で作成済みなら再利用可)

```bash
python src/embed.py --input data/synthetic_topic.csv \
  --text-col text --id-col id \
  --output data/embeddings/topic.npy
```

### 2. KMeans + silhouette

```bash
python src/cluster.py \
  --embeddings data/embeddings/topic.npy \
  --texts data/synthetic_topic.csv --text-col text \
  --k-range 2 6
```

出力:

- 標準出力に k ごとの silhouette、選択された k
- `data/output/topic-clusters.json` — クラスタ割当、各クラスタの重心近傍 3 件

### 3. 日本語ラベル生成

```bash
python src/label_clusters.py --clusters data/output/topic-clusters.json
```

出力: `data/output/topic-labels.json`

```json
{
  "source_clusters": "data/output/topic-clusters.json",
  "aoai_deployment": "label-gpt54mini",
  "reasoning_effort": "low",
  "labels": {
    "0": {"label": "宿泊", "summary": "旅館やホテルなど宿泊施設の体験を語る投稿", "confidence": 0.85},
    "1": {"label": "食事", "summary": "地元料理や飲食店での食体験に関する内容", "confidence": 0.80},
    "...": "..."
  }
}
```

## 期待される結果

`synthetic_topic.csv` (4 クラス × 8 件) では、k=4 前後で silhouette が最大化されるはずです (0.10〜0.25 程度)。silhouette の絶対値は日本語短文では低めに出るのが普通です。

> [!NOTE]
> **silhouette が低い = 悪いとは限りません**。日本語の高次元埋め込みでは 0.1〜0.3 が典型的です。クラスタサイズの偏りや `label_clusters.py` が返した `confidence` も併せて総合判断してください。

## HDBSCAN / UMAP を試したい場合

`src/cluster.py` は KMeans のみを実装しています。HDBSCAN や UMAP による可視化は次のように追記できます:

```python
from sklearn.cluster import HDBSCAN
import umap

hdb = HDBSCAN(min_cluster_size=3, metric="euclidean")
labels = hdb.fit_predict(X)                   # -1 はノイズ

reducer = umap.UMAP(metric="cosine", n_neighbors=5, random_state=42)
X2 = reducer.fit_transform(X)
```

30〜60 件では UMAP `n_neighbors` を 5〜10 に下げないと警告が出ます。

## 想定コスト

- Embedding: 04 と共有なら追加 0
- ラベル生成: クラスタ数 × (入力 ~500 tokens + 出力 ~100 tokens) × ($0.75/$4.50 per 1M)
- 例: 4 クラスタ → **約 $0.003**

`label_clusters.py --reasoning-effort low --max-completion-tokens 200` が既定で、これでも品質は十分です。
