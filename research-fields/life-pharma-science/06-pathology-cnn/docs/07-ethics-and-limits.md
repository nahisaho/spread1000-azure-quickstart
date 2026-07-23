# 07 — 倫理と限界

## 医療 AI の規制

- **診断への直接利用は薬事承認 (PMDA/FDA) が必須**
- 本教材のような研究用モデルは **診断支援ツール** として位置づけ、最終判断は病理医
- SaMD (Software as a Medical Device) 分類、GxP 準拠が必要

## データバイアス

- PathMNIST の元データは **単一施設 (NCT/UMM Heidelberg)** の H&E 染色
- **他施設の染色プロトコル、スキャナ、患者集団**では精度が急落する (domain shift)
- **染色正規化**、**多施設データでの学習**が実用化には必須
- 民族/地域による組織所見の違いにも注意

## False Positive/Negative の非対称コスト

- FN (見逃し): 治療機会損失 → 生命リスク
- FP (過剰診断): 不要な精密検査、患者不安、医療コスト
- **threshold 調整で recall (sensitivity) を優先**することが多い
- ROC/PR カーブで運用点を明示

## 説明可能性

- ブラックボックス予測は病理医・患者に受け入れられにくい
- **Grad-CAM, Attention Map** で「どの領域を根拠に判定したか」を可視化
- CLAM, HIPT 等の MIL モデルは attention weight で解釈可能

## プライバシー

- 病理画像は **個人識別情報 (PHI)** に該当する場合あり (メタデータ、識別マーク)
- 学習前に**匿名化**、Azure なら **Azure Health Data Services** で HIPAA 準拠環境
- 論文/公開時は **IRB 承認**必須、患者同意書テンプレート整備

## AI 診断結果の責任

- 医療事故時の責任所在 (医師/病院/開発者/AI ベンダー) は法的にグレー
- **人間による最終確認**を必須プロセスとして組み込む
- 医療機関のガバナンス方針との整合

## 参考

- FDA (2021). *"Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan"*
- PMDA (2024). *"次世代医療機器・再生医療等製品評価指標"* (AI 医療機器評価指標)
- 日本病理学会「AI 病理診断ガイドライン」
