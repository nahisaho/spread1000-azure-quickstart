#!/usr/bin/env bash
#
# AlphaFold 3 セットアップスクリプト
# Azure ML Compute Instance の Jupyter ターミナル (Ubuntu 22.04, Docker + NVIDIA container toolkit 済み) 用
#
# 動作内容:
#   1. nvidia-smi / /mnt 容量 / Docker のチェック
#   2. AF3 リポジトリを ~/alphafold3 に clone (タグ v3.0.2 を pin)
#   3. Docker イメージ alphafold3:v3.0.2 をビルド (20-40 分、初回のみ)
#   4. /mnt/af3 配下のディレクトリ構造を作成
#   5. fetch_databases.sh で ~630 GB の遺伝子 DB をダウンロード (60-120 分)
#   6. サニティチェック (docker run --help)
#
# 前提:
#   - Compute Instance が Standard_NC40ads_H100_v5 (H100 94GB, 3.5 TiB NVMe)
#     または Standard_NC24ads_A100_v4 (A100 80GB, 960 GiB NVMe)
#   - AF3 モデル重み (af3.bin) は Google から個別に取得済み。このスクリプトは重みには触れない。
#
# 使い方:
#   cd ~/spread1000-azure-quickstart/research-fields/life-pharma-science/03-protein-structure-alphafold3
#   sudo bash scripts/setup-af3.sh
#
# 実行時間: 約 90-150 分 (初回)
#
set -euo pipefail

# --- ユーザー判定 (sudo 実行時 $HOME=/root なので、実ユーザーの HOME を先に解決) ---
if [[ ${EUID} -ne 0 ]]; then
  echo "⚠️  root/sudo で実行されていません。Docker ビルドと /mnt への書き込みで sudo が必要になる可能性があります。"
  echo "   推奨: sudo bash scripts/setup-af3.sh"
  echo "   続行しますか？ [y/N]"
  read -r ANS
  [[ "${ANS,,}" != "y" ]] && exit 1
fi

# 実際のユーザー / ホームを判定 (sudo 実行時 $HOME=/root だが、成果物は非 root ユーザー配下に置く)
REAL_USER="${SUDO_USER:-${USER}}"
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
if [[ -z "${REAL_HOME}" || ! -d "${REAL_HOME}" ]]; then
  echo "❌ ユーザー ${REAL_USER} のホームディレクトリが解決できません。"
  exit 1
fi

# --- 変数 ---------------------------------------------------------------
AF3_REPO_URL="https://github.com/google-deepmind/alphafold3.git"
AF3_TAG="v3.0.2"
AF3_HOME="${REAL_HOME}/alphafold3"
DOCKER_TAG="alphafold3:${AF3_TAG}"
MNT_ROOT="/mnt/af3"
DB_DIR="${MNT_ROOT}/public_databases"
MODEL_DIR="${MNT_ROOT}/models"
INPUT_DIR="${MNT_ROOT}/inputs"
OUTPUT_DIR="${MNT_ROOT}/outputs"
MIN_MNT_GB=700   # DB 630 GB + 作業領域

# --- 事前チェック ------------------------------------------------------
echo "==== [0/6] 事前チェック ===="

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "❌ nvidia-smi が見つかりません。GPU 付き Compute Instance で実行してください。"
  exit 1
fi
nvidia-smi -L

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ docker が見つかりません。Azure ML Compute Instance の DSVM ベースイメージで実行してください。"
  exit 1
fi

# NVIDIA Container Toolkit 動作確認
echo "==== Docker から GPU が見えるか確認..."
if ! docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi >/dev/null 2>&1; then
  echo "❌ docker から GPU が見えません。nvidia-container-toolkit を確認してください。"
  echo "   詳細は docs/troubleshooting.md の該当節を参照。"
  exit 1
fi
echo "✅ Docker + GPU OK"

# /mnt 容量チェック
if [[ ! -d "/mnt" ]]; then
  echo "❌ /mnt ディレクトリが見つかりません。SKU (NC40ads_H100_v5 等) と一時ディスクを確認してください。"
  echo "   参考: NC40ads_H100_v5 は約 3576 GiB, NC24ads_A100_v4 は約 960 GiB の一時 NVMe を /mnt に自動マウントします。"
  echo "   A100 SKU で /mnt が空/未マウントの場合、Azure ML のイメージ設定により /dev/nvme* → /mnt を手動 mount する必要が生じることがあります (lsblk で確認)。"
  exit 1
