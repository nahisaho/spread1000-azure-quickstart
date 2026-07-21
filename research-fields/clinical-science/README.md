# 臨床科学（Clinical Sciences）

SPReAD-1000 第1回公募で **70 課題**が採択された分野です。医用画像解析、電子カルテ解析、生体信号処理などが中心です。

## クイックスタート一覧

| # | シナリオ | 用途 | GPU / 計算資源 | 想定コスト (1 回) |
|---:|---|---|---|---:|
| [01](01-medical-imaging-monai/) | **MONAI 3D 医用画像セグメンテーション** | CT/MRI の 3D セグメンテーション (spleen で例示) | NC4as_T4_v3 (推論) / NC24ads_A100_v4 (fine-tune) | ¥300〜3,000 |

## 学習パス（推奨順）

1. **MONAI 3D** — Bundle Zoo を用いた最短ルート。まず 20 症例の推論を数分で回し、続いて自データで fine-tune

## 想定される SPReAD-1000 課題例（実データより）

- 「医用画像」「CT/MRI 解析」「病変検出」→ シナリオ 01
- 「電子カルテ NLP」「臨床テキスト解析」→ 今後追加予定
- 「生体信号 (ECG/EEG) 時系列」→ 今後追加予定

## 追加予定

- **電子カルテ NLP** (Azure OpenAI + AI Search)
- **生体信号時系列** (Time Series Insights / Fabric)
- **予測モデル** (AutoML on AML)
