# 03 — TamGen をセットアップして推論を実行

所要 40〜70 分（うち待機 30〜50 分）。ここでは GPU コンピュート上で TamGen をセットアップし、任意の PDB を標的に分子を生成します。

## 1. Compute Instance のターミナルを開く

1. [Azure ML Studio](https://ml.azure.com) を開く（前ステップの `studioUrl`）
2. 左メニュー **コンピューティング** → **コンピューティング インスタンス** タブ
3. `ci-tamgen-<yourname>-<suffix>` の行にある **ターミナル** をクリック（ブラウザ内でシェルが開く）

> [!TIP]
> VS Code 派の方は、同じ行の **VS Code (Web)** または **VS Code (Desktop)** リンクからリモート接続できます。以降のコマンドはどこで打っても同じです。

## 2. セットアップスクリプトを取得して確認

セキュリティのため **`curl | bash` は使いません**。まずスクリプトを取得し、目視で確認してから実行します。

```bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/nahisaho/spread1000-azure-quickstart.git

# スクリプトを読んで内容を確認 (推奨)
less spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh
```

## 3. セットアップスクリプトを実行

```bash
bash spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh
```

このスクリプトは以下を自動実行します（30〜50 分）：

| ステップ | 内容 |
|---:|---|
| 1 | `microsoft/TamGen` を **ピン留め commit** で `~/TamGen` に `git clone` |
| 2 | `conda create -n TamGen python=3.9`（既存ならスキップ） |
| 3 | 上流 `setup_env.sh` を **非対話モード** で実行（PyTorch 2.3.0 + CUDA 12.1、fairseq、RDKit 等） |
| 4 | Zenodo から `checkpoints.zip`（**2.34 GB**）と `gpt_model.zip`（**786 MB**）をダウンロードし、**MD5 で整合性検証** |
| 5 | CUDA 動作確認（`torch.cuda.is_available()` かつ GPU テンソル演算が通ることを確認、失敗すると非ゼロで終了） |

**成功時の期待出力**：

```
CUDA available   : True
CUDA device      : NVIDIA A100 80GB PCIe
GPU tensor op OK : sum=...
✅ TamGen セットアップ完了
```

エラーが出た場合は [troubleshooting.md](troubleshooting.md) を参照。

## 4. 推論を実行

**Option A: 用意した Python ラッパースクリプト（推奨・任意 PDB に対応）**

上流の `scripts/example_inference.sh` は `data/crossdocked/bin/` を要求します（この 100 GB 超のデータセットはリポジトリに含まれず、事前構築が必要）。したがって **クリーンインストールでは動かない** ため、本クイックスタートは独自スクリプトを提供します。

```bash
# 例: PDB 3WZE (Mycobacterium tuberculosis の DNA gyrase B) を標的に 50 個生成
bash ~/spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/run-inference.sh 3wze 50
```

10〜30 分程度で、`~/TamGen/output/3wze/` に以下が出力されます：

| ファイル | 内容 |
|---|---|
| `generated_molecules.smi` | 生成分子 (SMILES 1 行 1 分子) |
| `generated_molecules.csv` | SMILES + 物性 (MW / LogP / QED / TPSA / HBD / HBA / Lipinski) |
| `generation_stats.json` | 生成統計 (有効数・Lipinski 適合数・平均多様性) |

内部の流れは [`scripts/generate_from_pdb.py`](../scripts/generate_from_pdb.py) を参照。API は上流 `TamGen_Demo.py` に厳密に従います：

```python
prepare_pdb_data(pdb_id="3wze", DemoDataFolder="TamGen_Demo_Data", thr=10.0)
worker = TamGenDemo(
    data="TamGen_Demo_Data",
    ckpt="checkpoints/crossdock_pdb_A10/checkpoint_best.pt",
    use_conditional=True,
)
worker.reload_data(subset="gen_3wze")
results_set, ref_mol = worker.sample(m_sample=50, maxseed=101)
# results_set は {smiles: rdkit_mol} の dict
```

**Option B: 上流 Jupyter ノートブック（対話的）**

> [!NOTE]
> 上流のノートブック名は **`interctive_decode.ipynb`**（"interactive" のタイポ）です。README は "interactive" と書いていますが、実ファイルはこの綴りです。

1. Azure ML Studio 左メニュー **ノートブック**
2. **ファイル** タブで **アップロード** から新規タブを開くか、ターミナルで下記を実行して Studio 内で見えるようにコピー：

    ```bash
    mkdir -p "${HOME}/cloudfiles/code/Users/$(whoami)/tamgen"
    cp ~/TamGen/interctive_decode.ipynb \
       "${HOME}/cloudfiles/code/Users/$(whoami)/tamgen/interactive_decode.ipynb"
    ```

3. Studio の **ノートブック** → 上記のパスを開く
4. 右上の **カーネル** で **Python 3.9 (TamGen)** を選択（`setup-tamgen.sh` の最後に自動登録済み）
5. 上から順にセル実行

## 5. 自分の PDB で試す（応用）

上流 API に完全準拠したまま任意 PDB を試せます：

```bash
# 例: EGFR T790M/L858R 変異体
bash ~/spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/run-inference.sh 5edq 100
```

独自 PDB ファイルを使いたい場合は、`~/TamGen/customized_example/` にファイルを置き、上流の [customized_example/README](https://github.com/microsoft/TamGen/tree/main/customized_example) に従って CSV を書きます。

## 完了チェック

- [ ] `run-inference.sh 3wze 50` がエラーなく完了
- [ ] `~/TamGen/output/3wze/generation_stats.json` に有効分子数と Lipinski 適合数が記録されている

**次**: [04-interpret-results.md](04-interpret-results.md) — 生成結果を読み解く

