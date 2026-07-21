# 03 — AlphaFold 3 環境構築と推論実行

所要 90〜150 分（初回のみ；Docker ビルド 20〜40 分 + DB ダウンロード 60〜120 分）。
ここでは Compute Instance に接続し、AF3 の Docker イメージ構築、
遺伝子データベース (~630 GB) の準備、モデル重みの安全な配置、
そして最初の推論を実行します。

## 前提

- [`docs/01-prerequisites.md`](01-prerequisites.md) を完了していること
- **AF3 の承認メールを受領し、`af3.bin` をローカル PC に保存済み** であること
- [`docs/02-provision-aml.md`](02-provision-aml.md) で H100 (または A100) Compute Instance が Running 状態

---

## 1. Compute Instance に接続

**方法 A: Azure ML Studio の Jupyter**（初回推奨）
1. [Azure ML Studio](https://ml.azure.com) → 対象 Workspace を選択
2. 左メニュー **Compute** → Compute Instance を選択 → **Jupyter** をクリック
3. ブラウザで JupyterLab が開く

**方法 B: VS Code Remote**（推奨・大量ファイル操作向け）
- VS Code 拡張 **Azure Machine Learning** をインストール
- コマンドパレット → `Azure ML: Connect to Compute Instance`

## 2. `/mnt` の状態確認（重要）

AF3 のデータベース (~630 GB) は Compute Instance の **一時 NVMe (`/mnt`)** に配置します。
OS ディスク (120 GB) では容量不足のため必須です。

```bash
df -h /mnt
```

H100 (`Standard_NC40ads_H100_v5`) は約 **3,576 GiB** の `/mnt` を持つため十分です。
A100 (`Standard_NC24ads_A100_v4`) は約 **960 GiB**（DB 630 GB + 作業領域）で十分です。

> [!WARNING]
> **`/mnt` は一時 NVMe です。Compute Instance を停止 (deallocate) すると全消去されます。**
> 停止する前に、推論結果は必ず `~/cloudfiles/`（永続 Blob）にコピーしてください。
> 詳細は [`docs/05-cleanup.md`](05-cleanup.md)。
>
> 再開時にはこの `setup-af3.sh` を再度実行して DB を再ダウンロードする必要があります（約 60〜120 分）。
> 頻繁に再開する場合の永続化案は [`docs/05-cleanup.md`](05-cleanup.md) の「DB の永続化」節を参照。

## 3. リポジトリ取得とセットアップ

```bash
cd ~
git clone https://github.com/nahisaho/spread1000-azure-quickstart.git
cd spread1000-azure-quickstart/research-fields/life-pharma-science/03-protein-structure-alphafold3

# Docker ビルド + DB ダウンロード (合計 90〜150 分)
sudo bash scripts/setup-af3.sh
```

`setup-af3.sh` は以下を行います：

1. `nvidia-smi` と `/mnt` 容量チェック
2. NVIDIA Container Toolkit の存在確認（Azure ML CI にはプレインストール済み）
3. AF3 リポジトリを `~/alphafold3` にクローン（タグ **v3.0.2** を指定）
4. Docker イメージ `alphafold3:v3.0.2` をビルド（20〜40 分、初回のみ）
5. `/mnt/af3` に以下のディレクトリを作成:
   - `/mnt/af3/public_databases` — 遺伝子 DB (~630 GB)
   - `/mnt/af3/models` — `af3.bin` を配置する場所（後述、手動）
   - `/mnt/af3/inputs` — JSON 入力ファイル
   - `/mnt/af3/outputs` — 予測結果
6. `fetch_databases.sh` で 9 種のデータベースをダウンロード（60〜120 分）
7. 動作テスト用に `docker run --gpus all alphafold3:v3.0.2 --help` を実行

**進捗確認**: 別ターミナルで `watch -n 30 'df -h /mnt; du -sh /mnt/af3/public_databases 2>/dev/null'`

## 4. モデル重み `af3.bin` の配置

> [!IMPORTANT]
> **`af3.bin` は Terms of Use により再配布禁止です。以下のいずれかの方法で安全に配置してください。**
>
> - ❌ **やってはいけないこと**: GitHub / Blob 公開コンテナ / Docker イメージ内 / パブリック URL への配置
> - ❌ **やってはいけないこと**: 個人承認の重みを、機関の共有 Blob 等に配置して他人と共有

**方法 1: JupyterLab のアップロード機能**（お勧め）

1. JupyterLab のファイル ブラウザで `/home/azureuser/` を開く
2. **Upload** ボタン → ローカル PC の `af3.bin` を選択（約 1 GB、5〜15 分）
3. ターミナルで移動:
   ```bash
   mkdir -p /mnt/af3/models
   mv ~/af3.bin /mnt/af3/models/
   chmod 600 /mnt/af3/models/af3.bin
   sha256sum /mnt/af3/models/af3.bin
   ```
4. 承認メールに記載された SHA-256 と一致することを確認

**方法 2: `azcopy` で個人 Blob 経由**（機関承認の場合、アクセス制御された Blob 前提）

事前準備: ローカル PC から `az storage blob upload` 等で af3.bin をプライベート Blob コンテナに配置し、時間限定 SAS を発行しておく。**Compute Instance 上で** 以下を実行:

```bash
# Compute Instance のターミナルで実行
# SAS URL はシェル履歴に残さないよう -s (silent) で読み取る
read -rsp "af3.bin の SAS URL を入力: " AF3_SAS && echo
azcopy copy "${AF3_SAS}" '/mnt/af3/models/af3.bin'
unset AF3_SAS
chmod 600 /mnt/af3/models/af3.bin
sha256sum /mnt/af3/models/af3.bin
```

代替: SAS を使わず、Compute Instance のマネージド ID にストレージアカウントの **Storage Blob Data Reader** を付与し、`azcopy login --identity` してから `azcopy copy 'https://<st>.blob.core.windows.net/<container>/af3.bin' /mnt/af3/models/af3.bin` を使う方法もあります (推奨、資格情報の露出なし)。

方法 2 を使う場合は、Blob コンテナに **プライベート アクセス** を設定し、SAS トークンの有効期限を短く（数時間）してください。

## 5. サンプルで動作確認（ubiquitin monomer）

```bash
# サンプル入力を /mnt/af3/inputs にコピー
cp scripts/examples/ubiquitin_monomer.json /mnt/af3/inputs/

# 推論実行
python scripts/run-inference.py \
  --input /mnt/af3/inputs/ubiquitin_monomer.json \
  --model-dir /mnt/af3/models \
  --db-dir /mnt/af3/public_databases \
  --output-dir /mnt/af3/outputs \
  --docker-image alphafold3:v3.0.2 \
  --jax-cache-dir ~/cloudfiles/jax-cache
```

**期待される出力**（H100 の場合、約 10〜15 分。NIG L40S 300aa 単量体の実測値に基づく参考値。うち MSA 約 8〜12 分、GPU 推論 約 30 秒 + 初回 JAX コンパイル 5〜10 分）：

```
[INFO] Validating input JSON: /mnt/af3/inputs/ubiquitin_monomer.json
[INFO] dialect=alphafold3, version=4, seeds=[42]
[INFO] Verifying model weights at /mnt/af3/models/af3.bin
[INFO] Docker image: alphafold3:v3.0.2
[INFO] Starting AF3 (combined pipeline)...
[INFO] ==> Data pipeline (MSA + templates)...
[INFO] MSA/templates completed in 542s
[INFO] ==> Inference (JAX compile + sample)...
[INFO] JAX compile finished in 384s (cached for next runs)
[INFO] Sample 1/1 completed in 27s
[INFO] Ranking scores: [0.87]
[INFO] Output: /mnt/af3/outputs/ubiquitin_monomer/
```

**出力ファイル**（詳細は [`docs/04-interpret-results.md`](04-interpret-results.md)。ファイル名の先頭にジョブ名がプレフィクスとして付与されます）:

```
/mnt/af3/outputs/ubiquitin_monomer/
├── ubiquitin_monomer_model.cif                            ← トップランク構造（mmCIF）
├── ubiquitin_monomer_confidences.json                     ← 詳細信頼度
├── ubiquitin_monomer_summary_confidences.json             ← サマリ (トップランク)
├── ubiquitin_monomer_data.json                            ← MSA/テンプレート情報
├── ubiquitin_monomer_ranking_scores.csv                   ← サンプル間ランキング
├── TERMS_OF_USE.md                                        ← 出力ライセンス（必ず保持）
├── ubiquitin_monomer_seed-42_sample-0_model.cif           ← 各サンプルの構造
├── ubiquitin_monomer_seed-42_sample-0_confidences.json
├── ubiquitin_monomer_seed-42_sample-0_summary_confidences.json
├── ubiquitin_monomer_seed-42_sample-1_model.cif
...
└── ubiquitin_monomer_seed-42_sample-4_summary_confidences.json
```

## 6. 応用例: タンパク質-リガンド複合体（TetR/tetracycline）

このリポジトリの `scripts/examples/tetr_dimer_tetracycline.json` は **プレースホルダー** です。
公式検証済みの入力は AF3 リポジトリから取得してください:

```bash
# setup-af3.sh 実行後、~/alphafold3 に公式サンプルが揃っている
cp ~/alphafold3/examples/tetr_dimer_tetracycline.json /mnt/af3/inputs/

python scripts/run-inference.py \
  --input /mnt/af3/inputs/tetr_dimer_tetracycline.json \
  --model-dir /mnt/af3/models \
  --db-dir /mnt/af3/public_databases \
  --output-dir /mnt/af3/outputs \
  --docker-image alphafold3:v3.0.2 \
  --jax-cache-dir ~/cloudfiles/jax-cache
```

TetR は 208 残基 × 2 (homodimer) + tetracycline (CCD: `TAC`) の複合体。
H100 で **約 20〜25 分**（MSA 約 15 分、推論 約 1 分、JAX キャッシュ再利用時）。

## 7. MSA と推論を別ステージで実行（応用）

MSA だけ実行して `_data.json` を保存し、後で推論のみ繰り返すことで、
MSAを再実行せず開始でき、**JAX コンパイルキャッシュがある場合は JIT コンパイルも省略**できます。
リガンドやシード違いの試行を短時間で繰り返せます。

> [!IMPORTANT]
> `run-inference.py` は `--stage msa` で `--gpus all` を付けず、`--stage inference` で 630 GB DB volume を mount しません。したがって:
> - **本当に GPU コストを削減する運用**: 別途 **CPU 専用の Azure VM (例: `Standard_D32ds_v5`)** + 同じ DB マウントで MSA を回し、生成された `<job>_data.json` を GPU CI に転送する
> - **同じ H100/A100 CI 上で `--stage msa` を回す運用**: GPU コストは削減できません (CI 起動中は常時課金)。ただし **シード違いを高速に試す** 用途では有効です

```bash
# ステージ 1: MSA のみ（データパイプライン、DB スキャン中心、10〜15 分、GPU 未使用）
python scripts/run-inference.py \
  --input /mnt/af3/inputs/target.json \
  --stage msa \
  --model-dir /mnt/af3/models \
  --db-dir /mnt/af3/public_databases \
  --output-dir /mnt/af3/outputs \
  --docker-image alphafold3:v3.0.2

# ステージ 2: 推論のみ（GPU 集中、H100 約 30 秒 + コンパイル、DB マウント無し）
# 上で作成された <job>_data.json を入力に使う (job 名は入力 JSON の name を正規化した名前)
python scripts/run-inference.py \
  --input /mnt/af3/outputs/target/target_data.json \
  --stage inference \
  --model-dir /mnt/af3/models \
  --db-dir /mnt/af3/public_databases \
  --output-dir /mnt/af3/outputs \
  --docker-image alphafold3:v3.0.2 \
  --jax-cache-dir ~/cloudfiles/jax-cache
# 内部で --force_output_dir=true が付与され、MSA と同じ <job>/ 下に推論結果が追加されます
```

## GPU 別の実測目安

DeepMind 公式ベンチマーク（コンパイル時間・MSA を除く純粋な推論時間）：

| トークン数 | A100 80GB | H100 80GB |
|-----------:|----------:|----------:|
| 1,024 | 62 秒 | 34 秒 |
| 2,048 | 275 秒 | 144 秒 |
| 3,072 | 703 秒 | 367 秒 |
| 4,096 | 1,434 秒 | 774 秒 |
| 5,120 | 2,547 秒 | 1,416 秒 |

出典: [google-deepmind/alphafold3 performance.md](https://github.com/google-deepmind/alphafold3/blob/main/docs/performance.md#accelerator-hardware-requirements)

> [!NOTE]
> **「トークン数」= アミノ酸 + 塩基 + リガンド原子 + イオン の総和**です。
> 単なる残基数ではありません。大きな複合体では想定より早く上限 (5,120) に達します。

> [!IMPORTANT]
> **初回の JAX コンパイルは 5〜10 分かかります**。`--jax-cache-dir` を **永続領域**
> (`~/cloudfiles/jax-cache`) に指定すれば、2 回目以降は数秒で済みます。

## 完了チェック

- [ ] `docker images | grep alphafold3` に `v3.0.2` イメージが表示される
- [ ] `du -sh /mnt/af3/public_databases` が 600 GB 前後
- [ ] `ls /mnt/af3/models/af3.bin` が存在し、SHA-256 が承認メールと一致
- [ ] `ubiquitin_monomer` の推論が正常終了し、`ranking_scores.csv` が生成される
- [ ] `TERMS_OF_USE.md` が出力ディレクトリに含まれている

**次**: [04-interpret-results.md](04-interpret-results.md) — mmCIF, pLDDT, pTM, ipTM の読み方
