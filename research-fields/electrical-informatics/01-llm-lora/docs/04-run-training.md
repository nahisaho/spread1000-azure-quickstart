# 04: 訓練実行 — ハイパーパラメータの意味

## `src/train_lora.py` の CLI オプション

```
python src/train_lora.py [OPTIONS]
```

| オプション | 既定値 | 意味・調整のヒント |
|---|---|---|
| `--model` | `microsoft/Phi-4-mini-instruct` | ベースモデルの HF ID。CPU では `Qwen/Qwen2.5-0.5B-Instruct` |
| `--model-revision` | *(必須)* | モデルの commit SHA（再現性のため必須）|
| `--dataset-revision` | *(必須)* | データセットの commit SHA（再現性のため必須）|
| `--trust-remote-code` | `False` | モデルリポジトリのリモートコードを許可（既定は無効）|
| `--data` | `data/train.jsonl` | `prepare_data.py` で生成した chat JSONL |
| `--output` | `data/adapter/` | 保存先ディレクトリ |
| `--epochs` | `3` | 学習エポック数 |
| `--max-steps` | `-1` | ステップ数で上書き（`-1` = epochs を使用）|
| `--batch-size` | `2` | GPU 当たりのバッチサイズ。T4 16GB QLoRA では 2 が上限 |
| `--grad-accum` | `4` | 勾配累積ステップ数。実効バッチ = `batch-size * grad-accum` |
| `--lr` | `2e-4` | Adam 学習率。LoRA では `1e-4〜5e-4` の範囲が定番 |
| `--warmup-ratio` | `0.03` | ウォームアップ比率 `[0, 1)` |
| `--max-seq-length` | `512` | トークン列の最大長。長くすると VRAM 消費増大 |
| `--lora-r` | `16` | LoRA ランク。**参考値** として r=16, alpha=32 を設定；8〜32 が定番 |
| `--lora-alpha` | `32` | LoRA scaling factor。`alpha = 2 * r` が経験的定番 |
| `--lora-dropout` | `0.05` | LoRA 層の dropout `[0, 1)` |
| `--device` | `auto` | `auto` (CUDA→CPU fallback) / `cuda` / `cpu` |
| `--no-quant` | `False` | 4-bit 量子化を無効化。CPU では必須 |
| `--seed` | `42` | 乱数シード |
| `--max-gpu-hours` | `1.0` | GPU 使用のウォールクロック制限（時間）|
| `--allow-long-run` | `False` | 2 時間超の訓練を許可するフラグ |
| `--resume-from-checkpoint` | `None` | Spot VM 中断後の再開用チェックポイントパス |
| `--model-license` | `None` | 事前承認リスト外のモデルのライセンス SPDX ID |
| `--accept-model-license` | `False` | モデルライセンスに同意したことを確認するフラグ |

## 学習プロセスの流れ

```
1. ライセンスチェック (事前承認済みモデル or --accept-model-license)
2. 乱数シード設定 (完全決定論モード: CUBLAS_WORKSPACE_CONFIG, cudnn.deterministic)
3. Tokenizer 読み込み (--model-revision で固定)
   - pad_token_id が None の場合 → "[PAD]" を追加し embeddings をリサイズ
   - model.config.pad_token_id と model.generation_config.pad_token_id も更新
4. モデル読み込み
   - GPU + QLoRA: BitsAndBytesConfig で 4-bit NF4 量子化
   - GPU + LoRA:  fp16 でロード
   - CPU:         fp32 でロード
5. QLoRA 場合: prepare_model_for_kbit_training (use_reentrant=False)
6. データ読み込み → 90%/10% で train/eval 分割 (seed 固定)
7. LoRA 設定 (r, alpha, dropout, target_modules="all-linear")
   → 適用後に trainable module 名をログ出力
8. SFTConfig 設定 (eval_strategy="epoch", load_best_model_at_end=True, EarlyStopping)
9. SFTTrainer で訓練ループ実行
   → 各 epoch 後: eval_loss 計算 → EarlyStoppingCallback(patience=1) で過学習停止
   → FiniteLossCallback: loss/eval_loss が非有限なら即座に RuntimeError
10. 訓練後: train_loss の有限性チェック
11. LoRA アダプタ + tokenizer を final/ に保存
12. metrics.json (allow_nan=False) + manifest.json (SHA-256、ライセンス情報) を出力
13. src/verify.py で最終整合性チェック
```

## Tokenizer のパディング設定

**Phi-4-mini の場合**:

`tokenizer.pad_token_id` が `None` のとき、以下のロジックで `[PAD]` トークンを追加します:

```python
added = 0
if tokenizer.pad_token_id is None:
    added = tokenizer.add_special_tokens({"pad_token": "[PAD]"})
model = AutoModelForCausalLM.from_pretrained(...)
if added:
    model.resize_token_embeddings(len(tokenizer))
model.config.pad_token_id = tokenizer.pad_token_id
model.generation_config.pad_token_id = tokenizer.pad_token_id
```

