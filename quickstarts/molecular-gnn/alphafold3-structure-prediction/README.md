# AlphaFold 3 構造予測クイックスタート

> **対象**: MEXT SPReAD-1000 生命科学・薬学分野、`molecular-gnn` カテゴリ。
> タンパク質単体だけでなく **タンパク質-リガンド / DNA / RNA / イオン / 翻訳後修飾** を含む
> 複合体構造を高精度に予測したい研究者向け。
>
> **前提**: Azure と AI for Science が初めての方でも、コマンドをコピー&ペーストすれば動くことを目指します。
> **所要時間**: 初回セッション 約 3〜6 時間（重み申請後）。
> **想定コスト**: 約 ¥5,000〜¥10,000／セッション（H100, Japan East, PAYG, アイドル自動停止あり）。

---

## ⚠ このクイックスタートで生成した構造は「AI 予測」です

- pLDDT / pTM / ipTM / ranking_score は **信頼度スコア**であって、実験検証の代替ではありません。
- リガンド結合姿勢や複合体界面は特に予測誤差が大きくなり得ます。
- 医療・臨床判断や創薬の意思決定には、必ず実験による検証を経てください。
- AF3 の出力は **AlphaFold 3 Output Terms of Use**（非商用）に従います。詳細は [`docs/04-interpret-results.md`](docs/04-interpret-results.md)。

---

## ⚠ ライセンスに関する 3 つの重要事項

AlphaFold 3 は **3 種類の異なるライセンス** に従います。混同すると規約違反になります。

| 対象 | ライセンス | 商用利用 | 再配布 |
|------|-----------|---------|-------|
| **ソースコード** (github.com/google-deepmind/alphafold3) | Apache License 2.0 | ✅ 可 | ✅ 可 |
| **モデル重み** (`af3.bin`) | AlphaFold 3 Model Parameters Terms of Use（非商用カスタム）| ❌ 不可 | ❌ 不可（承認組織内のみ） |
| **AF3 の出力** (mmCIF, confidence JSON 等) | AlphaFold 3 Output Terms of Use（非商用）| ❌ 不可 | 条件付き（`TERMS_OF_USE.md` 添付要）|

- **このリポジトリには `af3.bin` を含めません。** ユーザーが Google フォームから直接受領してください。
- **承認は「個人」または「機関代表者」に対して個別に発行**されます。あなたの承認範囲を確認してください。
  - 個人承認 → その個人だけが利用可。同僚と共有しない。
  - 機関代表者承認 → 承認された組織の従業員/協力者と共有可（承認要件の範囲内）。
- **SPReAD-1000 の研究課題は通常「非商用の学術研究」に該当**しますが、企業共同研究や委託研究に利用する場合は所属機関の法務レビューを推奨します。

