# 02. データ取得 (Materials Project API)

## 実行

```bash
python src/fetch_data.py --output data/mp-bandgap.parquet
```

既定条件 (1〜3 元素、band gap 0.1〜5.0 eV) で約 1500 件を取得します (数分)。

## 主要オプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--num-elements-min / --max` | 1 / 3 | 元素数フィルタ (mp-api では `nelements` に送信) |
| `--band-gap-min / --max` | 0.1 / 5.0 | band gap (eV) 範囲 |
| `--chunk-size` | 1000 | 1 チャンクあたりの取得件数 |
| `--num-chunks` | 2 | 取得するチャンク数 (上限件数 = chunk-size × num-chunks) |
| `--limit` | 1500 | 取得後に **material_id 昇順**でソートしてから先頭 N 件をスライス |
| `--force` | off | 出力ファイルが既に存在する場合に上書きを許可 |
| `--expected-sha256` | なし | 生成 parquet の 64 文字 SHA-256 を事前に指定した場合、一致しなければ削除して失敗 |

> [!IMPORTANT]
> `--limit` 適用前に `material_id` で昇順ソートするため、同じ MP DB バージョン × 同じフィルタなら **同じサブセット**が再現されます。ただし MP DB がバージョン更新されると内容は変わりますので、`data/mp-bandgap.manifest.json` の `mp_database_version` と `parquet_sha256` (フル 64 文字) を必ず控えてください。

## 出力

- `data/mp-bandgap.parquet` — material_id, formula_pretty, band_gap, nsites, nelements, structure_json (6 列)
- `data/mp-bandgap.manifest.json` — mp-api バージョン、DB バージョン、クエリ条件全項目、レコード数、**全 material_id リスト**、フル 64 文字 SHA-256、取得日時

> [!IMPORTANT]
> `include_gnome=False` を必ず指定しています (`fetch_data.py` の既定)。GNoME (117,000 材料) は **CC BY-NC** ライセンスで本教材の CC BY 4.0 統一運用と非互換のため除外しています。GNoME を含めたい場合は GNoME 個別ライセンス条件を直接確認してください。

## クエリのカスタマイズ

例: 二元素化合物のみ、band gap 1〜3 eV (光触媒候補):

```bash
python src/fetch_data.py --output data/photocat.parquet \
  --num-elements-min 2 --num-elements-max 2 \
  --band-gap-min 1.0 --band-gap-max 3.0
```

## レート制限とキャッシュ

- MP API は **リクエスト頻度 (req/s)** で制限されます
- `chunk_size` を大きくすると 1 リクエストで多く取れるため、総リクエスト数はむしろ**減ります**。`429` を防ぐには `chunk_size` を大きく保ったまま並列実行を控え、リトライ間隔を空けてください
- 一度取得した Parquet はローカルキャッシュとして扱い、頻繁に再取得しないでください
- 大量ダウンロードが必要な場合は [MP 公式の bulk download](https://docs.materialsproject.org/downloading-data/using-the-api/tips-for-large-downloads.md) を使い、API を叩き続けないでください

## band gap 分布の確認

```python
import pandas as pd
df = pd.read_parquet("data/mp-bandgap.parquet")
print(df.band_gap.describe())
df.band_gap.hist(bins=40)
```

MP の band gap は **DFT 由来** (PBE / GGA + Hubbard U 等) で、実験値より系統的に小さくなります (bandgap underestimation problem)。詳細は [06-ethics-and-limits.md](06-ethics-and-limits.md) を参照。
