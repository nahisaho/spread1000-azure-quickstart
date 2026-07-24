# 05 — 実データへの応用

## CWRU Bearing Dataset

Case Western Reserve University (CWRU) が公開しているベアリング振動データセット。

> **ライセンス・引用上の注意**
>
> - 利用前に CWRU Bearing Data Center の現行利用規約を必ず確認すること:
>   <https://engineering.case.edu/bearingdatacenter/>
> - 本データセットは研究・教育目的での利用が想定されている (商用利用については
>   現行の利用規約を確認すること)。
> - ダウンロードしたファイルの **SHA-256 ハッシュと取得日** を記録すること:
>   ```bash
>   sha256sum X097_DE_time.mat  # 例: 取得日と照合
>   ```
> - 引用例 (取得日・バージョン・ファイル URL を必ず含める):
>   ```
>   Loparo, K. (2012). Bearing Data Center.
>   Case Western Reserve University.
>   Retrieved [YYYY-MM-DD] from https://engineering.case.edu/bearingdatacenter/
>   SHA-256: <ハッシュ値>
>   ```
> - 「公開データなら制限なし」とは主張しないこと。

### データの基本情報

- サンプリング周波数: 12k / 48k サンプル/秒
- 複数の欠陥種別: Inner race, Outer race, Ball
- 複数の欠陥サイズ (0.007〜0.028 inch)

### 適用手順

**⚠️ 重要: データ分割はウィンドウ切り出しの前に行うこと (MED 13 参照)**

以下の順序を必ず守る。この順序を誤るとウィンドウ間のデータ漏えいが生じる。

```python
# 1. まず、ソース録音を「機械」「取得ラン」「時間ブロック」で分割する
#    同一ラン内の連続データをランダムに train/test に分けてはいけない

# 正例: 取得ランごとに先に分割
all_runs = {
    "normal_run1": load_mat("97.mat"),    # 正常ラン
    "normal_run2": load_mat("98.mat"),    # 正常ラン (別取得)
    "fault_run1":  load_mat("105.mat"),   # 欠陥ラン
}
train_runs = ["normal_run1"]
cal_runs   = ["normal_run2"]   # 閾値キャリブレーション用
test_runs  = ["fault_run1"]    # テスト用

# 2. 各分割ごとに独立してウィンドウを切り出す
def window_signal(signal: np.ndarray, win: int = 2048, stride: int = 1024):
    """1 つのランのシグナルをウィンドウに切り分ける."""
    return np.stack([
        signal[i:i + win]
        for i in range(0, len(signal) - win + 1, stride)
    ])

X_train = window_signal(all_runs["normal_run1"])
X_cal   = window_signal(all_runs["normal_run2"])
X_test  = window_signal(all_runs["fault_run1"])

# 禁止: ウィンドウ化したあとにランダム分割 ← オーバーラップ漏えい
# X_all = window_signal(concat_all_runs)
# X_train, X_test = train_test_split(X_all)  # ← これはやってはいけない

# 3. npz に保存して学習パイプラインに投入
np.savez_compressed("data/real_bearing.npz",
                    X_train=X_train, X_val=X_cal[:32], X_cal=X_cal,
                    X_test=X_test, y_test=y_test,
                    fs=12000.0, sample_len=2048)
```

### なぜウィンドウ前に分割するのか

オーバーラップウィンドウ (stride < win) では、隣接するウィンドウが同じ元データを共有する。
**ウィンドウ化後にランダム分割すると、同一録音の前後ウィンドウが train と test に散らばり、
実質的なデータ漏えいが起きる**。ROC-AUC が楽観的な値になるため、実運用では再現しない。

正しい順序:
1. ソース録音を機械 / 取得ラン / 連続時間ブロックで分割
2. 各分割ごとに独立してウィンドウ切り出し
3. ウィンドウレベルのランダム分割は同一録音内では禁止

## 実データのプライバシーと情報管理

実機振動データには以下の情報が含まれる可能性がある:

- **資産同定**: 機械の固有振動数・共振周波数から機種・型番が特定されうる
- **稼働情報**: 回転数・負荷パターンから生産スケジュール・稼働率が推測されうる
- **故障履歴**: 欠陥パターンから保全記録が漏えいしうる

**外部へのデータ移動前に以下を確認すること**:
- アクセス制御 (最小権限、ロールベース)
- 資産 ID の削除・仮名化
- 保持期間の設定と期限後削除
- 転送・保存時の暗号化 (TLS + AES-256 等)
- 社内・外部への持ち出し可否に関する機関・組織の承認取得

## 前処理の推奨

- **順序**: DC 除去 → バンドパスフィルタ (10 Hz 〜 fs/2) → ウィンドウ切り出し → 正規化
- **周波数領域特徴** も試す: STFT スペクトログラム を 2D 画像として `Conv2D AE` に投入すると F1 が上がるケースが多い

## モデル拡張

- **Variational AE (VAE)**: 潜在分布に prior を仮定、より smoother な latent space
- **LSTM AE**: 時系列の長期依存を扱いたい場合
- **PatchCore / PaDiM (画像 AD の技法)**: スペクトログラムに転用可能

## 分布シフトへの対処

- 環境変化 (温度、回転数、負荷) に伴い正常分布が変わる → **リカバリブル・キャリブレーション**
- 定期的に `X_cal` セットを再サンプルし、閾値を再決定する運用が現実的