> **以前の実装から変更**: `pad_token = unk_token` という設定は使わなくなりました。Phi-4-mini は既に `pad_token_id`、`unk_token_id`、`eos_token_id` がすべて `<|endoftext|>` に設定されており、`unk_token` を `pad_token` に流用すると EOS と同一 ID になり、モデルが「パディング = 終了」を学習してしまう問題がありました。

## Completion-only loss（重要）

`prepare_data.py` は **TRL の prompt/completion 対** で JSONL を出力するため、`SFTTrainer` は自動的に **completion-only loss** を有効にします。つまり損失計算は **assistant 応答トークン** に対してのみ実施され、system prompt や user instruction には損失がかかりません。

**制限**: Prompt トークンに `-100` ラベルを付けることで入力への損失は計算されませんが、これはモデルがプロンプトを記憶することを**防ぐわけではありません**。少量データや多数 epoch では訓練データの memorization が起こる可能性があります。`eval_loss` を継続的にモニタリングし、上昇が始まったら `EarlyStoppingCallback` が自動停止します。

参考: [TRL SFTTrainer — completion-only loss](https://huggingface.co/docs/trl/main/en/sft_trainer#train-on-completions-only)

## なぜ QLoRA (4-bit) を使うのか

**フルファインチューニング**: Phi-4-mini 3.8B → fp32 で 15 GB、fp16 で 8 GB + optimizer states → **A100 80GB が必須**

**QLoRA 4-bit**: モデル本体 ~2 GB + LoRA + gradients → **T4 16GB で余裕**

QLoRA の計算グラフでは実行時に de-quantize されるため、精度低下は参考値 1-2% 以内（[Dettmers et al., 2023](https://arxiv.org/abs/2305.14314)）。

## LoRA ターゲットモジュール

### Phi-4-mini の場合

`target_modules="all-linear"` を使うと `peft` が全 `nn.Linear` に自動挿入します（peft ≥ 0.14）。

Phi-4-mini での主要ターゲットは:
- `qkv_proj`, `o_proj` (Attention)
- `gate_up_proj`, `down_proj` (FFN / MLP)

> **注意**: `q_proj`/`k_proj`/`v_proj` の分離名は Qwen スタイルです。Phi-4-mini では `qkv_proj` として統合されています。`all-linear` は両方のモデルで自動検出するため、ハードコードは不要です。

訓練開始時にログで確認できます:
```
[lora] trainable modules (48): ['model.layers.0.self_attn.qkv_proj.lora_A.default.weight', ...]
```

### Qwen2.5 の場合

`all-linear` が自動で `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` を検出します。

`r=16, alpha=32` は出発点としての**参考値**です。タスクとデータ量によって調整してください（少量データ: r=8、大規模適応: r=32〜64）。

参考: [peft.LoraConfig — target_modules](https://huggingface.co/docs/peft/main/en/package_reference/lora#peft.LoraConfig.target_modules)

## なぜ `fp16=True, bf16=False` か

T4 GPU (Turing アーキ、compute capability 7.5) は **bfloat16 を hardware 対応していません**。`bf16=True` を指定すると数値エラーが発生します。**T4 では常に fp16 を使う** ことが正解です。A100/A10/L40 (Ampere+) では bf16 が使えます。

## 学習率スケジューラ (cosine + warmup)

```
lr(step) = 0 → 2e-4 (最初の warmup_ratio % ステップで線形上昇)
        → 2e-4 → 0 (残りで cosine 減衰)
```

既定の `warmup_ratio=0.03` (3%) は LoRA アダプタの初期爆発を防ぐ定番設定です。

## 学習ログの読み方

```
{'loss': 1.842, 'grad_norm': 1.98, 'learning_rate': 0.00019, 'epoch': 0.2}
{'eval_loss': 1.35, 'eval_runtime': 12.3, 'epoch': 1.0}
```

- **loss**: 訓練 batch の cross-entropy。**参考値**: 開始 2.0〜2.5、終了 1.0〜1.3 が健全
- **eval_loss**: 検証データへの loss。`load_best_model_at_end=True` で最小 epoch の重みを使用
- **grad_norm**: 勾配ノルム。5.0 未満で安定、10.0 超えは要注意
- **learning_rate**: 現在の LR（cosine で減衰）

詳細な結果解釈は [05-understand-results.md](05-understand-results.md) を参照。

## アダプタのマージ（オプション）

LoRA アダプタをベースモデルに統合して単体モデルとして保存する場合:

```bash
python src/merge_adapter.py \
    --adapter data/adapter/final \
    --output data/merged_model/ \
    --model-revision cfbefacb99257ffa30c83adab238a50856ac3083
```

> **注意**: 量子化 (4-bit) ロードしたモデルはマージ不可です。`merge_adapter.py` は fp16 ロードを強制します。マージ後の配布前にライセンス確認を行ってください（[07-ethics-and-limits.md](07-ethics-and-limits.md) 参照）。