fi

# /mnt が OS ディスクの一部になっているだけで実際の一時 NVMe がマウントされていない場合の警告
if command -v findmnt >/dev/null 2>&1; then
  MNT_SOURCE=$(findmnt -n -o SOURCE /mnt 2>/dev/null || echo "")
  if [[ -z "${MNT_SOURCE}" ]] || [[ "${MNT_SOURCE}" == /dev/sda* ]] || [[ "${MNT_SOURCE}" == /dev/root* ]]; then
    echo "⚠️  /mnt が独立ボリュームとしてマウントされていない可能性 (source=${MNT_SOURCE:-なし})。"
    echo "    A100 SKU の場合、Azure ML イメージにより /dev/nvme* が未マウントの場合があります。"
    echo "    lsblk で NVMe デバイスを確認し、必要に応じて 'sudo mount /dev/nvme0n1 /mnt' を実行してください。"
    lsblk 2>/dev/null | head -20 || true
  fi
fi
MNT_FREE_GB=$(df -BG --output=avail /mnt | tail -n 1 | awk '{gsub(/[^0-9]/,""); print}')
echo "==== /mnt free: ${MNT_FREE_GB} GB (最低 ${MIN_MNT_GB} GB 必要)"
if [[ "${MNT_FREE_GB}" -lt "${MIN_MNT_GB}" ]]; then
  echo "❌ /mnt の空き容量が ${MIN_MNT_GB} GB 未満です (現在 ${MNT_FREE_GB} GB)。"
  echo "   H100 (NC40ads_H100_v5, 3576 GiB) または A100 80GB (NC24ads_A100_v4, 960 GiB) を使用してください。"
  exit 1
fi
echo "✅ /mnt 容量 OK"

# --- 1. ディレクトリ準備 ------------------------------------------------
echo ""
echo "==== [1/6] /mnt/af3 配下のディレクトリを準備 ===="
mkdir -p "${DB_DIR}" "${MODEL_DIR}" "${INPUT_DIR}" "${OUTPUT_DIR}"
chown -R "${REAL_USER}:${REAL_USER}" "${MNT_ROOT}"
# 重みディレクトリはより厳しく (再配布防止)
chmod 700 "${MODEL_DIR}"
echo "✅ ${MNT_ROOT}/{public_databases,models,inputs,outputs} 作成"

# --- 2. AF3 リポジトリ ------------------------------------------------
echo ""
echo "==== [2/6] AlphaFold 3 リポジトリを clone (tag ${AF3_TAG}) ===="
if [[ -d "${AF3_HOME}/.git" ]]; then
  echo "既存の clone を検出: ${AF3_HOME}"
  sudo -u "${REAL_USER}" -H git -C "${AF3_HOME}" fetch --tags --depth 1
  sudo -u "${REAL_USER}" -H git -C "${AF3_HOME}" checkout "${AF3_TAG}"
else
  sudo -u "${REAL_USER}" -H git clone --depth 1 --branch "${AF3_TAG}" "${AF3_REPO_URL}" "${AF3_HOME}"
fi
echo "✅ Repo: ${AF3_HOME} @ ${AF3_TAG}"

# --- 3. Docker イメージビルド ------------------------------------------
echo ""
echo "==== [3/6] Docker イメージ ${DOCKER_TAG} をビルド (20-40 分) ===="
if docker image inspect "${DOCKER_TAG}" >/dev/null 2>&1; then
  echo "既存のイメージを検出: ${DOCKER_TAG}。再ビルドをスキップします。"
  echo "  再ビルドしたい場合: docker rmi ${DOCKER_TAG} してから再実行"
else
  cd "${AF3_HOME}"
  DOCKER_BUILDKIT=1 docker build --progress=plain -t "${DOCKER_TAG}" -f docker/Dockerfile .
fi
echo "✅ Docker image: ${DOCKER_TAG}"

# --- 4. データベースダウンロード ---------------------------------------
echo ""
echo "==== [4/6] 遺伝子データベース ~630 GB をダウンロード (60-120 分) ===="
if [[ -f "${DB_DIR}/.fetch_completed" ]]; then
  echo "既存 DB を検出 (${DB_DIR}/.fetch_completed)。ダウンロードをスキップします。"
  echo "  再ダウンロードしたい場合: rm -rf ${DB_DIR}/* してから再実行"
