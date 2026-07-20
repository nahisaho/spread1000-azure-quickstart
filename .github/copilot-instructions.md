# SPReAD-1000 Azure クイックスタート — Copilot 指示書

## リポジトリの目的

文部科学省 **SPReAD-1000** 採択者（大学・研究機関の研究者）向けに、**Azure リソースを最速でデプロイする**ためのクイックスタート集を提供する。読者は次の前提で書くこと。

- **AI for Science を扱ったことがない**
- **Azure を使ったことがない**
- 研究者本人が読み、自分でコピペしてデプロイする

初心者を迷わせない導線と、**課金を止め忘れない**構成を最優先する。

---

## ディレクトリ構成

**研究分野別トップ × ワークロード（AI 手法）別配下**。ユーザーは自分の分野から入る。

分野は **文部科学省 SPReAD-1000 公募要領の 10 分野**（`docs/source/spread1000-adopted.pdf`）に準拠する。ディレクトリ名は**英語スラッグ**、README の見出しは日本語を併記する。

```
research-fields/
  life-pharma-science/       # 生命科学・薬学（98 課題）
  clinical-science/          # 臨床科学（70 課題）
  eecs-cs/                   # 電気工学・電子工学・情報科学・コンピューターサイエンス（68 課題）
  social-science/            # 社会科学（55 課題）
  materials-process-biomed/  # 材料・プロセス・応用医工学（33 課題）
  mech-infra-energy/         # 機械・社会基盤・エネルギー工学（32 課題）
  math-physics-earth/        # 数学・物理学・地球科学（30 課題）
  agri-env-ecology/          # 農学・環境学・生態学（25 課題）
  arts-humanities/           # 芸術・人文科学（23 課題）
  chemistry/                 # 化学（22 課題）
    README.md                # この分野の学習パス（採択課題例・カテゴリ内訳・推奨クイックスタート）
    01-<category>-<scenario>/
      README.md              # 概要／前提／時間／コスト／次ステップ のみ
      steps/
        01-prerequisites.md
        02-deploy.md
        03-verify.md
        04-run-sample.md
        99-cleanup.md        # cleanup は必ず 99 番
      bicep/   # または azd/ または cli/
      .env.example
shared/                      # 分野横断の共通テンプレート
  bicep-modules/
  azd-templates/
docs/
  00-azure-account-setup.md
  01-cost-management.md
  source/                    # 一次情報（PDF・JSON・分類結果）
    spread1000-adopted.pdf
    spread1000-adopted.json
    projects-classified.json
```

同じテンプレートを複数分野から使うときは、`shared/` に置いて README からリンクする（重複コピーしない）。

**分野内訳**（合計 456 課題、`docs/source/projects-classified.json` より）:

| 英語スラッグ | 分野名 | 課題数 |
|---|---|---:|
| life-pharma-science | 生命科学・薬学 | 98 |
| clinical-science | 臨床科学 | 70 |
| eecs-cs | 電気工学・電子工学・情報科学・コンピューターサイエンス | 68 |
| social-science | 社会科学 | 55 |
| materials-process-biomed | 材料・プロセス・応用医工学 | 33 |
| mech-infra-energy | 機械・社会基盤・エネルギー工学 | 32 |
| math-physics-earth | 数学・物理学・地球科学 | 30 |
| agri-env-ecology | 農学・環境学・生態学 | 25 |
| arts-humanities | 芸術・人文科学 | 23 |
| chemistry | 化学 | 22 |

---

## AI 手法カテゴリと Azure ワークロードマッピング

採択 456 課題を分類した **13 の AI 手法カテゴリ**（`docs/source/projects-classified.json` の `primary_category`）と、それぞれの Azure ワークロード：

| カテゴリ | 課題数 | Azure サービス | 主な使い所 |
|---|---:|---|---|
| **`foundation-model-science`** ⭐ | 18 | **Azure AI Foundry** (Foundry Models / Foundry Labs) | 科学基盤モデルの即利用 |
| `llm-rag` | 62 | Azure OpenAI + AI Search | LLM / RAG / エージェント |
| `graph-rag` | 2 | AOAI + AI Search + Cosmos DB (Gremlin) | ナレッジグラフ RAG |
| `medical-imaging` | 27 | Azure Machine Learning + GPU VM (NC/ND) | 医用画像 (CT/MRI/病理/内視鏡等) |
| `computer-vision` | 49 | AML + GPU VM | 一般画像・動画・顕微鏡・リモセン |
| `nlp-text` | 28 | AOAI / AML | 古典 NLP・OCR・多言語コーパス |
| `speech-audio` | 10 | Azure AI Speech + AML | 音声認識・音響信号 |
| `timeseries-signal` | 43 | AML + Data Lake | 時系列・生体信号 (EEG/ECG/加速度) |
| `omics-bioinfo` | 37 | AML + Azure Batch/Storage | シングルセル・ゲノム・空間トランスクリプトーム |
| `molecular-gnn` | 54 | GPU VM (PyTorch Geometric) / AML | 分子生成・GNN・MD・DFT |
| `simulation-hpc` | 40 | Azure CycleCloud / HB-series VM | 数値シミュ・デジタルツイン |
| `multimodal` | 19 | AML + AOAI | 画像＋テキスト＋センサ融合 (VLM 等) |
| `classical-ml-stats` | 67 | AML CPU / Container Apps | 統計・古典 ML・因果推論 |

**`foundation-model-science` の Foundry モデル対応**（18 件の内訳）:

