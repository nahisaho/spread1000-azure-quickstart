# 07: 倫理と限界

本クイックスタートで学べる LoRA ファインチューニングは、非常に強力な技術ですが、そのまま研究成果や実プロダクトに使うには以下の制約を必ず理解してください。

## データセットのライセンス

| データセット | ライセンス | 商用利用 | ShareAlike |
|---|---|---|---|
| `kunishou/databricks-dolly-15k-ja` | **CC BY-SA 3.0** | ✅ 可 | ⚠️ **要（派生物も CC BY-SA）** |
| `elyza/ELYZA-tasks-100` | ELYZA custom | ⚠️ 評価のみ | — |
| `ichikara-instruction` | **CC-BY-NC-SA** | ❌ 非商用のみ | ⚠️ 要 |
| JGLUE 各サブセット | 個別 (概ね CC BY-SA 4.0) | ✅ 可 | ⚠️ 要 |

**dolly-ja (CC BY-SA 3.0) で LoRA したモデルを公開する場合**:
- 派生モデル (LoRA アダプタ) も **CC BY-SA 3.0 以上互換** で公開する必要
- 商用可、ただし ShareAlike 条件遵守
- 商標や個人情報を含む場合は別途配慮

**プロプライエタリな研究データで LoRA する場合**:
- 学内・組織内のデータ利用規約を確認
- 患者データ、個人特定可能情報 (PII) は必ずマスク or 除外
- GDPR、個人情報保護法、医療研究倫理指針 (医学研究に該当する場合) の適用範囲

## モデルのライセンスと配布

| モデル | ライセンス | 商用利用 | 派生モデル配布 |
|---|---|---|---|
| `microsoft/Phi-4-mini-instruct` | **MIT** | ✅ 可 | ✅ 可 |
| `Qwen/Qwen2.5-0.5B-Instruct` | **Apache 2.0** | ✅ 可 | ✅ 可 |
| `meta-llama/Llama-3.*` | Meta Community License | ⚠️ 条件付き | ⚠️ 条件付き |
| `mistralai/Mistral-Large-*` | Mistral Research License / Commercial | ⚠️ 条件付き | ⚠️ 条件付き |

**Phi-4-mini + dolly-ja LoRA の組み合わせは**:
- モデル本体: MIT (最も緩い)
- データ由来: CC BY-SA 3.0 → **派生 LoRA は CC BY-SA 3.0 で公開する** のが安全
- 論文・成果物の謝辞 (Attribution) に元データセット・モデルを明示

## LoRA の技術的な限界

### 1. **知識のインジェクションには不向き**

LoRA は主にスタイル・応答形式を変化させます。**新しい事実知識** (例: 最新論文の内容) を LoRA で覚えさせるのは非効率で、RAG (Retrieval-Augmented Generation) の方が適しています。

- 新しい事実を教えたい → RAG (ベクトル検索 + LLM)
- 応答スタイル・専門用語の使い方を変えたい → LoRA

### 2. **少量データでは過学習しやすい**

50〜100 件の LoRA では **1〜2 epoch で止める** ことが重要。3 epoch 以上は簡単に過学習し、ベースモデルの汎用性を失います。

### 3. **量子化 (4-bit QLoRA) の精度低下**

QLoRA では模型本体を 4-bit に丸めるため、fp16 LoRA より 1〜2% 程度の性能低下があります (Guanaco 論文 [Dettmers et al., 2023](https://arxiv.org/abs/2305.14314))。実用上は問題ないケースが多いですが、ベンチマークで最後の 1% を追求する場面では fp16 LoRA (A10/A100 が必要) を検討してください。

### 4. **チャットテンプレートのミスマッチ**

Phi-4-mini と Qwen2.5 では chat template が異なります (`<|user|>` vs `<|im_start|>user`)。`train_lora.py` は `apply_chat_template` を経由するので自動整合しますが、**推論時は必ずベースモデルと同じ tokenizer** を使ってください。

### 5. **日本語トークン効率**

Phi-4-mini の tokenizer は 200K vocab で日本語効率が良いですが、Qwen2.5 (152K) より若干 subword が細かい傾向があります。max_seq_length を短く設定するときは日本語で切れる可能性を考慮。

## 責任ある使用

1. **バイアスの検証**: 学習データの偏り (性別、職業、地域など) が LoRA モデルに反映される可能性。公開前に代表的なプロンプトで応答を確認
2. **hallucination の警告**: どんな LoRA モデルも事実誤認する可能性がある。応用ドメインでは必ず一次資料で確認するワークフローを併用
3. **セーフティ**: 医療診断、法律アドバイス、金融助言などのクリティカル用途では、**LoRA モデルを直接ユーザに露出しない**。人間の専門家によるレビューを挟む
4. **証拠追跡**: LoRA 学習時のデータ、seed、ハイパラは `metrics.json` で保存されるが、**論文用に別途 config スナップショットを保管** することを推奨

## 参考文献

- **Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models"** (ICLR 2022) — [arxiv.org/abs/2106.09685](https://arxiv.org/abs/2106.09685)
- **Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs"** (NeurIPS 2023) — [arxiv.org/abs/2305.14314](https://arxiv.org/abs/2305.14314)
- **Microsoft, "Phi-4-mini: Small Language Models for the New Era of AI"** — [huggingface.co/microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct)
- **Qwen Team, "Qwen2.5 Technical Report"** — [arxiv.org/abs/2412.15115](https://arxiv.org/abs/2412.15115)
- **HuggingFace TRL PEFT integration** — [huggingface.co/docs/trl/main/en/lora_tuning_peft](https://huggingface.co/docs/trl/main/en/lora_tuning_peft)

### BibTeX

```bibtex
@inproceedings{hu2022lora,
  title={{LoRA}: Low-Rank Adaptation of Large Language Models},
  author={Hu, Edward J. and Shen, Yelong and Wallis, Phillip and Allen-Zhu, Zeyuan and Li, Yuanzhi and Wang, Shean and Wang, Lu and Chen, Weizhu},
  booktitle={International Conference on Learning Representations},
  year={2022},
  url={https://openreview.net/forum?id=nZeVKeeFYf9}
}
@inproceedings{dettmers2023qlora,
  title={{QLoRA}: Efficient Finetuning of Quantized {LLMs}},
  author={Dettmers, Tim and Pagnoni, Artidoro and Holtzman, Ari and Zettlemoyer, Luke},
  booktitle={Advances in Neural Information Processing Systems},
  year={2023}
}
```
