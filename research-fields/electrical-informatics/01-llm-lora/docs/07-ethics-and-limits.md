# 07: 倫理と限界

本クイックスタートで学べる LoRA ファインチューニングは、非常に強力な技術ですが、そのまま研究成果や実プロダクトに使うには以下の制約を必ず理解してください。

## データプロバナンスと個人情報 (PII) への対応

### カスタムデータを使う場合の必須手続き

独自データで `prepare_data.py` を実行する場合、**データプロバナンス・サイドカー** (`<data>.provenance.json`) の作成が必須です:

```json
{
  "source": "データの出所 (例: 研究室内アンケート、Webクロール、社内文書)",
  "license": "CC BY-SA 4.0 / 独自ライセンス / 非公開",
  "purpose": "データ利用目的（例: 日本語医療Q&Aモデルの微調整）",
  "lawful_basis": "適法な根拠（例: 研究倫理委員会承認 #2026-xxx、CC BY-SA 4.0 ライセンス条件）",
  "contains_user_text": false,
  "pii_reviewed": true,
  "content_safety_reviewed": true
}
```

このサイドカーは:
- **個人情報保護法 (APPI)** 対応: 個人データの第三者提供・委託の記録として機能
- **GDPR Article 5(1)(b)** 対応: 目的の特定と記録
- 機関倫理審査の提出物として使用可能

> ⚠️ `contains_user_text: true` の場合: PII 除去・匿名化が完了していることを確認してください。患者データ、氏名・住所・連絡先・識別番号を含むデータは、医療研究倫理指針（厚生労働省）または機関 IRB の承認が必要です。

### ビルトインデータセット

`--builtin-dataset dolly-ja` を使う場合はプロバナンスが自動設定されます:

```bash
python src/prepare_data.py \
    --builtin-dataset dolly-ja \
    --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb
```

## データセットのライセンス

| データセット | ライセンス | 商用利用 | ShareAlike |
|---|---|---|---|
| `kunishou/databricks-dolly-15k-ja` | **CC BY-SA 3.0** | ✅ 可 | ⚠️ **要（派生物も CC BY-SA）** |
| `elyza/ELYZA-tasks-100` | **CC BY-SA 4.0** | ✅ 可 | ⚠️ 要（CC BY-SA 4.0） |
| `ichikara-instruction` | **CC-BY-NC-SA** | ❌ 非商用のみ | ⚠️ 要 |
| JGLUE 各サブセット | 個別（MARC-ja は商用利用に注意）| 要確認 | 要確認 |

> **訂正**: ELYZA-tasks-100 のライセンスは **CC BY-SA 4.0**（3.0 ではありません）。JGLUE サブセットのうち MARC-ja は元データの商用利用制限を引き継ぐ場合があります。各サブセットのライセンスを個別に確認してください。

> **JMultiPPDB**: 利用規約が明確に確認できていないため、本クイックスタートでは推奨しません。使用前に必ずライセンスを確認してください。

### databricks-dolly-15k-ja の引用

