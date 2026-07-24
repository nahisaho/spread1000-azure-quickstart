# 社会科学 03: テキスト分類・トピッククラスタリング

Azure OpenAI Embeddings + scikit-learn で日本語短文の**分類・クラスタリング・ラベル付け**を行う教材用最小パイプラインです。SPReAD-1000 の想定研究テーマ（偽情報検出、SNS/観光レビュー分析、金融テキスト解析）向けに、CC0 の合成データセットを同梱しています。

## 対象読者

- Azure と Python は触ったことがあるが、Embeddings / ベクトル検索 / クラスタリングは初めて
- 少量（30〜60 件）の日本語ラベル付きテキストで**分類器のベースライン**と**教師なしトピッククラスタ**を素早く試したい
- 本番の意思決定ではなく、**手法検証・教材・可視化**を目的とする

## 学習内容

1. **Embeddings 生成** — `text-embedding-3-small` (1536次元) で日本語短文をベクトル化
2. **分類** — LogisticRegression + StratifiedKFold で macro-F1 を評価
3. **クラスタリング** — KMeans + silhouette score でクラスタ数を決定
4. **ラベル生成** — 各クラスタの重心近傍テキストを `gpt-5.4-mini` に渡し、日本語ラベルを Structured Outputs で取得

補足: UMAP による 2 次元可視化のサンプルコードは [docs/05-cluster.md](docs/05-cluster.md) 末尾に掲載しています (追加ライブラリ `umap-learn` が必要)。

## 使用モデル

| モデル | デプロイ SKU | 用途 | 概算コスト (デモ 1 回) |
|---|---|---|---|
| `text-embedding-3-small` v1 | Standard (Regional Japan East) | テキスト → 1536 次元ベクトル | $0.0002 |
| `gpt-5.4-mini` v2026-03-17 | GlobalStandard | クラスタラベル生成 | $0.03 |

> [!IMPORTANT]
> Embedding-3 系 (small / large) と ada-002 系はいずれも 2027-04-15 に retirement 予定です (2026-07 時点、Microsoft Learn の "model retirements" を都度確認してください)。ada-002 系は 2027-04-15 まで動作しますが、Embedding-3 系の方が精度・コスト面で優位のため、新規実装では small を推奨します。

## 主要な設計判断

- **v1 API を採用**: `OpenAI(base_url="{endpoint}/openai/v1/")` により日付付き `api-version` 不要
- **Azure CLI 認証 (ローカル) / Managed Identity (Azure 上で実行時)**: `DefaultAzureCredential` は `az login` トークン → Managed Identity → 他 credentials の順にフォールバックします。ローカル開発では Azure CLI credentials、Container Apps / AML 上で動かす場合は Managed Identity が使われます。トークンオーディエンスは `https://ai.azure.com/.default`。
- **合成データのみ**: 実 SNS / ニュース / レビューは著作権・規約上の懸念があるため、AI 生成の CC0 データを同梱
- **形態素解析は原則不要**: 埋め込み入力には Unicode 正規化のみ。SudachiPy は c-TF-IDF での説明用途に限定
- **GPT-5 系は `temperature` 非対応**: `reasoning_effort=["low"|"medium"|"high"]` を使用（既定 `low`）

## クイックスタート

```bash
# 1. インフラ準備 (Bicep デプロイ)
export AZURE_RESOURCE_GROUP=rg-spread-social-03
cd infra && ./deploy.sh

# 2. Python 環境と .env の読み込み
cd .. && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a

# 3. 埋め込み生成 (3 データセット分)
python src/embed.py --input data/synthetic_sentiment.csv \
  --text-col text --id-col id --output data/embeddings/sentiment.npy
python src/embed.py --input data/synthetic_topic.csv \
  --text-col text --id-col id --output data/embeddings/topic.npy
python src/embed.py --input data/synthetic_disinformation.csv \
  --text-col text --id-col id --output data/embeddings/disinfo.npy

# 4. 分類器 (StratifiedKFold 5-fold)
python src/classify.py --embeddings data/embeddings/sentiment.npy \
  --labels data/synthetic_sentiment.csv --id-col id --label-col label

# 5. クラスタリング + 日本語ラベル生成
python src/cluster.py --embeddings data/embeddings/topic.npy \
  --texts data/embeddings/topic.cleaned.csv --id-col id --text-col cleaned_text --k-range 2 6
python src/label_clusters.py --clusters data/output/topic-clusters.json
```

詳細は [docs/](docs/) を参照。

## ドキュメント

1. [01 前提条件](docs/01-prerequisites.md)
2. [02 Azure リソースの払い出し](docs/02-provision.md)
3. [03 サンプルデータの準備](docs/03-prepare-data.md)
4. [04 分類](docs/04-classify.md)
5. [05 クラスタリングとラベル生成](docs/05-cluster.md)
6. [06 クリーンアップ](docs/06-cleanup.md)
7. [07 倫理と限界](docs/07-ethics-and-limits.md)

トラブルシューティング: [troubleshooting.md](troubleshooting.md)

## 想定コスト

デモを 1 回実行するとおよそ **$0.03〜0.05 (¥4〜8)** です。合成データを再生成すると追加で $0.05〜0.10 かかります。詳細は各 docs 内で試算しています。
