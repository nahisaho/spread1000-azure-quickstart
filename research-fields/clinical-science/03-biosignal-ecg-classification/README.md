# 生体信号 ECG 分類クイックスタート (MIT-BIH × PyTorch 1D CNN on Azure ML)

**PhysioNet MIT-BIH Arrhythmia Database** の心電図から **AAMI 5 クラス (N/S/V/F/Q)** の心拍分類を、Azure Machine Learning (AML) の command job で学習する最短ルートです。

> [!IMPORTANT]
> **教育・研究用途専用**です。本 quickstart で作成されるモデルは診断・治療・医療機器のいずれの目的にも使用できません。医療現場での ECG 判読を代替するものではありません。

## ゴール

- Azure ML ワークスペースを Bicep でデプロイ
- MIT-BIH の 48 レコードを ローカル → Blob に登録
- 小型 1D CNN (~9.5k params) を **T4 GPU (`Standard_NC4as_T4_v3`)** で 10〜15 epoch 学習
- MLflow に macro-F1 / confusion matrix / classification report を記録
- モデルを AML Job output として保存

**CPU フォールバック**: GPU quota が 0 の場合は `Standard_D4as_v5` に切替可能です（約 3〜5 倍時間かかるが動作は同一）。

## 所要時間・コスト目安

| 項目 | 目安 |
|---|---|
| 初回デプロイ (Bicep) | 5〜8 分 |
| データ ダウンロード + Blob 登録 | 3〜5 分 |
| Environment build | 5〜10 分（初回のみ、ACR ビルド） |
| Compute プロビジョン | 3〜5 分（初回のみ、cold start） |
| Training (T4, 15 epoch) | 15〜25 分 |
| **合計初回** | 約 40〜60 分 |
| **VM 料金 (T4 Japan East, 30 分)** | **約 $0.36** |
| ACR Basic (固定) | 約 $5/月 (0.167 USD/日) |
| Storage / Log Analytics / App Insights | 月額 $1 未満（本チュートリアル規模） |
| **想定 1 run 総コスト** | **$1〜3**（初回は image build 分含む、ACR 固定費は日割り分のみ） |

> [!TIP]
> `compute-t4.yml` の `min_instances: 0` により、ジョブが完了すればノードは自動的に **スケールダウン (0 台) → compute VM 課金 0** になります。ただし ACR Basic はコンテナが 0 でも月 $5 程度発生するため、長期的に使わない場合は Resource Group ごと削除してください（→ `docs/05-cleanup.md`）。

## データセット

| 項目 | 内容 |
|---|---|
| データ | [MIT-BIH Arrhythmia Database v1.0.0](https://physionet.org/content/mitdb/1.0.0/) |
| ライセンス | Open Data Commons Attribution License v1.0 (ODC-By 1.0) |
| サイズ | 48 レコード × 約 30 分 = 47 被験者、110,000+ 心拍注釈、~104 MB |
| サンプリング | 360 Hz、2 チャネル (通常 MLII + V1/V2/V5) |
| アクセス | Open Access（PhysioNet 資格認定不要） |
| 出典 | Moody GB, Mark RG. *IEEE Eng Med Biol* 20(3):45-50, 2001. |

**AAMI 5 クラス マッピング** (ANSI/AAMI EC57):

| AAMI クラス | MIT-BIH 記号 | 意味 |
|---|---|---|
| **N** (Normal) | `N L R e j` | 正常、脚ブロック、上室性 escape |
| **S** (SVEB) | `A a J S` | 上室性期外収縮 |
| **V** (VEB) | `V E` | 心室性期外収縮・escape |
| **F** (Fusion) | `F` | 正常/心室融合 |
| **Q** (Unknown) | `/ f Q` | ペーシング、paced fusion、分類不能 |

非 beat 注釈および未マップの注釈は学習・評価から除外します。
このカテゴリには **非 beat の rhythm/quality 注釈** (`| ! [ ] + ~` 等) と、
**学習中に定まらなかった beat 注釈** (`?` = LEARN、WFDB 上は beat 注釈ですが AAMI 5 クラスに
写像できないため除外) が含まれます。

## ドキュメント

| # | ドキュメント | 内容 |
|---:|---|---|
| 01 | [prerequisites.md](docs/01-prerequisites.md) | Azure サブスクリプション / CLI / GPU quota 準備 |
| 02 | [provision-aml.md](docs/02-provision-aml.md) | Bicep で AML Workspace + 依存リソースをデプロイ |
| 03 | [download-and-upload.md](docs/03-download-and-upload.md) | MIT-BIH ダウンロード + Blob 登録 |
| 04 | [train-and-evaluate.md](docs/04-train-and-evaluate.md) | AML command job で 1D CNN 学習 → 評価 |
| 05 | [cleanup.md](docs/05-cleanup.md) | リソース削除で課金停止 |
| — | [troubleshooting.md](troubleshooting.md) | よくあるつまずき集 |

## リポジトリ構成

```
03-biosignal-ecg-classification/
├── README.md                       (本ファイル)
├── troubleshooting.md
├── docs/
│   ├── 01-prerequisites.md
│   ├── 02-provision-aml.md
│   ├── 03-download-and-upload.md
│   ├── 04-train-and-evaluate.md
│   └── 05-cleanup.md
├── infra/
│   ├── main.bicep                  (Workspace + Storage + KV + ACR + AppInsights)
│   ├── deploy.sh
│   └── parameters.example.json
├── aml/
│   ├── conda.yml                   (Python 3.10 + torch 2.4 + wfdb 4.3.1)
│   ├── environment.yml             (mcr openmpi5.0-cuda12.4 base)
│   ├── compute-t4.yml              (Standard_NC4as_T4_v3, min=0, max=1)
│   ├── compute-cpu.yml             (Standard_D4as_v5, quota 0 時の fallback)
│   ├── data-mitbih.yml             (Blob 上の MIT-BIH を uri_folder data asset 化)
│   └── job-train.yml               (command job YAML)
├── scripts/
│   ├── download-data.sh            (PhysioNet から MIT-BIH を wget)
│   ├── upload-dataset.sh           (AAD 認証で Blob へ upload)
│   └── verify-output.py            (MLflow ラン + metrics 確認)
└── src/
    ├── prepare_data.py             (wfdb で record → (window, label) NPZ 作成)
    ├── model.py                    (小型 1D CNN)
    └── train.py                    (学習エントリーポイント — AML command job で実行)
```

## 出典・ライセンス

- **データ**: Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. *IEEE Eng Med Biol* 20(3):45-50, 2001. (ODC-By 1.0)
- **PhysioNet プラットフォーム**: 現行の PhysioNet 引用推奨に従い、
  データセットページ ([mitdb 1.0.0](https://physionet.org/content/mitdb/1.0.0/)) 記載の最新引用形式を
  使用してください。歴史的な Goldberger et al. *Circulation* 101(23):e215-e220, 2000. と併せ、
  必要に応じて Pollard et al. (2026) 等の更新引用を追加します（PhysioNet 側の掲載を確認）。
- **AAMI クラス定義**: ANSI/AAMI EC57:2012/(R)2020
- **クラス評価手法**: de Chazal et al. *IEEE Trans Biomed Eng* 51(7):1196-1206, 2004. https://doi.org/10.1109/TBME.2004.827359

## 参照

- [../../../docs/00-azure-account-setup.md](../../../docs/00-azure-account-setup.md)
- [../../../docs/01-cost-management.md](../../../docs/01-cost-management.md)
- [../../../docs/02-gpu-quota.md](../../../docs/02-gpu-quota.md)
