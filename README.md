# SPReAD-1000 Azure クイックスタート

文部科学省 **SPReAD-1000**（第1回公募・令和8年度採択）に選ばれた研究代表者向けに、**Azure で AI for Science 環境を最速でデプロイする**ためのクイックスタート集です。

- 対象読者: 大学・研究機関の研究者本人（**AI for Science 未経験・Azure 未経験を前提**）
- 目的: コピペで動かせる。動作確認後は**必ず課金を止められる**構成にする。

## 構成

研究分野（SPReAD-1000 公募要領の 10 分野）ごとにクイックスタートを整理しています。ディレクトリ名は英語スラッグ、README 冒頭に日本語分野名を明記します。

```
research-fields/
  life-pharma-science/   # 生命科学・薬学 (98 課題)
  clinical-science/      # 臨床科学 (70 課題)
  ...
```

## 分野別クイックスタート一覧

### 🧬 [生命科学・薬学](research-fields/life-pharma-science/)（採択 98 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [TamGen 分子生成](research-fields/life-pharma-science/01-molecular-generation-tamgen/) | Target-aware drug design | T4 |
| 02 | [ESMFold タンパク質構造予測](research-fields/life-pharma-science/02-protein-structure-esmfold/) | Single-sequence protein folding | A100 |
| 03 | [AlphaFold 3 構造予測](research-fields/life-pharma-science/03-protein-structure-alphafold3/) | Multimer / ligand complex | A100 |
| 04 | [RNA-Seq (nf-core)](research-fields/life-pharma-science/04-transcriptomics-rnaseq/) | Bulk transcriptomics | Azure Batch |
| 05 | [BioEmu タンパク質アンサンブル](research-fields/life-pharma-science/05-conformational-ensemble-bioemu/) | Conformational ensemble sampling | A100 |

### 🩺 [臨床科学](research-fields/clinical-science/)（採択 70 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [MONAI 3D セグメンテーション](research-fields/clinical-science/01-medical-imaging-monai/) | 医用画像 (spleen CT) | T4 / A100 |
| 02 | [電子カルテ NLP (RAG)](research-fields/clinical-science/02-ehr-nlp-rag/) | 合成 SOAP ノート × Azure OpenAI + AI Search (**合成データ専用**) | — (LLM API) |
| 03 | [生体信号 (ECG) 分類](research-fields/clinical-science/03-biosignal-ecg-classification/) | MIT-BIH × 1D CNN AAMI 5-class (AML v2) | T4 (CPU fallback 可) |

### ⚗️ [化学](research-fields/chemistry/)（採択 22 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [REINVENT4 分子生成](research-fields/chemistry/01-molecular-generation-reinvent4/) | LibInvent scaffold decoration (AML v2) | — (CPU) |
| 02 | [ReactionT5v2 反応予測](research-fields/chemistry/02-reaction-prediction-reactiont5/) | 反応物 SMILES → 生成物 SMILES (HF Transformers, 推論のみ) | T4 |
| 03 | [PyG GINE 分子物性予測](research-fields/chemistry/03-property-prediction-gnn/) | MoleculeNet ESOL 溶解度回帰 (train + evaluate) | T4 |

### 👥 [社会科学](research-fields/social-science/)（採択 55 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [LLM ペルソナ調査シミュレーション](research-fields/social-science/01-persona-survey-simulation/) | Azure OpenAI Structured Outputs で仮想ペルソナ × Likert 質問の合成回答 + χ² バイアス分析 (**合成データ専用**) | — (LLM API) |
| 02 | [歴史・法務文書の LLM 構造化](research-fields/social-science/02-document-structuring/) | Document Intelligence (prebuilt-layout) + AOAI Structured Outputs で PDF → JSON (判例・工場名簿) | — (LLM API) |
| 03 | [テキスト分類・トピッククラスタリング](research-fields/social-science/03-text-classification-clustering/) | AOAI Embeddings + scikit-learn (LogReg / KMeans) + gpt-5.4-mini による日本語クラスタラベル生成 | — (LLM API) |

