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
  --texts data/embeddings/topic.cleaned.csv \
  --id-col id --text-col cleaned_text \
  --k-range 2 6
```

出力:

- 標準出力に k ごとの silhouette、選択された k
- `data/output/topic-clusters.json` — クラスタ割当、各クラスタの重心近傍 3 件、`selected_k` は「silhouette 最大の候補」であって「真に最適な k」ではない旨のメモを含む

> [!NOTE]
> silhouette は「相対的な良さ」の指標にすぎず、k=4 で最大になっても真のクラスタ数が 4 とは限りません。ドメイン知識や複数シードでの安定性 (`--random-state` を変えて再実行) と合わせて判断してください。

### 3. 日本語ラベル生成

```bash
python src/label_clusters.py --clusters data/output/topic-clusters.json
```

出力: `data/output/topic-labels.json`

```json
{
  "source_clusters": "data/output/topic-clusters.json",
  "aoai_deployment": "label-gpt54mini",
  "label_model": "gpt-5.4-mini",
  "label_model_version": "2026-03-17",
  "reasoning_effort": "low",
  "note_on_model_self_assessment": "The 'model_self_assessment' field is a raw LLM self-report and is NOT a calibrated probability. Do not report it as confidence or reliability.",
  "labels": {
    "0": {"label": "宿泊", "summary": "旅館やホテルなど宿泊施設の体験を語る投稿", "model_self_assessment": 0.85},
    "1": {"label": "食事", "summary": "地元料理や飲食店での食体験に関する内容", "model_self_assessment": 0.80},
    "...": "..."
  }
}
```

> [!IMPORTANT]
> `model_self_assessment` は LLM の**自己申告**であって、統計的な確度・信頼度ではありません。校正されていないため、学術発表で「confidence」と呼ばないでください。実験的な信頼指標が必要な場合は、複数シードでのクラスタ安定性や人手アノテーションとの一致率を用いてください。

## 期待される結果

`synthetic_topic.csv` (4 クラス × 8 件) では、k=4 前後で silhouette が最大化されるはずです (0.10〜0.25 程度)。silhouette の絶対値は日本語短文では低めに出るのが普通です。

> [!NOTE]
> **silhouette が低い = 悪いとは限りません**。日本語の高次元埋め込みでは 0.1〜0.3 が典型的です。クラスタサイズの偏りや `label_clusters.py` が返した `model_self_assessment` も併せて総合判断してください (`model_self_assessment` は LLM の自己申告なので過信は禁物)。

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
