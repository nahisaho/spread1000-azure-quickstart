# 08 — 医療データへの適応メモ

> [!IMPORTANT]
> 本シナリオは UCI HAR の教育用 quickstart です。医療データへ移す際は、**ライセンス・倫理・分割設計** を最初に作り直してください。

## ライセンス確認表

| データ種別 | 例 | ライセンス / アクセス条件 | 実務上の注意 |
|---|---|---|---|
| PhysioNet Open Access | PTB-XL, MIT-BIH | **ODC-By 1.0**、出典表示必須 | 論文・manifest にデータ版、引用、ライセンス URL を必ず残す |
| Credentialed access | 一部の ICU / EHR / 医用画像データ | **人対象研究トレーニング + DUA 必須** | 認証情報の共有禁止、再配布禁止、許可外用途への転用禁止 |

## manifest に必ず残す項目

医療系データへ適応する場合、`reproducibility_manifest.json` または同等の追跡台帳に最低限以下を記録してください。

1. **dataset version**（例: PTB-XL v1.0.3）
2. **正式 citation**（論文・DOI・URL）
3. **license / DUA 情報**
4. **取得日・前処理版・除外基準**
5. **患者 / セッション / 施設 / 装置の分割ポリシー**

## 時間リーク・セッションリークを防ぐ

医療時系列では、subject-independent だけでは不十分です。以下を同時に守ってください。

- **患者単位で grouping**（同一患者を train / val / test に跨がせない）
- **recording / session 単位でも grouping**（同一入院・同一検査日の窓を跨がせない）
- **duplicate-window hash** を作り、重複窓・ほぼ重複窓を除去する
- **site / device separation** を明示し、施設差・機器差のリークを防ぐ
- 実運用時点の性能が重要なら **chronological holdout** を使う

PTB-XL でも、患者を跨がない fold を使うことが再現性と公正比較の前提です。患者尊重の fold 設計を崩すと、性能は簡単に過大評価されます。

## 推奨チェックリスト

- [ ] train / val / test で患者 ID が重複していない
- [ ] session / recording 単位でも重複していない
- [ ] duplicate-window hash を保存した
- [ ] site / device / acquisition-year の分離方針を明文化した
- [ ] 評価指標に macro-F1 だけでなく、感度・特異度・校正も含めた
- [ ] データ版・引用・ライセンスを manifest に保存した
