# Troubleshooting

## インストール系

### `bitsandbytes` が import できない

```
ImportError: Please install bitsandbytes to use 4-bit quantization
```

**原因**: CPU 環境で 4-bit quant を要求している、または bitsandbytes が CUDA と非互換

**対処**:
- CPU パスなら `--no-quant` フラグを追加
- GPU パスなら `pip install bitsandbytes==0.49.2 --force-reinstall`
- WSL2 では NVIDIA CUDA WSL ドライバの導入も必要

### `torch` が CUDA を認識しない

```python
>>> import torch; print(torch.cuda.is_available())
False
```

**対処**:
1. `nvidia-smi` で GPU が見えるか確認
2. `pip uninstall torch torchvision` してから `pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126`
3. WSL2 → Windows 側で NVIDIA CUDA for WSL ドライバをインストール ([Microsoft 手順](https://learn.microsoft.com/windows/wsl/tutorials/gpu-compute))

### `RuntimeError: bf16 is not supported on this GPU`

T4 は bf16 非対応です。`train_lora.py` は `fp16=True, bf16=False` を自動設定しますが、独自スクリプトを書く場合は必ず `fp16` を選んでください。

## 訓練系

### CUDA Out of Memory

**対処** (優先順):
1. `--batch-size 1 --grad-accum 8` (実効バッチは変えず VRAM を減らす)
2. `--max-seq-length 384` または `256` (T4 では 512 が現実的上限)
3. `--lora-r 8` に下げる
4. Gradient checkpointing は既に有効化済み

### `train_loss` が減らない / NaN

- `train_loss` が increasing → `--lr 1e-4` に下げる
- `train_loss` が NaN → fp16 の underflow。`--max-seq-length` を短く or `--lr 5e-5`
- `grad_norm` が 100 以上 → gradient explosion。同上 + `max_grad_norm=1.0` を SFTConfig に追加

### 訓練が始まらない (数分待ってもログ無し)

- 初回モデル DL 中の可能性。`ls -lh ~/.cache/huggingface/hub/` で進捗確認
- HF Hub が遅いなら `HF_HUB_ENABLE_HF_TRANSFER=1` を環境変数に

## 推論・比較系

### `compare.py` で応答が同じ

- `PeftModel.from_pretrained` が失敗して adapter が有効化されていない可能性
- `data/adapter/final/adapter_config.json` が存在し、`base_model_name_or_path` が正しいか確認
- `lora.disable_adapter()` と有効化の両方で出力が同じ → LoRA が学習していない、`train_loss` を再確認

### 応答が無限生成される、EOS で止まらない

**主要原因**: `pad_token = eos_token` の誤設定（`train_lora.py` では `unk_token` を優先）

**対処**:
- `tokenizer.pad_token` の設定を確認 (`train_lora.py` の該当箇所)
- 推論時に `generate(max_new_tokens=200)` を必ず指定

### 応答に英語が混じる

- ベースモデル (Phi-4-mini) は multilingual なので英語混在は正常
- LoRA 適応後もこの傾向が残ることがある
- 対処: dolly-ja サンプル数を増やす (`--n 2000`)、または `--epochs 5` に

## Azure ML 系

### ジョブが Queued のまま進まない

**原因候補**:
1. NCasT4v3 vCPU クォータ不足 → **Usage + quotas** で確認
2. Region に空き容量がない → Japan West / East US など別 region を試す
3. Compute Cluster の max_nodes が 0 → Studio で cluster 設定を確認

### `AzureML-*` 環境がない

curated 環境は時期により更新されます。以下で確認:
```bash
az ml environment list --resource-group <RG> --workspace-name <WS> --query "[].name" -o tsv
```
なければ [Azure ML curated environments](https://learn.microsoft.com/azure/machine-learning/resource-curated-environments) から現行の環境名を選ぶ、または custom Dockerfile を指定。

### ジョブ完了後もクラスタが 0 に戻らない

- Idle scale-down (5 分) を待つ、または手動で Cluster → Edit → Min = 0 → Save
- それでも駄目なら Cluster を削除 (`az ml compute delete --name t4-cluster -g $RG -w $WS --yes`)。**自動再作成はされません**。次回使用時は `az ml compute create -f infra/t4-cluster.yml -g $RG -w $WS` で手動再作成してください
