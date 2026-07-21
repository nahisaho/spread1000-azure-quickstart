# 03. Chignolin 100 サンプル生成 (Job 実行)

## 0. 前提

- [02. AML プロビジョニング](02-provision-aml.md) を完了
- `AZURE_RESOURCE_GROUP` / `AZURE_WORKSPACE_NAME` を export 済み
- `bioemu-1-4-1-cuda:1` environment が Build succeeded
- `gpu-a100` compute が Succeeded

## 1. なぜ Chignolin か

**Chignolin (10 残基, `GYDPETGTWG`)** は BioEmu 公式のスモークテスト対象です。

- 最小の折り畳みタンパク (β-hairpin)
- リファレンス構造 (PDB `1UAO`) が公開されている
- サンプリングは A100 で数秒、コールドスタート込みで 20 分程度
- **AlphaFold2 パラメータ 3.5 GB のダウンロード**が Job 初回に発生 (これを避けたければ [Troubleshooting §オフライン化](troubleshooting.md#alphafold-params-のオフライン化) を参照)

> [!WARNING]
> **データガバナンス**: `chignolin.fasta` を投入すると配列が **公開 ColabFold MMseqs2 サーバ (`api.colabfold.com`)** に送信されて MSA が生成されます。chignolin は公開既知配列なので問題ありませんが、**未公開・機密配列を扱う場合**は事前にローカルで A3M を生成する (下記) か、自前 MMseqs2 API を `--msa_host_url` で指定してください。

## 2. Job 内容の理解

`aml/bioemu-sample.yml` の要点:

```yaml
code: ../                              # quickstart ルートを code snapshot として送る
command: >-
  ...
  python -m bioemu.sample
  --sequence ${{inputs.sequence}}      # ../inputs/chignolin.fasta
  --num_samples ${{inputs.num_samples}}
  --output_dir ${{outputs.ensemble}}
  --model_name bioemu-v1.1
  --base_seed ${{inputs.seed}}         # サンプリング seed の起点 (bitwise 再現は保証されない)
environment: azureml:bioemu-1-4-1-cuda:1
compute: azureml:gpu-a100
inputs:
  sequence:
    type: uri_file
    path: ../inputs/chignolin.fasta    # YAML ファイル (aml/bioemu-sample.yml) から見た相対パス
    mode: download
  num_samples: 100
  seed: 20260807
outputs:
  ensemble:
    type: uri_folder
    mode: rw_mount
```

**batch サイズの自動計算**: BioEmu 内部で `batch_size = max(1, batch_size_100 × (100/L)²)` になります。L=10 (chignolin) なら batch_size = 100 (num_samples 100 でも 1 バッチで完了)。

> [!NOTE]
> `base_seed` は各バッチの seed 起点を固定しますが、**GPU モデル / CUDA / JAX / PyTorch のバージョン差、ColabFold MSA の返答差、パッケージ更新**などにより bitwise には完全再現しません。同一環境での再現性向上のための機能です。

## 3. Job 投入

```bash
cd research-fields/life-pharma-science/05-conformational-ensemble-bioemu

JOB_NAME=$(az ml job create --file aml/bioemu-sample.yml --query name -o tsv)
echo "Job: $JOB_NAME"
```

投入後の状態確認:

```bash
az ml job show --name "$JOB_NAME" --query "status" -o tsv
# Queued → Preparing → Running → Completed の順に進む
```

## 4. ログをストリーム表示

```bash
az ml job stream --name "$JOB_NAME"
```

期待する進行:

1. **Preparing** (2〜5 分): image pull + code snapshot upload
2. **Running (初回のみ)**:
   - `bioemu 1.4.1 PyTorch 2.6.x CUDA True GPU NVIDIA A100 80GB PCIe`
   - HuggingFace から `checkpoints/bioemu-v1.1/checkpoint.ckpt` (~120 MiB) をダウンロード
   - **AlphaFold2 パラメータ 3.5 GB を Google Cloud Storage からダウンロード** ← 初回のみ 3〜10 分
   - ColabFold MMseqs2 サービスに MSA を問い合わせ (chignolin なら数秒)
   - JAX による JIT コンパイル (2〜3 分)
   - Embedding 生成 → DPM sampler で 50 step
   - `topology.pdb`, `samples.xtc`, `sequence.fasta`, `batch_*.npz` を出力
3. **Completed**: 全体 15〜30 分 (Spot 中断がなければ)

## 5. 出力ファイルの確認

```bash
az ml job show --name "$JOB_NAME" \
  --query "outputs.ensemble.path" -o tsv
# → azureml://datastores/workspaceblobstore/paths/azureml/<JOB_NAME>/ensemble/
```

構造:

```
<ensemble>/
├── sequence.fasta       # 入力配列のコピー
├── topology.pdb         # トポロジ (Cα + backbone atoms)
├── samples.xtc          # フィルタ後のサンプル (frame ≤ num_samples)
└── batch_*.npz          # 内部生バッチ (通常削除して良い)
```

> [!NOTE]
> `filter_samples=True` (default) により、chain break や steric clash を含む構造が除去されるため、**保存 frame 数は要求 num_samples を下回ることがあります**。全 frame を保持したい場合は Command YAML の command に `--filter_samples=False` を追加してください (物理的妥当性は保証されません)。

## 6. 結果を手元にダウンロード

```bash
az ml job download --name "$JOB_NAME" --download-path ./downloaded
```

ダウンロード後の構造:

```
downloaded/
└── named-outputs/
    └── ensemble/
        ├── sequence.fasta
        ├── topology.pdb
        ├── samples.xtc
        └── batch_*.npz
```

整合性チェック:

```bash
pip install mdtraj numpy scikit-learn matplotlib
python scripts/verify-output.py downloaded --min-frames 50
```

期待: `✓ すべての BioEmu 出力が検証に合格 (1 run)`

## 7. コスト確認

```bash
az ml compute show --name gpu-a100 --query "current_node_count" -o tsv
# 2 分アイドル後に 0 に戻ることを確認
```

**Spot で 20 分実行 → 約 ¥50。PAYG なら約 ¥270。**

## 8. 次に試すこと

- **より長い配列**: `inputs/` に Trp-cage (20 残基, `NLYIQWLKDGGPSSGRPPPS`) や BPTI (58 残基) の FASTA を置き、Job YAML の `path:` を差し替え。ただし BPTI はジスルフィド結合を明示できないため定量比較には不向き。
- **サンプル数を増やす**: `num_samples: 1000` (chignolin なら数分で完了、A100 80GB VRAM に余裕あり)
- **seed を変える**: `seed:` を変更し、独立な run を merge (下記 XTC 結合手順)

XTC を merge する例:

```python
import mdtraj as md
run1 = md.load_xtc("downloaded1/named-outputs/ensemble/samples.xtc", top="downloaded1/named-outputs/ensemble/topology.pdb")
run2 = md.load_xtc("downloaded2/named-outputs/ensemble/samples.xtc", top=run1.top)
merged = md.join([run1, run2])
merged.save_xtc("merged.xtc")
merged[0].save_pdb("topology.pdb")
```

## チェックリスト

- [ ] Job が `Completed` になった
- [ ] `topology.pdb` + `samples.xtc` + `sequence.fasta` がダウンロードされた
- [ ] `verify-output.py` が合格
- [ ] `gpu-a100` の `current_node_count` が 0

## 次のステップ

→ [04. 結果解析 (RMSD, Rg, クラスタリング)](04-analyze-ensemble.md)
