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
| 06 | [病理画像 CNN 分類](research-fields/life-pharma-science/06-pathology-cnn/) | MedMNIST PathMNIST 9 クラス、PathoCNN ~95K params | — (CPU) |

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

### 🌏 [数学・物理学・地球科学](research-fields/math-physics-earth/)（採択 30 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [DDPM 最小実装](research-fields/math-physics-earth/01-ddpm-tiny/) | Tiny U-Net (~500K params) + T=200 拡散、Fashion-MNIST 16×16 で拡散モデル体験 | — (CPU) |
| 02 | [記号回帰で物理法則発見](research-fields/math-physics-earth/02-symbolic-regression/) | gplearn 遺伝的プログラミングで観測データから解析式を学習 | — (CPU) |
| 03 | [ガウス過程回帰](research-fields/math-physics-earth/03-gp-regression/) | sklearn GaussianProcessRegressor で周期信号 + ノイズを不確実性込みで回帰 | — (CPU) |
| 04 | [ニューラル PDE サロゲート](research-fields/math-physics-earth/04-pde-surrogate/) | TinyUNet (~117K params) 残差学習で 2D 移流拡散 FD を高速代替、autoregressive rollout | — (CPU) |

### 🌾 [農学・環境学・生態学](research-fields/agriculture-environment/)（採択 25 課題）

| # | シナリオ | ワークロード | GPU |
|---:|---|---|---|
| 01 | [転移学習で少数データ画像分類](research-fields/agriculture-environment/01-transfer-plant-disease/) | ResNet18 (ImageNet) backbone 凍結 + fc 再学習、Flowers102 5-class 転移学習定番パターン | — (CPU) |
| 02 | [scRNA-seq クラスタリング](research-fields/agriculture-environment/02-scrnaseq-clustering/) | scanpy (PBMC 3k) で normalization + PCA + UMAP + Leiden、single-cell 定番前処理 | — (CPU) |
| 03 | [ハイパースペクトル画像分類](research-fields/agriculture-environment/03-hyperspectral-1dcnn/) | Indian Pines 200 バンドスペクトルを 1D-CNN でピクセル単位分類 | — (CPU) |

### 🎨 [芸術・人文学](research-fields/arts-humanities/)（採択 21 課題）

| # | シナリオ | ワークロード | Azure リソース |
|---:|---|---|---|
| 01 | [音声書き起こし](research-fields/arts-humanities/01-speech-transcription/) | Azure Speech continuous recognition (ja-JP)、Detailed 出力で confidence 付き、TTS→STT ラウンドトリップデモ | Speech S0 |
| 02 | [古文書翻刻](research-fields/arts-humanities/02-document-transcription/) | Document Intelligence Layout OCR → Azure OpenAI Structured Outputs で書誌情報 Pydantic JSON 抽出 | Doc Intelligence + AOAI |
| 03 | [多言語エンベディング検索](research-fields/arts-humanities/03-multilingual-embedding-search/) | text-embedding-3-large + Azure AI Search (HNSW ベクター + BM25 ハイブリッド) で日/英/仏/独/中 コーパスを言語横断検索、FAISS ローカルフォールバック対応 | Azure AI Search + AOAI Embeddings |
| 04 | [GraphRAG ナレッジグラフ + QA](research-fields/arts-humanities/04-graphrag/) | Microsoft GraphRAG で史料/科学文献からエンティティ・関係抽出 → local/global search | AOAI GPT + Embeddings |

以上で SPReAD-1000 採択 456 課題を 10 分野 × 3-6 シナリオ (計 35 クイックスタート) でカバーします。

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

## サポートポリシー（重要）

> [!IMPORTANT]
> **本リポジトリはコミュニティ提供の非公式サンプルであり、Microsoft 公式のサポート対象ではありません。**
> コードは MIT ライセンスの "AS IS" 条項に従って提供され、Microsoft は本コードに対する SLA・障害対応・個別サポート・保証を提供しません。
>
> - **技術的な質問・不具合報告 (ベストエフォート)**: GitHub Issues / Microsoft Learn / Stack Overflow
> - **Azure サービスの障害対応・SLA が必要な場合**: [Azure Support プラン](https://azure.microsoft.com/support/plans/) (Developer / Standard / Professional Direct) または組織の **Microsoft Unified サポート契約**
> - **ライセンス調達・Enterprise 契約 (EA / MCA-E) ・本番運用の SI サポート**: [マイクロソフト パートナー (MSP / SI)](https://partner.microsoft.com/)
> - **研究データの分類・IRB・データガバナンス**: 所属機関の情報部門・倫理審査

## シナリオ選定に関する注意事項

> [!WARNING]
> **本リポジトリの 35 シナリオは、文部科学省が公開している SPReAD-1000 採択課題のタイトルから「この分野ならこういう AI 環境が典型的だろう」と推測して構築した参考実装です。**
>
> 個別の採択研究者にヒアリングして作成したものではないため、実際の研究計画で必要な以下の要素は一致しない可能性があります:
> - **ワークロード** (使うモデル・アルゴリズム・前処理)
> - **データ** (公開データセットの代替 vs 自機関のデータ)
> - **スケール** (GPU 台数・データ量・並列度)
> - **評価指標** (研究目的固有のメトリクス)
>
> 各クイックスタートは **「そのまま使うテンプレート」ではなく「まず動く型 (starter)」** として設計されています。**Azure 上の AI 環境の勘所を掴むための出発点** として利用し、皆さんの研究計画に合わせてモデル・データ・ハイパーパラメータ・評価を差し替えて改変してください。改変のヒントは各シナリオの `docs/05-your-data.md` に記載しています。

