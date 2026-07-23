# 05: 結果の見方

## 訓練終了時に確認するファイル

```
data/adapter/
├── final/
│   ├── adapter_config.json       # LoRA 設定 (r, alpha, target_modules)
│   ├── adapter_model.safetensors # LoRA 重み (~30-100 MB)
│   ├── tokenizer.json
│   ├── tokenizer_config.json
│   └── special_tokens_map.json
├── checkpoint-<step>/            # epoch ごとの中間チェックポイント
└── metrics.json                  # 訓練終了時の指標サマリ
```

### `metrics.json` の内容

```json
{
  "train_runtime_sec": 2340.5,
  "train_samples_per_second": 1.28,
  "train_loss": 1.31,
  "epochs": 3,
  "n_train_samples": 1000,
  "model": "microsoft/Phi-4-mini-instruct",
  "device": "cuda",
  "quantized_4bit": true,
  "lora_r": 16,
  "lora_alpha": 32
}
```

## 損失曲線の解釈

### 期待される軌跡（Phi-4-mini + dolly-ja 1000 サンプル + 3 epoch）

| epoch | 期待 train_loss | 意味 |
|---:|---:|---|
| 0.2 (early) | ~1.8〜2.2 | ベースモデルの初期損失 |
| 1.0 | ~1.4〜1.6 | LoRA が dolly-ja のスタイルを学習中 |
| 2.0 | ~1.2〜1.4 | 主要パターンが安定 |
| 3.0 (end) | ~1.0〜1.3 | 収束、`train_loss < 1.0` は過学習の可能性 |

**赤信号**:
- ❌ `train_loss` が上昇 → LR が高すぎる、`--lr 1e-4` に下げる
- ❌ `grad_norm > 10` が続く → gradient explosion。`--lr` を下げるか `--max-seq-length` を短く
- ❌ `train_loss` が NaN → fp16 の underflow / bf16 誤指定。`fp16=True, bf16=False` を確認

## `compare.py` の出力を読む

`src/compare.py` は各プロンプトについてベースモデルと LoRA モデルの応答を並置します:

```
======================================================================
[3/10] Python でリスト内包表記が普通の for 文よりも速い理由を教えてください。
======================================================================

--- Base (microsoft/Phi-4-mini-instruct) ---
リスト内包表記は Python の C レベルで最適化されており、
バイトコード レベルで LIST_APPEND opcode が使われるため速いです。
一方、明示的な for ループは append メソッドの呼び出しごとに関数
呼び出しのオーバーヘッドが発生します。

--- LoRA-adapted ---
Python のリスト内包表記が for 文よりも高速な理由は主に 3 点あります。
1. バイトコード最適化: LIST_APPEND という専用の opcode を使う
2. 属性アクセスの省略: list.append を毎回ルックアップしなくてよい
3. 内部ループの C 実装: for 文よりも interpreter overhead が少ない
これらにより、通常 20〜40% 高速です。
```

### 何を評価するか

| 観点 | 判断基準 |
|---|---|
| **回答の網羅性** | LoRA 版がベース版より箇条書きや構造化された応答をするか |
| **日本語の自然さ** | dolly-ja の文体（丁寧語、体系的）を学習しているか |
| **回答の長さ** | 短すぎる (< 50 文字) / 長すぎる (> 500 文字) 傾向はないか |
| **無限生成** | 途中で切れず、EOS で自然に終了しているか (padding = eos 問題) |
| **反復・幻覚** | 同じフレーズの反復や、事実誤認が増えていないか |

### LoRA が「効いた」判断

- **良い症状**: 応答が dolly-ja 的な体系構造（箇条書き、番号付け、明示的な結論）に変わる
- **微妙な症状**: ベースとほぼ同じ → データ量不足、あるいは `--epochs` を増やす
- **悪い症状**: 明らかに劣化（文法崩壊、日本語→英語混在の増加）→ 過学習または LR 過大

## 定量評価 (発展)

`compare.py` の出力を `data/comparison.json` に保存しているので、以下の方法で定量評価できます:

### 方法 A: 人手評価（最も信頼できる）

- 5-point Likert scale で 10 プロンプト × 2 応答を評価
- 相対比較 (どちらの応答が良いか) で A/B テスト形式

### 方法 B: LLM-as-Judge

```python
# GPT-4o を審査員に、A(base) と B(lora) のどちらが良いかを判定
import openai
client = openai.AzureOpenAI(...)  # Azure OpenAI エンドポイント

for row in comparison_data:
    prompt = f"""以下の 2 つの応答を評価してください:
Q: {row['prompt']}
A: {row['base']}
B: {row['lora']}
A と B のどちらが優れているか、理由と共に JSON で回答: {{"winner": "A"|"B"|"tie", "reason": "..."}}
"""
    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
```

### 方法 C: 標準ベンチマーク

- [ELYZA-tasks-100](https://huggingface.co/datasets/elyza/ELYZA-tasks-100) — 100 の多様な日本語タスク
- [JGLUE](https://github.com/yahoojapan/JGLUE) — Japanese GLUE benchmark

これらは本クイックスタート範囲外ですが、LoRA の効果を測る次のステップとして推奨されます。

## 想定される結果（Phi-4-mini + dolly-ja 1000 サンプル + 3 epoch, T4）

- **train_loss** 開始 ~2.0 → 終了 ~1.2
- **train_runtime**: 35〜45 分
- **LoRA adapter サイズ**: ~50 MB (Phi-4-mini の場合)
- **応答比較**: dolly-ja 特有の丁寧語 + 構造化スタイルへの明確な変化を確認可能
