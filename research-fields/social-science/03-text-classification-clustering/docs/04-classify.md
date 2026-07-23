# 04. 分類 (Embeddings → LogisticRegression)

## 手順

### 1. 埋め込みを生成

```bash
python src/embed.py \
  --input data/synthetic_sentiment.csv \
  --text-col text --id-col id \
  --output data/embeddings/sentiment.npy
```

出力:

- `data/embeddings/sentiment.npy` — (N, 1536) float32
- `data/embeddings/sentiment.ids.csv` — 元の id との対応
- `data/embeddings/sentiment.manifest.json` — モデル・次元・トークン数・コスト概算・実行時刻

### 2. LogisticRegression をクロスバリデーション

```bash
python src/classify.py \
  --embeddings data/embeddings/sentiment.npy \
  --labels data/synthetic_sentiment.csv \
  --label-col label
```

出力:

- 標準出力に fold ごとの macro-F1、`classification_report`、混同行列
- `data/output/sentiment-cv.json` に構造化された結果

### 3. トピック分類 (4 クラス)

```bash
python src/embed.py --input data/synthetic_topic.csv \
  --text-col text --id-col id \
  --output data/embeddings/topic.npy

python src/classify.py --embeddings data/embeddings/topic.npy \
  --labels data/synthetic_topic.csv --label-col label
```

### 4. 偽情報の二値分類 (教育用途)

```bash
python src/embed.py --input data/synthetic_disinformation.csv \
  --text-col text --id-col id \
  --output data/embeddings/disinfo.npy

python src/classify.py --embeddings data/embeddings/disinfo.npy \
  --labels data/synthetic_disinformation.csv --label-col label
```

## 期待される出力

30 件規模の合成データでは、感情分類の macro-F1 は **0.70〜0.85** 程度、トピックは **0.85〜0.95**、偽情報の二値は **0.85〜0.95** 程度が目安です (乱数シードにより変動)。

> [!NOTE]
> 少数データではフォールドごとの分散が大きくなります。`--n-splits 3` で分散を抑えるか、データを増やして安定化させてください。

## 精度改善の方向

1. **データを増やす**: `scripts/generate_synthetic_texts.py` で各クラス 20〜30 件に増やす
2. **モデルを大きくする**: `text-embedding-3-large` (3072 次元、精度 +2〜3 pt / コスト 6.5 倍)
3. **`class_weight="balanced"`** (既定): 不均衡データで重要
4. **`LinearSVC(C=1.0, class_weight="balanced")`** を試す (テキスト分類で強い)
5. **正規化**: 本スクリプトは既定で L2 正規化済み。cosine と互換

## 想定コスト (デモ 1 回)

- Embedding 30〜100 件 × 平均 60 token = 6K token × $0.02 / 1M = **$0.00012**
- 3 データセット合計でも $0.001 未満

分類自体はローカル計算 (scikit-learn) なので、追加の Azure 課金はありません。
