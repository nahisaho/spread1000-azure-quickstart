# 03 — ESMFold 環境構築と推論実行

所要 15〜30 分。ここでは Compute Instance に SSH または Jupyter でアクセスし、ESMFold を実行します。

## 1. Compute Instance に接続

**方法 A: Azure ML Studio の Jupyter**（初回推奨）
1. [Azure ML Studio](https://ml.azure.com) → 対象 Workspace を選択
2. 左メニュー **Compute** → Compute Instance を選択 → **Jupyter** をクリック
3. ブラウザで JupyterLab が開く

**方法 B: VS Code Remote**（推奨・大量ファイル操作向け）
- VS Code 拡張 **Azure Machine Learning** をインストール
- コマンドパレット → `Azure ML: Connect to Compute Instance`

## 2. リポジトリ取得と環境構築

Jupyter ターミナル or SSH ターミナルで以下を実行：

```bash
cd ~
git clone https://github.com/nahisaho/spread1000-azure-quickstart.git
cd spread1000-azure-quickstart/quickstarts/molecular-gnn/esmfold-structure-prediction

# 環境構築（8.44GB の重みダウンロードを含む、10〜15 分）
bash scripts/setup-esmfold.sh
```

`setup-esmfold.sh` は以下を行います：
1. conda 環境 `esmfold` (Python 3.10) を作成
2. PyTorch 2.3.0 + CUDA 12.1 をインストール
3. `transformers`, `accelerate`, `biopython`, `py3Dmol` をインストール
4. HuggingFace キャッシュを `~/cloudfiles/hf_cache` に設定（Compute Instance 再作成時も重みが残る）
5. `facebook/esmfold_v1` の重み（8.44 GB）を事前ダウンロード & SHA256 検証
6. `ipykernel` に **Python 3.10 (esmfold)** として登録

**HuggingFace キャッシュを `~/cloudfiles/` に置く理由**: `~/cloudfiles/` は Workspace 共有ストレージ（Azure Blob）にマウントされる永続領域。Compute Instance を削除しても消えないため、次回作成時に **重みを再ダウンロードせずに済みます**（8.44GB × 通信料の節約）。

## 3. サンプル配列で動作確認

```bash
conda activate esmfold

# 76 aa のユビキチン（動作確認用）
python scripts/run-inference.py \
  --input scripts/examples/ubiquitin.fasta \
  --output ./output/ \
  --chunk-size 64 \
  --half-precision
```

**期待される出力**（T4 の場合、約 20〜40 秒）：

```
[INFO] Loading facebook/esmfold_v1 (cache: /home/azureuser/cloudfiles/hf_cache)...
[INFO] Model loaded in 42.3s
[INFO] Applying FP16 to ESM stem + chunk_size=64
[INFO] Processing 1 sequence(s)...
[INFO] ubiquitin (76 aa): 8.2s | mean pLDDT = 93.4
[INFO] Saved: ./output/ubiquitin.pdb
[INFO] Saved: ./output/ubiquitin_plddt.csv
[INFO] Done in 51.1s total
```

**出力ファイル**：
- `output/ubiquitin.pdb` — 3D 構造（B-factor 列に pLDDT）
- `output/ubiquitin_plddt.csv` — 残基番号ごとの pLDDT（0〜100）

## 4. 自分の配列で推論

FASTA ファイル（複数配列可）を用意して実行：

```bash
# 単一 FASTA、複数配列
python scripts/run-inference.py \
  --input my_proteins.fasta \
  --output ./output/ \
  --chunk-size 64 \
  --half-precision \
  --max-length 800    # 安全のため上限を設定（T4 は 600 まで推奨）
```

### GPU 別の推奨オプション

| SKU | オプション | 対応配列長（絶対上限 1024 aa） |
|---|---|---|
| **T4 16GB** | `--half-precision --chunk-size 64` | 〜600 aa |
| **T4 16GB（長鎖）** | `--half-precision --chunk-size 16` | 〜1024 aa（時間 3〜5 倍） |
| **A100 80GB** | （オプション不要） | 〜700 aa |
| **A100 80GB（長鎖）** | `--half-precision --chunk-size 32` | 〜1024 aa |
| **H100 80GB** | （オプション不要） | 〜700 aa（A100 の 1.5〜2 倍高速） |

> [!IMPORTANT]
> **配列長の絶対上限は 1024 残基** です（ESMFold の位置埋め込み設計）。これを超える配列は `run-inference.py` が自動でスキップします。長鎖はドメイン分割（例: 500 aa ずつオーバーラップ 100 aa）するか、AlphaFold2/ColabFold の使用を検討してください。

> [!IMPORTANT]
> **`add_special_tokens=False` が必要** です。`run-inference.py` は既に対応済みですが、独自実装で `AutoTokenizer` を使う際は必ず指定してください。指定しないと構造が破綻します。

### Jupyter ノートブックで対話的に

```python
# ノートブックのカーネル選択: "Python 3.10 (esmfold)"
import os
os.environ["HF_HOME"] = "/home/azureuser/cloudfiles/hf_cache"

from transformers import AutoTokenizer, EsmForProteinFolding
import torch

tokenizer = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
model = EsmForProteinFolding.from_pretrained(
    "facebook/esmfold_v1", low_cpu_mem_usage=True
).cuda().eval()
model.esm = model.esm.half()
model.trunk.set_chunk_size(64)

sequence = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
tokens = tokenizer(sequence, return_tensors="pt", add_special_tokens=False)
tokens = {k: v.cuda() for k, v in tokens.items()}

with torch.no_grad():
    out = model(**tokens)

# pLDDT の値域を 0-100 に正規化 (transformers のバージョンによって 0-1 で返る場合がある)
if float(out["plddt"].max().detach().cpu()) <= 1.5:
    out["plddt"] = out["plddt"] * 100.0

pdb_str = model.output_to_pdb(out)[0]
plddt = out["plddt"][0, :, 1].cpu().numpy()   # index 1 = Cα atom
print(f"Mean pLDDT: {plddt.mean():.2f}")
print(f"pLDDT < 50 residues: {(plddt < 50).sum()} / {len(plddt)}")

with open("ubiquitin.pdb", "w") as f:
    f.write(pdb_str)
```

## 5. バッチ処理（数百配列）

```bash
python scripts/run-inference.py \
  --input all_targets.fasta \
  --output ./output/batch/ \
  --half-precision \
  --chunk-size 64 \
  --sort-by-length \
  --summary ./output/batch/summary.csv
```

`--sort-by-length` は配列を短い順にソートしてから処理（GPU メモリ効率）。`--summary` は各配列の `seq_id, length, mean_plddt, ptm, inference_sec` を CSV に出力します。

## 完了チェック

- [ ] `conda activate esmfold` で環境がアクティブになる
- [ ] `nvidia-smi` で GPU が見える（`nvidia-smi` は `esmfold` 環境不要）
- [ ] `scripts/examples/ubiquitin.fasta` の推論が正常終了し、mean pLDDT ≒ 90 前後
- [ ] `output/ubiquitin.pdb` を PyMOL または py3Dmol で開ける

**次**: [04-interpret-results.md](04-interpret-results.md) — pLDDT の見方と可視化
