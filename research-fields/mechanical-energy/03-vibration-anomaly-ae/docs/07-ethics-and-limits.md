# 07 — 倫理と限界

## 誤検出 (false positive) / 未検出 (false negative) のコスト非対称性

- **産業機器の予知保全**: 未検出 = 事故・停止・人身リスク、誤検出 = 不要な保全作業コスト。**未検出のコスト >> 誤検出コスト**
- **医療機器モニタリング**: 未検出 = 命に関わる、誤検出 = アラート疲労
- 用途によって閾値を非対称に選ぶ (recall 優先か precision 優先か) 意思決定が必要

## 教師なし異常検知の根本的限界

- **異常のパターンを事前に知らない**ため、AE が正常として学習してしまう「学習漏れ異常」が発生しうる
- 例: 学習期間中に軽微な欠陥が既に存在していた → AE がそれを正常と学習
- 対策: **domain expert による学習データレビュー** を必ず入れる

## 分布シフト

- 温度・湿度・回転数・負荷条件が変わると正常分布も変化 → 誤検出増加
- ドリフト検知メカニズム (KS 検定, PSI) を別途組み込む必要

## 実運用への監査

- 検出結果の **根拠可視化** (どのタイミングの再構成誤差が大きかったか): 再構成波形と原波形を重ねて表示
- 稼働時間ロギング、閾値変更履歴、再学習履歴を必ず記録

## 参考文献

- Ruff et al. (2021). *"A Unifying Review of Deep and Shallow Anomaly Detection"*, Proc. IEEE
- Smith, Randall (2015). *"Rolling element bearing diagnostics using the Case Western Reserve University data"*, Mech. Syst. Signal Process.
