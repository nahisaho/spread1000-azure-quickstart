# 05 — 実データへの応用

## CWRU Bearing Dataset (推奨)

- Case Western Reserve University の公開ベアリングデータセット
- ダウンロード: https://engineering.case.edu/bearingdatacenter/
- 12k / 48k サンプリング周波数、複数の欠陥種別 (Inner race, Outer race, Ball)、複数の欠陥サイズ

### 適用手順

1. `.mat` ファイルを scipy.io で読み込み: `scipy.io.loadmat('X097_DE_time.mat')`
2. 長時間信号を **オーバーラップウィンドウ** (2048 samples, stride 1024) で切り分け
3. 正常時 (baseline dataset) を train/val に、欠陥時を test にする
4. `src/generate_data.py` を書き換えて npz を作成
5. 学習・評価は本 quickstart のスクリプトをそのまま流用

### 注意

- 実データではラベルノイズ (欠陥と診断されたが実は正常/その逆) が混じる可能性
- 回転数 (rpm) が異なるとスペクトルもシフト → **同一回転数条件で学習・評価**
- MIMII / ToyADMOS など他の公開データも同様の要領

## 前処理の推奨

- **順序**: DC 除去 → バンドパスフィルタ (10 Hz 〜 fs/2) → ウィンドウ切り出し → 正規化
- **周波数領域特徴** も試す: STFT スペクトログラム を 2D 画像として `Conv2D AE` に投入すると F1 が上がるケースが多い

## モデル拡張

- **Variational AE (VAE)**: 潜在分布に prior を仮定、より smoother な latent space
- **LSTM AE**: 時系列の長期依存を扱いたい場合
- **PatchCore / PaDiM (画像 AD の技法)**: スペクトログラムに転用可能

## 分布シフトへの対処

- 環境変化 (温度、回転数、負荷) に伴い正常分布が変わる → **リカバリブル・キャリブレーション**
- 定期的に val セットを再サンプルし、閾値を再決定する運用が現実的
