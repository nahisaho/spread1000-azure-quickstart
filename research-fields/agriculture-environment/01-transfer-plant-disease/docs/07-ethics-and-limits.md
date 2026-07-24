# 07 — 倫理と限界

## 農業実装における注意点

- **誤検出コスト**: 健全な作物を病害と判定 → 不要な農薬散布/廃棄 → 経済的損失
- **未検出コスト**: 病害を見逃す → 拡散して収穫全滅
- 用途に応じて precision / recall のバランスを人間が決定する

## ドメインシフト

- 学習: 特定農園の特定品種、特定カメラ
- デプロイ: 他農園、他品種、スマホカメラ → 精度が急落
- 対策: **多様な条件のデータで学習**、または domain adaptation

## ImageNet 事前学習の偏り

- ImageNet 1000 クラス自体に地理的・文化的偏り (欧米中心)
- 特殊な植物 (熱帯・農産物・地衣類) では ResNet の特徴が微妙
- 対策: 農業ドメイン専用の事前学習モデル (e.g., PlantNet) を検討

## 説明可能性

- ブラックボックス予測は農家に受け入れられにくい
- Grad-CAM 等で **どの画像領域を根拠に判定したか** を可視化する仕組みを併設

## 責任所在

- AI 診断結果を根拠に散布・廃棄した場合の責任 (メーカー？農家？診断提供者？) は法的にグレー
- 導入前に **専門家 (植物病理学者、農業技師) との合意** と、**AI 判定は補助**とする運用ポリシーを明文化

> [!CAUTION]
> **農薬散布・作物廃棄の自動化は禁止**。本モデルの出力を直接トリガーとして農薬散布指令・廃棄指令を発行するシステムに組み込んではならない。いかなる判定結果も、必ず植物病理学者または農業技師による人間の確認を経てから実行すること。

## 参考文献

- Mohanty, Hughes, Salathé (2016). *"Using Deep Learning for Image-Based Plant Disease Detection"*, Frontiers in Plant Science
- Barbedo (2018). *"Impact of dataset size and variety on the effectiveness of deep learning and transfer learning for plant disease classification"*, Comput. Electron. Agric.
