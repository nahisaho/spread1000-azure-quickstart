# 03. サンプルデータの準備

## 同梱データ

以下 3 種類の **CC0 合成データ**が `data/` に既に用意されています。

| ファイル | 行数 | クラス | シナリオ例 |
|---|---:|---|---|
| `synthetic_sentiment.csv` | 30 | positive / negative / neutral | 観光レビュー感情分類 |
| `synthetic_topic.csv` | 32 | 観光 / 食事 / 宿泊 / 交通 | 旅行日記トピック分類・クラスタリング |
| `synthetic_disinformation.csv` | 24 | fact / misinformation | 偽情報検出の教育用二値分類 |

いずれも `id, label, text, synthetic` の 4 列 CSV です。実運用には**明らかに不足**する量なので、手法検証用としてのみ使ってください。

> [!WARNING]
> `synthetic_disinformation.csv` は **misinformation の判定モデルを構築する参考実装**であって、実際に真偽判定を下すために使うものではありません。詳細は [07-ethics-and-limits.md](07-ethics-and-limits.md) を参照。

## データ拡張 (任意)

より多くのサンプルが欲しい場合は `scripts/generate_synthetic_texts.py` で追加生成できます。

```bash
# 感情ラベル 3 クラスにそれぞれ 10 件追加
python scripts/generate_synthetic_texts.py --task sentiment --n-per-class 10

# トピック 4 クラスにそれぞれ 10 件追加
python scripts/generate_synthetic_texts.py --task topic --n-per-class 10

# 偽情報 2 クラスにそれぞれ 10 件追加
python scripts/generate_synthetic_texts.py --task disinformation --n-per-class 10
```

- 既存 CSV に追記され、`data/manifest.json` に生成履歴 (モデル、バージョン、行数、SHA-256) が記録されます
- 生成物は必ず**人間でレビュー**してから使用してください (合成データにも品質のばらつきがあります)

コスト概算 (1 クラス 10 件、gpt-5.4-mini):
- 出力 ~200 tokens × 10 件 × クラス数 → 数円 (例: 3 クラスで約 $0.03)

## 独自データを使いたい場合

CSV の必須列は `text` のみ (分類なら `label` も)。任意の id 列は `--id-col` で指定できます。

```bash
python src/embed.py --input path/to/mydata.csv \
  --text-col comment --id-col row_id \
  --output data/embeddings/mydata.npy
```

> [!IMPORTANT]
> 個人情報・機微情報を含む実データを扱う際は、必ず所属機関の倫理審査を通し、PII のマスキングを済ませてからアップロードしてください。詳細は [07-ethics-and-limits.md](07-ethics-and-limits.md)。