| モデル | 件数 | ドメイン | 主な使い所 |
|---|---:|---|---|
| **MatterGen** | 4 | 材料科学（結晶生成） | 目的物性を条件に新規無機結晶を生成 |
| **MatterSim** | 5 | 材料科学（物性シミュ） | 0–5000 K・10⁷ atm の原子間相互作用、DFT 代替 |
| **TamGen** | 5 | 創薬（生成化学） | 標的タンパク質構造を条件にリガンド生成 |
| **BioEmu** | 2 | 構造生物学 | タンパク質の多構造アンサンブル予測 |
| **Aurora** | 2 | 地球科学・気象 | 大気・海洋・大気汚染予測、NWP の最大 5,000 倍高速 |

**分類ルール**（新規クイックスタート作成時）:
1. `foundation-model-science` を最優先で検討する。5 モデルのいずれかで直接扱える課題なら、他カテゴリではなく本カテゴリを選ぶ。
2. 各シナリオのディレクトリ名は `<category>-<foundry_model|scenario>` 形式（例：`01-foundation-model-science-mattergen`、`02-llm-rag-scholar-copilot`）。
3. カテゴリと Foundry モデルの厳密な定義は `docs/source/projects-classified.json` の実データを参照。

---

## デプロイ手段

以下の 3 つを併用する。どれを採用したかを各シナリオの README とディレクトリ名（`bicep/` / `azd/` / `cli/`）で明示する。

- **Bicep**（`az deployment group create` / `azd up`）
- **Azure CLI スクリプト**（`az` コマンド中心。最も初心者向け）
- **Azure Developer CLI**（`azd` テンプレート）

ARM テンプレートは新規作成しない。Terraform は使わない。

---

## README テンプレート（各クイックスタート直下）

README には次の 5 項目のみ載せる。**詳細手順は `steps/` に分離**する。

1. **概要／このシナリオで学べること**
2. **前提条件**（サブスクリプション、権限、ローカルツール）
3. **所要時間の目安**
4. **想定コスト**（1 時間あたり / 完走時 / 対象リージョン）
5. **次のステップ**（関連クイックスタートへのリンク）

冒頭に必ず次のコスト警告を入れる：

```markdown
> [!WARNING]
> このシナリオを停止し忘れると 1 日あたり約 ¥XXX 課金されます。
> 使用後は必ず `steps/99-cleanup.md` を実施してください。
```

Qiita 記法（`:::note`）は使わず、GitHub Flavored Markdown のアラート（`> [!NOTE]` / `> [!WARNING]` / `> [!TIP]`）を使う。

---

## コード規約

### 命名

- **リソース**: `<type>-<scenario>-<seq>` の短縮版（例：`vm-mattergen-01`, `aml-scholar-copilot-01`）
- **リソースグループ**: `rg-spread1000-<scenario>-<yourname>`（衝突回避のためユーザー名を入れる）
- 環境（dev/prod）とリージョンはリソース名ではなく**タグ**で管理

### タグ（必須）

すべてのリソースに次を付与する。研究費の課金追跡に必須。

```
project  = spread1000
field    = life-pharma-science  # 分野スラッグ（10分野のいずれか）
category = foundation-model-science  # AI手法カテゴリ（13カテゴリのいずれか）
scenario = mattergen             # シナリオ名
owner    = <email or alias>      # 課金追跡
```

### リージョン

- 既定：`japaneast`
- GPU が無い場合：`eastus` にフォールバック（README に明記）
- リージョンは**必ず変数化**し、ユーザーが 1 箇所を変えれば切り替わるようにする

### Bicep

- **1 シナリオ = 1 `main.bicep`** を原則にする（初心者は 1 ファイルの方が読みやすい）
- モジュール分割は**大規模なもの（HPC / AKS など）のみ**
- 常に `--what-if` / `az deployment ... validate` を README に含める

### Azure CLI スクリプト

必ず冒頭に「変更するのはここだけ」ブロックを置く。コピペで即動作させるため。

```bash
# ===== 変更するのはここだけ =====
RG="rg-spread1000-mattergen-$(whoami)"
LOCATION="japaneast"
# ================================
```

- 出力は `--output table` / `--query` で見やすくする
- シナリオ配下に `.env.example` を置き、`RG`, `LOCATION` などを一元管理

---

## Copilot が守るべき事項

新規シナリオ・改修時、次を**必ず**満たす：

1. **課金停止**：`steps/99-cleanup.md` を必ず作成し、`az group delete` などで完全削除できるようにする
2. **秘密情報を埋め込まない**：サブスクリプション ID、テナント ID、SSH 秘密鍵、SAS トークン、接続文字列、API キー等をコード・ドキュメントに書かない。プレースホルダまたは `az login` / Managed Identity / Key Vault 参照を使う
3. **GPU クォータ／リージョン制約を事前案内**：`az vm list-usage --location <region>` などのチェックコマンドを `steps/01-prerequisites.md` に含める
4. **コストの目安を明記**：README に 1 時間あたり・想定完走時のコストを必ず記載
5. **一次情報を参照**：仕様確認は `microsoft-learn` MCP（`microsoft_docs_search` / `microsoft_docs_fetch`）を優先利用
6. **CLI 出力の可読性**：`--output table` / `--query` を活用
7. **デプロイ前検証**：Bicep は `--what-if` / `az deployment ... validate` を README とスクリプトに含める

---

## ドキュメント言語

- **日本語のみ**
- コード内コメント・変数名は英語でよい（技術用語の翻訳で混乱させない）
- Markdown は **GitHub Flavored Markdown**（`> [!NOTE]` 等のアラートを使う）