else
  echo "現在の /mnt 空き: $(df -BG /mnt | awk 'NR==2 {print $4}')"
  echo "開始時刻: $(date)"
  sudo -u "${REAL_USER}" -H bash "${AF3_HOME}/fetch_databases.sh" "${DB_DIR}"
  # ダウンロード完了マーカー
  touch "${DB_DIR}/.fetch_completed"
  chown "${REAL_USER}:${REAL_USER}" "${DB_DIR}/.fetch_completed"
  echo "完了時刻: $(date)"
fi

# サイズ確認 (600-700 GB 前後を期待)
DB_SIZE_GB=$(du -sBG "${DB_DIR}" 2>/dev/null | awk '{gsub(/[^0-9]/,"",$1); print $1; exit}')
DB_SIZE_GB="${DB_SIZE_GB:-0}"
echo "==== DB 展開後サイズ: ${DB_SIZE_GB} GB"
if [[ "${DB_SIZE_GB}" -lt 500 ]]; then
  echo "⚠️  DB サイズが 500 GB 未満です (期待: 600-700 GB)。展開が不完全な可能性があります。"
  echo "   ${DB_DIR}/.fetch_completed を削除して再実行を検討してください。"
fi

# --- 5. サニティチェック ------------------------------------------------
echo ""
echo "==== [5/6] AF3 Docker 動作確認 (--help) ===="
docker run --rm --gpus all "${DOCKER_TAG}" \
  python run_alphafold.py --help 2>&1 | head -20 || {
  echo "⚠️  --help がエラー終了しました。Docker イメージまたは JAX/CUDA を確認してください。"
}

# --- 6. モデル重みの存在チェック ---------------------------------------
echo ""
echo "==== [6/6] モデル重み (af3.bin) の配置確認 ===="
if [[ -f "${MODEL_DIR}/af3.bin" ]]; then
  BIN_SIZE=$(stat -c%s "${MODEL_DIR}/af3.bin")
  BIN_SIZE_MB=$((BIN_SIZE / 1024 / 1024))
  echo "✅ ${MODEL_DIR}/af3.bin を検出 (${BIN_SIZE_MB} MB)"
  if [[ "${BIN_SIZE_MB}" -lt 500 || "${BIN_SIZE_MB}" -gt 2000 ]]; then
    echo "⚠️  af3.bin のサイズが想定外です (期待: 約 1 GB)。承認メールの SHA-256 と比較してください。"
  fi
  sha256sum "${MODEL_DIR}/af3.bin"
else
  echo "⚠️  ${MODEL_DIR}/af3.bin がまだ配置されていません。"
  echo "   Google の承認メールから重みをダウンロードし、以下のいずれかで配置してください:"
  echo "     - JupyterLab の Upload 機能で ~/ に置いた後: mv ~/af3.bin ${MODEL_DIR}/"
  echo "     - azcopy でプライベート Blob から: azcopy copy '...?<SAS>' ${MODEL_DIR}/af3.bin"
  echo "   配置後: chmod 600 ${MODEL_DIR}/af3.bin && sha256sum ${MODEL_DIR}/af3.bin"
fi

# --- 完了 ----------------------------------------------------------------
echo ""
echo "==================================================================="
echo " ✅ AlphaFold 3 セットアップ完了"
echo "==================================================================="
echo ""
echo " 構成:"
echo "   AF3 repo         : ${AF3_HOME} @ ${AF3_TAG}"
echo "   Docker image     : ${DOCKER_TAG}"
echo "   Databases        : ${DB_DIR} (${DB_SIZE_GB} GB)"
echo "   Models           : ${MODEL_DIR}"
echo "   Inputs / Outputs : ${INPUT_DIR}  /  ${OUTPUT_DIR}"
echo ""
echo " ⚠️  /mnt は Compute Instance 停止で消えます (一時 NVMe)。"
echo "    停止前に outputs を ~/cloudfiles に退避してください (docs/05-cleanup.md)。"
echo ""
echo " 次のステップ (docs/03-run-af3.md):"
echo "   cp scripts/examples/ubiquitin_monomer.json ${INPUT_DIR}/"
echo "   python scripts/run-inference.py \\"
echo "     --input ${INPUT_DIR}/ubiquitin_monomer.json \\"
echo "     --model-dir ${MODEL_DIR} \\"
echo "     --db-dir ${DB_DIR} \\"
echo "     --output-dir ${OUTPUT_DIR} \\"
echo "     --docker-image ${DOCKER_TAG} \\"
echo "     --jax-cache-dir ${REAL_HOME}/cloudfiles/jax-cache"
echo ""