公式ドキュメント:
- [Model Parameters Terms of Use](https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md)
- [Prohibited Use Policy](https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_PROHIBITED_USE_POLICY.md)
- [Output Terms of Use](https://github.com/google-deepmind/alphafold3/blob/main/OUTPUT_TERMS_OF_USE.md)

---

## 何ができるか

- **単体タンパク質** の 3D 構造を高精度予測（従来の AlphaFold 2 相当以上）
- **タンパク質-タンパク質複合体** (multimer) の構造+界面予測
- **タンパク質-低分子リガンド複合体**（CCD コードまたは SMILES）
- **タンパク質-核酸複合体**（DNA/RNA）
- **翻訳後修飾** (PTM) を含む構造予測
- **共有結合リガンド**、**イオン**、**修飾ヌクレオチド** の扱い

**ESMFold との違い（`../esmfold-structure-prediction/`）**:

| 観点 | ESMFold | AlphaFold 3 |
|------|---------|-------------|
| 対象 | タンパク質単体（1024 aa 上限）| タンパク質＋DNA/RNA/リガンド/イオン等（〜5,120 トークン標準）|
| MSA データベース | 不要（PLM 由来）| 必要（約 630 GB 展開）|
| 重みライセンス | MIT | 非商用カスタム、申請必須（2〜3 営業日）|
| 推論時間 (300aa) | 数秒〜数十秒 | MSA 含め約 10〜15 分（H100、300aa 単量体、NIG L40S 実測に基づく参考値）|
| GPU 必要 VRAM | 8〜16 GB（NC4/NC8 T4 で可）| 80 GB 以上（H100/A100 80GB）|
| 1 セッション費用 | 約 ¥300〜¥1,700 | 約 ¥5,000〜¥10,000 |
| 出力形式 | PDB | mmCIF |

「タンパク質単体だけで十分」なら ESMFold のクイックスタートをお勧めします。

---

## 全体の流れ

```text
[申請 数日前] Google フォームで AF3 重みを申請 (2〜3 営業日で承認メール)
       ↓
[Day 1] 事前準備: サブスクリプション/クォータ/リージョン確認 (docs/01)
       ↓
[Day 1] Azure ML Workspace + H100 Compute Instance を Bicep でデプロイ (docs/02)
       ↓
[Day 1] Compute Instance にサインイン → af3.bin を安全にアップロード
       ↓
[Day 1] setup-af3.sh: Docker ビルド → 630GB DB を /mnt にダウンロード (約 60〜120 分)
       ↓
[Day 1] ubiquitin_monomer.json で動作確認 → TetR/tetracycline 複合体で応用
       ↓
[Day 1 終わり] 出力を Blob に退避 → Compute Instance を停止 (docs/05)
```

---

## クイックスタート構成

```text
alphafold3-structure-prediction/
├── README.md                       (このファイル)
├── docs/
│   ├── 01-prerequisites.md         事前準備・重み申請・クォータ確認
│   ├── 02-provision-aml.md         Azure ML デプロイ手順（Bicep）
│   ├── 03-run-af3.md               setup-af3.sh 実行 → 推論
│   ├── 04-interpret-results.md     mmCIF / pLDDT / pTM / ipTM の読み方
│   ├── 05-cleanup.md               停止・削除・データ退避
│   └── troubleshooting.md          エラー対応集
├── infra/
│   ├── main.bicep                  Workspace + Compute Instance
│   ├── deploy.sh                   az deployment group create ラッパー
│   └── parameters.example.json     Bicep パラメータ雛形（H100 デフォルト）
└── scripts/
    ├── setup-af3.sh                Docker ビルド + DB ダウンロード
    ├── run-inference.py            AF3 推論ラッパー
    └── examples/
        ├── ubiquitin_monomer.json  76aa 動作確認用（公式サンプル）
        └── tetr_dimer_tetracycline.json  ホモ二量体+リガンド応用例
```

---

## コスト概算（Japan East, PAYG, 2026 年 7 月時点）

| SKU | GPU | VRAM | 時給 | 1 セッション (4h) | メモ |
|-----|-----|------|------|-------------------|------|
| **Standard_NC40ads_H100_v5** ★推奨 | H100 NVL | 94 GB | ¥1,637 | 約 ¥6,548 | 最速、最大 5,120 トークン |
| **Standard_NC24ads_A100_v4** | A100 | 80 GB | ¥861 | 約 ¥3,444 | H100 の約 1.5〜2 倍時間、最大 5,120 トークン |

補足:
- Azure ML Compute Instance の **OS ディスクは 120 GB 固定** です。DB (630 GB) は `/mnt` の一時 NVMe を使います。
  停止すると `/mnt` は消えるため、DB を毎回ダウンロードする覚悟が必要です（永続化は [`docs/05-cleanup.md`](docs/05-cleanup.md) 参照）。
- **アイドル自動停止 (60 分)** を有効化することで、閉め忘れによる高額課金を防ぎます。
- 上記は Compute Instance のみの費用。Workspace 付属の Storage/Container Registry/Key Vault は月数十円〜数百円レベルです。
- 詳細は Azure 料金計算ツールで再確認: <https://azure.microsoft.com/pricing/calculator/>

---

## 次のステップ

**まず [`docs/01-prerequisites.md`](docs/01-prerequisites.md)** を読み、
- サブスクリプションと権限を確認
- **Google フォームから AF3 重みを申請**（承認まで 2〜3 営業日、余裕を持って）
- H100 または A100 の vCPU クォータを確認

を進めてください。

---

## サポート

- **AF3 本家の質問**: <https://github.com/google-deepmind/alphafold3/discussions>
- **Azure ML の質問**: [Microsoft Q&A](https://learn.microsoft.com/answers/topics/azure-machine-learning.html)
- **このクイックスタート自体の問題**: [Issues](https://github.com/nahisaho/spread1000-azure-quickstart/issues) で報告してください