### 🔬 [材料・応用医工学](research-fields/materials-medical-engineering/)（採択 33 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [材料バンドギャップ回帰](research-fields/materials-medical-engineering/01-materials-property-prediction/) | Materials Project + Matminer (magpie) + XGBoost、reduced-formula GroupKFold で組成リーク対策 | — (CPU) |
| 02 | [MACE-MP-0 汎用 NNP](research-fields/materials-medical-engineering/02-nnp-mace-mp/) | MACE-MPA-0 (MIT) で Si ダイヤモンド構造緩和 + 5 ps NVT-MD (ASE Langevin) | — (CPU) / T4 任意 |
| 03 | [顕微鏡画像セグメンテーション](research-fields/materials-medical-engineering/03-microscopy-segmentation/) | MiniUNet (~117K params) で合成 SEM 粒界セグメンテーション、torch 2.7.1 + torchmetrics | — (CPU) / T4 任意 |

### 💻 [電気工学・電子工学・情報科学・コンピューターサイエンス](research-fields/electrical-informatics/)（採択 68 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [Phi-4-mini LoRA ファインチューニング](research-fields/electrical-informatics/01-llm-lora/) | `databricks-dolly-15k-ja` × QLoRA 4-bit (TRL SFTTrainer) × Azure ML T4、日本語 instruction 適応 | T4 (CPU スモークテスト可) |
| 02 | [時系列信号分類 (1D-CNN)](research-fields/electrical-informatics/02-timeseries-1dcnn/) | UCI HAR (加速度+ジャイロ 9ch × 128 時点) × コンパクト 1D-CNN (~32K params)、被験者独立分割 | — (CPU) |
| 03 | [画像復元 U-Net (Gaussian ノイズ除去)](research-fields/electrical-informatics/03-image-restoration-unet/) | 合成幾何画像 + Gaussian ノイズ × MiniUNet (~117K params, D-3 と同構造)、L1 損失 + PSNR/SSIM | — (CPU) / T4 任意 |

### ⚙️ [機械・社会基盤・エネルギー工学](research-fields/mechanical-energy/)（採択 32 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [PINNs で 1D 熱伝導](research-fields/mechanical-energy/01-pinns-heat/) | 座標入力 MLP + Autograd 二階微分 + PDE 残差損失 (Adam→L-BFGS)、1D 熱伝導方程式 | — (CPU) |
| 02 | [強化学習 CartPole](research-fields/mechanical-energy/02-rl-cartpole/) | Stable-Baselines3 PPO × Gymnasium CartPole-v1、報酬曲線可視化 | — (CPU) |
| 03 | [振動信号異常検知](research-fields/mechanical-energy/03-vibration-anomaly-ae/) | 合成振動波形 × 1D Conv Autoencoder、再構成誤差閾値で異常判定 | — (CPU) |

その他の分野（数物・地球 / 農学・環境 / 芸術・人文）は順次追加予定です。

## 一次資料

- 採択課題 456 件の一覧: [`docs/source/spread1000-adopted.pdf`](docs/source/spread1000-adopted.pdf)
- 構造化データ: [`docs/source/spread1000-adopted.json`](docs/source/spread1000-adopted.json)
- 出典: https://www.mext.go.jp/content/20260629-mxt_jyohoka01-000050750_5.pdf

## 共通事項（すべてのシナリオ着手前に読む）

- 📘 **[Azure アカウント準備](docs/00-azure-account-setup.md)** — サブスクリプション調達・権限・az login・RP 登録
- 💰 **[コスト管理](docs/01-cost-management.md)** — 予算アラート・タグ戦略・Spot / GPU 節約
- 🎮 **[GPU クォータ申請](docs/02-gpu-quota.md)** — SKU 選定・quota 確認・増加申請

## ライセンス

各クイックスタート内で利用するモデル・データセット・OSS のライセンスは、それぞれの README に明記しています。
