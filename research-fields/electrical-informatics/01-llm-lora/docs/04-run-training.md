# 04: 訓練実行 — ハイパーパラメータの意味

## `src/train_lora.py` の CLI オプション

```
python src/train_lora.py [OPTIONS]
```

| オプション | 既定値 | 意味・調整のヒント |
|---|---|---|
| `--model` | `microsoft/Phi-4-mini-instruct` | ベースモデルの HF ID。CPU では `Qwen/Qwen2.5-0.5B-Instruct` |
| `--data` | `data/train.jsonl` | `prepare_data.py` で生成した chat JSONL |
| `--output` | `data/adapter/` | 保存先ディレクトリ（`adapter_config.json` + `adapter_model.safetensors`） |
| `--epochs` | `3` | 学習エポック数。1000 件データで 3 epoch が経験的ベストバランス |
| `--batch-size` | `2` | GPU 当たりのバッチサイズ。T4 16GB QLoRA では 2 が上限 |
| `--grad-accum` | `4` | 勾配累積ステップ数。実効バッチ = `batch-size * grad-accum` |
| `--lr` | `2e-4` | Adam 学習率。LoRA では `1e-4〜5e-4` の範囲が定番 |
| `--max-seq-length` | `512` | トークン列の最大長。長くすると VRAM 消費増大 |
| `--lora-r` | `16` | LoRA ランク。8, 16, 32 が定番。大きいと表現力↑・パラメータ数↑ |
| `--lora-alpha` | `32` | LoRA scaling factor。`alpha = 2 * r` が経験的定番 |
| `--lora-dropout` | `0.05` | LoRA 層の dropout。過学習抑制 |
| `--device` | `auto` | `auto` (CUDA→CPU fallback) / `cuda` / `cpu` |
| `--no-quant` | `False` | 4-bit 量子化を無効化。CPU では必須 |
| `--seed` | `42` | 乱数シード |

## 学習プロセスの流れ

```
1. Tokenizer 読み込み (pad_token = unk_token に設定、eos_token は避ける)
2. モデル読み込み
   - GPU + QLoRA: BitsAndBytesConfig で 4-bit NF4 量子化
   - GPU + LoRA:  fp16 でロード
   - CPU:         fp32 でロード
3. JSONL データ読み込み → HuggingFace Dataset に変換
4. LoRA 設定 (r, alpha, dropout, target_modules="all-linear")
5. SFTConfig 設定 (epochs, batch, lr, fp16, cosine scheduler, warmup 3%)
6. SFTTrainer で訓練ループ実行
   → 各 batch: prompt に chat_template 適用 → tokenize → completion のみを損失計算対象に → forward → cross-entropy → backward
7. Best-effort save: outputs/final/ に adapter を保存、metrics.json を出力
```

## Completion-only loss（重要）

`prepare_data.py` は **TRL の prompt/completion 対** で JSONL を出力するため、`SFTTrainer` は自動的に **completion-only loss** を有効にします。つまり損失計算は **assistant 応答トークン** に対してのみ実施され、system prompt や user instruction（既に既知のもの）には損失がかかりません。

これにより:
- モデルは「入力を暗記する」浪費を避け、応答生成能力の学習にリソースを集中
- 推論時のプロンプト形式と学習時が完全一致し、テスト時ミスマッチを回避
- 少量データ (100〜1000 件) でも過学習を抑制

参考: [TRL SFTTrainer — completion-only loss](https://huggingface.co/docs/trl/main/en/sft_trainer#train-on-completions-only)

## なぜ QLoRA (4-bit) を使うのか

**フルファインチューニング** (全パラメータ更新):
- Phi-4-mini 3.8B → fp32 で 15 GB, fp16 で 8 GB のモデル本体だけで T4 16GB を占有
- Adam optimizer states でさらに 2 倍必要 → **A100 80GB クラスが必須**

**LoRA fp16** (LoRA アダプタのみ更新、モデル本体は fp16):
- モデル本体 8 GB + LoRA 学習可能 ~0.5% + gradients + activations → T4 16GB でギリギリ or OOM

**QLoRA 4-bit** (モデル本体を 4-bit 量子化、LoRA だけ fp16):
- モデル本体 ~2 GB + LoRA + gradients + activations → **T4 16GB で 30-40% 余裕**
- QLoRA の計算グラフでは実行時に de-quantize されるため、精度低下は 1-2% 以内（Guanaco 論文 [Dettmers et al., 2023](https://arxiv.org/abs/2305.14314)）

## なぜ `target_modules="all-linear"` か

Phi-4-mini と Qwen2.5 では self-attention の内部モジュール名が異なります:

- Phi-4-mini: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- Qwen2.5: 同じだが、モデル階層の名前が異なる

`target_modules="all-linear"` は `peft` が **すべての `nn.Linear` レイヤ** に自動的に LoRA を挿入する指定で、モデル毎の名前ハードコードを不要にします（peft ≥ 0.14 の機能）。

参考: [peft.LoraConfig — target_modules](https://huggingface.co/docs/peft/main/en/package_reference/lora#peft.LoraConfig.target_modules)

## なぜ `fp16=True, bf16=False` か

T4 GPU (Turing アーキ、compute capability 7.5) は **bfloat16 を hardware 対応していません**。`bf16=True` を指定すると:
- 最新のドライバでは実行時エラー
- 古いドライバでは silent numerical error (数値が壊れて loss が NaN になる)

**T4 では常に fp16 を使う** ことが正解です。A100/A10/L40 (Ampere+) では bf16 が使えます（安定領域が広いので推奨）。

## 学習率スケジューラ (cosine + warmup 3%)

```
lr(step) = 0 → 2e-4 (最初の 3% ステップで線形に上昇, warmup)
        → 2e-4 → 0 (残り 97% で cosine 減衰)
```

Warmup は LoRA アダプタの初期爆発を防ぎ、cosine 減衰は最後に細かく収束させます。定番の組み合わせで、`trl` の SFTTrainer でも推奨されています。

## 学習ログの読み方

```
{'loss': 1.842, 'grad_norm': 1.98, 'learning_rate': 0.00019, 'epoch': 0.2}
```

- **loss**: cross-entropy on assistant tokens. 開始 2.0〜2.5、終了 1.0〜1.3 が健全な学習曲線
- **grad_norm**: 勾配のノルム。5.0 未満で安定、10.0 超えは要注意
- **learning_rate**: 現在の LR（cosine で減衰していく）
- **epoch**: 現在の epoch 進捗（小数）

詳細な結果解釈は [05-understand-results.md](05-understand-results.md) を参照。