- 原文 (英語): [databricks/databricks-dolly-15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) — Databricks, Inc. (CC BY-SA 3.0)
- 日本語翻訳版: [kunishou/databricks-dolly-15k-ja](https://huggingface.co/datasets/kunishou/databricks-dolly-15k-ja) — kunishou (CC BY-SA 3.0)

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
| `meta-llama/Llama-3.*` | Meta Llama 3 Community License | ⚠️ バージョン・用途により条件が異なる | ⚠️ 条件付き |
| `mistralai/Mistral-Large-*` | Mistral Research License / Commercial | ⚠️ モデル・バージョンにより異なる | ⚠️ 条件付き |
| `google/gemma-*` | Gemma Terms of Use | ⚠️ バージョンにより条件が異なる | ⚠️ 条件付き |

> **重要**: Llama、Mistral、Gemma などのモデルライセンスはバージョンやリポジトリごとに条件が大きく異なります。利用前に必ず当該モデルの HuggingFace Hub ページで最新ライセンスを確認し、条件を理解した上で `--model-license` と `--accept-model-license` フラグを使用してください。

**LoRA 学習済みモデル (アダプタ) の重みの法的地位**:
> ⚠️ 学習済み LoRA アダプタが「ベースモデルの派生物」に当たるかどうかは、現時点で法的に確立されていません。再配布前に、所属機関の法務・知財部門による確認を強く推奨します。

**Phi-4-mini + dolly-ja LoRA の組み合わせは**:
- モデル本体: MIT (最も緩い)
- データ由来: CC BY-SA 3.0 → **派生 LoRA は CC BY-SA 3.0 で公開するのが安全**
- 論文・成果物の謝辞 (Attribution) に元データセット・モデルを明示

### モデルライセンス確認の仕組み

`train_lora.py` は起動時にモデル ID をチェックします:
- **事前承認済み** (`Phi-4-mini`, `Qwen2.5-0.5B`): 自動承認
- **それ以外**: `--model-license <SPDX>` + `--accept-model-license` の両方が必要

```bash
python src/train_lora.py \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --model-revision <SHA> \
  --dataset-revision <SHA> \
  --model-license "Meta-Llama-3" \
  --accept-model-license \
  ...
```

## LoRA の技術的な限界

### 1. **知識のインジェクションには不向き**

LoRA は主にスタイル・応答形式を変化させます。**新しい事実知識** (例: 最新論文の内容) を LoRA で覚えさせるのは非効率で、RAG (Retrieval-Augmented Generation) の方が適しています。

- 新しい事実を教えたい → RAG (ベクトル検索 + LLM)
- 応答スタイル・専門用語の使い方を変えたい → LoRA

### 2. **少量データでは過学習しやすい**

50〜100 件の LoRA では **1〜2 epoch で止める** ことが重要。3 epoch 以上は簡単に過学習し、ベースモデルの汎用性を失います。`EarlyStoppingCallback` が自動的に `eval_loss` の上昇を検知して停止します。

### 3. **量子化 (4-bit QLoRA) の精度低下**

QLoRA では模型本体を 4-bit に丸めるため、fp16 LoRA より **参考値** 1〜2% 程度の性能低下があります ([Dettmers et al., 2023](https://arxiv.org/abs/2305.14314))。実用上は問題ないケースが多いですが、ベンチマークで最後の 1% を追求する場面では fp16 LoRA (A10/A100 が必要) を検討してください。

### 4. **チャットテンプレートのミスマッチ**

Phi-4-mini と Qwen2.5 では chat template が異なります (`<|user|>` vs `<|im_start|>user`)。`train_lora.py` は `apply_chat_template` を経由するので自動整合しますが、**推論時は必ずベースモデルと同じ tokenizer** を使ってください。

### 5. **日本語トークン効率**

Phi-4-mini の tokenizer は 200K vocab で日本語効率が良いですが、Qwen2.5 (152K) より若干 subword が細かい傾向があります。max_seq_length を短く設定するときは日本語で切れる可能性を考慮。

### 6. **Completion-only loss の制限**

Prompt tokens に `-100` ラベルを付けることで、損失はアシスタント応答トークンのみで計算されます。これは効率的ですが、**モデルがプロンプトを記憶することを防ぐわけではありません**。少量データや繰り返し epoch では訓練データの過学習 (memorization) が起こる可能性があります。検証データの `eval_loss` を継続的にモニタリングしてください。

## 責任ある使用

1. **バイアスの検証**: 学習データの偏り (性別、職業、地域など) が LoRA モデルに反映される可能性。公開前に代表的なプロンプトで応答を確認
2. **hallucination の警告**: どんな LoRA モデルも事実誤認する可能性がある。応用ドメインでは必ず一次資料で確認するワークフローを併用
3. **セーフティ**: 医療診断、法律アドバイス、金融助言などのクリティカル用途では、**LoRA モデルを直接ユーザに露出しない**。人間の専門家によるレビューを挟む
4. **証拠追跡**: LoRA 学習時のデータ、seed、ハイパラは `manifest.json` で保存される。**論文用に別途 config スナップショットを保管** することを推奨
5. **機関・倫理審査**: 人間を対象とする研究 (ユーザ発話データ、医療 Q&A 等) でモデルを学習・展開する場合は機関倫理審査委員会 (IRB/倫理委員会) の事前承認を取得してください

## 参考文献

- **Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models"** (ICLR 2022) — [arxiv.org/abs/2106.09685](https://arxiv.org/abs/2106.09685)
- **Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs"** (NeurIPS 2023) — [arxiv.org/abs/2305.14314](https://arxiv.org/abs/2305.14314)
- **Microsoft, "Phi-4-mini"** — [huggingface.co/microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct)
- **Qwen Team, "Qwen2.5 Technical Report"** — [arxiv.org/abs/2412.15115](https://arxiv.org/abs/2412.15115)
- **HuggingFace TRL PEFT integration** — [huggingface.co/docs/trl/main/en/lora_tuning_peft](https://huggingface.co/docs/trl/main/en/lora_tuning_peft)
- **databricks/databricks-dolly-15k** (Databricks, CC BY-SA 3.0) — [huggingface.co/datasets/databricks/databricks-dolly-15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k)
- **kunishou/databricks-dolly-15k-ja** (kunishou, CC BY-SA 3.0) — [huggingface.co/datasets/kunishou/databricks-dolly-15k-ja](https://huggingface.co/datasets/kunishou/databricks-dolly-15k-ja)

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
