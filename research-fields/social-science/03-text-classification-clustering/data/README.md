# サンプルデータ

すべて教材用の**CC0 合成データ**です。実在の**人物・組織**は含みません。地名について、「京都」「金沢」等の一般的な地理名詞は文脈上登場する場合がありますが、これらは特定の店舗や事業所を指すものではなく、教材の題材として使われている一般名詞です。

| ファイル | ラベル | 用途 |
|---|---|---|
| `synthetic_sentiment.csv` | positive / negative / neutral | 感情分類 (旅行レビュー風) |
| `synthetic_topic.csv` | 観光 / 食事 / 宿泊 / 交通 | トピック分類・クラスタリング |
| `synthetic_disinformation.csv` | fact / misinformation | 二値分類 (研究教育例のみ) |

> [!WARNING]
> `synthetic_disinformation.csv` は**分類技術の教育用途**であり、実際の偽情報判定システムとして使ってはいけません。このデータは**表現スタイル (陰謀論的語彙、根拠なき断定)** で `fact` / `misinformation` を弁別しており、命題の**真偽そのものは検証していません**。実運用には根拠検索・人間確認・第三者ファクトチェッカーとの連携が必須です (詳細: [docs/07-ethics-and-limits.md](../docs/07-ethics-and-limits.md))。

## ライセンス

本ディレクトリのファイルは [CC0-1.0](LICENSE) (パブリックドメイン相当) で提供されます。

## データ拡張

`scripts/generate_synthetic_texts.py` で gpt-5.4-mini を使って各クラスにサンプルを追加できます:

```bash
python scripts/generate_synthetic_texts.py --task sentiment --n-per-class 10
```

追加コストは 1 クラスあたり数円程度です (詳細: [docs/03-prepare-data.md](../docs/03-prepare-data.md))。
