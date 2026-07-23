# Phi-4-mini LoRA ファインチューニング クイックスタート

Microsoft の小型言語モデル **Phi-4-mini-instruct** (3.8B, MIT ライセンス) を、日本語の instruction データ **databricks-dolly-15k-ja** (CC BY-SA 3.0) に **QLoRA 4-bit** で適応させる 30〜60 分のクイックスタートです。SPReAD-1000 の LLM 関連課題 (推論高速化、パーソナライズ、教材生成、対話モデル評価など) の出発点として使えます。

> 主経路は **Azure ML の T4 GPU** です (~$0.50、45 分)。GPU クォータ申請中の間は、**ローカル CPU + Qwen2.5-0.5B のスモークテスト** で同じパイプラインを検証できます (~10〜15 分、$0)。

## 何ができるようになるか

- **LoRA アダプタ**（数十 MB）だけ学習して、モデル本体（数 GB）は凍結する現代的なファインチューニング手法を理解
- ドメイン特化データ（例: 研究論文要約、学術用語の説明、実験プロトコル）を数百〜数千サンプル用意すれば、同じスクリプトで自分のタスクに適用可能
- ベース Phi-4-mini と LoRA 適応後の応答を **並べて比較** し、ファインチューニングの効果を定量・定性的に確認
- 学習済み LoRA アダプタを **HuggingFace Hub** や **Azure ML Model Registry** に登録し、`AutoModelForCausalLM` + `PeftModel.from_pretrained()` の 2 行で再利用可能に

## クイックスタート

**GPU クォータがすでにある場合** (Azure ML T4 パス、推奨):

```bash
# 1. 環境構築 (Python 3.12, Azure ML compute or 手元の cu126 GPU)
python -m venv .venv && source .venv/bin/activate
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements-gpu.txt

# 2. データ準備
python src/prepare_data.py --n 1000 --output data/train.jsonl

# 3. QLoRA 訓練 (T4 で 30〜45 分)
python src/train_lora.py --data data/train.jsonl --output data/adapter/

# 4. ベース vs LoRA 応答比較
python src/compare.py --adapter data/adapter/final --prompts data/eval_prompts.json
```

**CPU スモークテスト（GPU 待機中に動作検証、$0）**:

```bash
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-cpu.txt
python src/prepare_data.py --n 100 --output data/train.jsonl
python src/train_lora.py --model Qwen/Qwen2.5-0.5B-Instruct --data data/train.jsonl \
    --epochs 1 --device cpu --no-quant --output data/adapter/
```

詳細は [`docs/`](docs/) を順に参照してください:

1. [prerequisites (前提条件・環境準備)](docs/01-prerequisites.md)
2. [CPU スモークテスト](docs/02-cpu-smoketest.md)
3. [Azure ML T4 GPU での本番訓練](docs/03-aml-gpu.md)
4. [訓練実行 (ハイパラの意味)](docs/04-run-training.md)
5. [結果の見方 (loss、応答比較、性能評価)](docs/05-understand-results.md)
6. [クリーンアップ (課金停止)](docs/06-cleanup.md)
7. [倫理と限界 (LoRA の適用範囲・データライセンス)](docs/07-ethics-and-limits.md)

## 想定コスト・時間

| 実行環境 | 時間 | コスト |
|---|---|---|
| ローカル CPU (`Qwen2.5-0.5B`, 100 サンプル, 1 epoch, スモークテスト) | 10〜15 分 | $0 |
| Azure ML `Standard_NC4as_T4_v3` (`Phi-4-mini`, 1000 サンプル, 3 epoch, QLoRA) | 30〜45 分 | ~$0.40 (¥62)〜 |
| ローカル cu126 GPU (RTX 30xx/40xx 16GB+) | 15〜30 分 | $0 |

## SPReAD-1000 の適用可能な研究課題（例）

- **LLM 推論高速化・分散**: Phi-4-mini + LoRA で軽量な派生モデルを試作し、投機的デコーディングやドラフター評価の基盤に
- **パーソナライズド LLM**: 個人発話ログ・研究ノートで LoRA 適応
- **教材自動生成**: 教科書サンプル + Q&A ペアで教育ドメイン特化 LoRA
- **意味推論・思考連鎖評価**: Reasoning task データセットで JP 推論能力を測定
- **LLM 対話エージェント**: 対話履歴データで人格・スタイル特化 LoRA
- **LLM 安全性・敵対的検出**: 攻撃/防御プロンプトペアで検出モデルを訓練

## 主要技術スタック

- **Python 3.12**
- **PyTorch 2.7.1** (cu126 GPU / CPU)
- **transformers 5.14.1** — Phi-4-mini / Qwen2.5 モデル読み込み
- **peft 0.19.1** — LoRA アダプタ設定・保存・読み込み
- **trl 1.9.0** — `SFTTrainer` (Supervised Fine-Tuning)
- **bitsandbytes 0.49.2** — QLoRA 4-bit 量子化 (GPU のみ)
- **accelerate 1.14.0** — `device_map="auto"`, 混合精度
- **datasets 5.0.0** — HuggingFace データセット
