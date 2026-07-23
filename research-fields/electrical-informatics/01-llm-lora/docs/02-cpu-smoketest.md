# 02: CPU スモークテスト

GPU クォータ申請待ちの間、または課金を発生させたくないときのために、**ローカル CPU で完結する動作検証パス** を用意しています。同じスクリプトを `--device cpu --no-quant` オプションで実行するだけです。

## 用意するもの

- Python 3.12 環境（[01-prerequisites.md](01-prerequisites.md) の CPU セクション）
- 8 GB 以上の RAM
- 3 GB 程度のディスク余裕（Qwen2.5-0.5B モデルのダウンロード）
- 10〜15 分の時間

## 手順

### Step 1: 依存パッケージ

```bash
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-cpu.txt
```

### Step 2: データ準備（100 サンプル）

```bash
python src/prepare_data.py --n 100 --output data/train.jsonl
```

期待出力:
```
[data] loading kunishou/databricks-dolly-15k-ja …
[data] total rows available: 15015
[data] sampled 100 rows with seed=42
[data] wrote 100 prompt/completion samples → data/train.jsonl
[data] wrote 10 eval prompts → data/eval_prompts.json
```

### Step 3: LoRA 訓練（Qwen2.5-0.5B, 1 epoch）

```bash
python src/train_lora.py \
    --model Qwen/Qwen2.5-0.5B-Instruct \
    --data data/train.jsonl \
    --epochs 1 \
    --batch-size 1 --grad-accum 4 \
    --device cpu --no-quant \
    --max-seq-length 384 \
    --output data/adapter/
```

**予期される出力**:
```
[model] loading tokenizer for Qwen/Qwen2.5-0.5B-Instruct
[model] loading Qwen/Qwen2.5-0.5B-Instruct (device=cpu, 4-bit=False)
[model] total parameters: 494,032,768
[data] loading data/train.jsonl
[data] 100 prompt/completion samples
[train] starting: epochs=1, batch=1x4, lr=0.0002, LoRA r=16
{'loss': 2.4123, 'grad_norm': 3.12, 'learning_rate': 0.00018, 'epoch': 0.4}
{'loss': 2.1856, 'grad_norm': 2.87, 'learning_rate': 0.00012, 'epoch': 0.8}
{'train_runtime': 762.4, 'train_samples_per_second': 0.13, 'train_loss': 2.29, ...}
[train] saved LoRA adapter → data/adapter/final
[train] metrics: {'train_runtime_sec': 762.4, ...}
```

> **NOTE**: CPU 上での 1 epoch は Qwen2.5-0.5B + 100 サンプルで **10〜15 分**、より大きなモデル（Phi-4-mini 3.8B）だと数時間になります。CPU パスでは **Qwen2.5-0.5B に固定** することを強く推奨します。

### Step 4: 応答比較

```bash
python src/compare.py \
    --adapter data/adapter/final \
    --model Qwen/Qwen2.5-0.5B-Instruct \
    --prompts data/eval_prompts.json \
    --device cpu \
    --max-new-tokens 150
```

各プロンプトについて `--- Base ---` と `--- LoRA-adapted ---` が並べて表示されます。CPU + 0.5B モデルの推論は 1 プロンプト 30〜60 秒程度です。

## スモークテストで確認すべきこと

✅ `train_loss` が **単調に減少** している（epoch 完了時 2.0 前後）
✅ LoRA アダプタが `data/adapter/final/adapter_model.safetensors` に保存されている（ファイルサイズ 5〜30 MB 程度）
✅ `compare.py` が `--- Base ---` と `--- LoRA-adapted ---` の両方で異なる応答を出力する
✅ `data/adapter/metrics.json` が JSON として妥当

## スモークテストで**確認できないこと**

❌ 実用的な日本語応答の質（0.5B モデル、100 サンプル、1 epoch では限界）
❌ QLoRA 4-bit の動作（CPU では quantization を無効化するため）

これらは GPU パスで検証します → [03-aml-gpu.md](03-aml-gpu.md)。

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `ImportError: bitsandbytes` | CPU に quant 依存を要求している | `--no-quant` を必ず付ける |
| Killed / OOM | RAM 不足 | `--batch-size 1 --grad-accum 8` に、あるいは `--max-seq-length 256` |
| データ DL が遅い | HF Hub のミラー | `HF_HUB_ENABLE_HF_TRANSFER=1 pip install hf_transfer` |
| 学習開始まで 5 分以上 | 初回モデル DL 中 | `~/.cache/huggingface/hub/` を確認、待つ |
