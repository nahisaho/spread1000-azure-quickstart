# 07 — 倫理と限界

## 生成モデル一般に共通するリスク

- **学習データバイアスの継承**: 大規模拡散モデルは web スケールデータから性別・人種等のバイアスを取り込む
- **プライバシー**: 学習データ内の顔画像・個人情報が生成物に一部再現される (memorization) 事例が報告されている
- **合成メディアの悪用**: deepfake, misinformation

## 本教材の範囲

- Fashion-MNIST (16×16 グレースケール、服カテゴリのみ) での演習に限り、**上記リスクは無視できるほど小さい**
- データセットを差し替える場合 (顔・独占資料・科学データ等) は以下を再確認:
  ライセンス・同意 / 合成コンテンツの表示 / 来歴管理 / なりすまし用途の禁止
- しかし、**同じアーキテクチャで学習データを差し替えれば大規模モデルと同型の問題が発生する**ことは理解しておく

## 科学応用における注意

- 分子・材料生成に使う場合、生成物の **物理妥当性** はモデルでは保証されない → 別途 DFT や実験検証が必要
- 気象データ生成では、**極値イベント** (熱波、豪雨) が学習分布から外れやすく、ダウンスケーリング誤差が大きい

## 参考文献

- Ho, Jain, Abbeel (2020). *"Denoising Diffusion Probabilistic Models"*, NeurIPS
- Song et al. (2021). *"Score-Based Generative Modeling through SDEs"*, ICLR
- Karras et al. (2022). *"Elucidating the Design Space of Diffusion-Based Generative Models"*, NeurIPS
- Carlini et al. (2023). *"Extracting Training Data from Diffusion Models"*, USENIX Security
