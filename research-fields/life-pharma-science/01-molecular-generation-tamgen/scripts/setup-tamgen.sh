#!/usr/bin/env bash
#
# TamGen セットアップスクリプト
# ------------------------------
# Azure ML Compute Instance のターミナルで実行してください。
# 実行時間: 30〜50 分 (conda env 構築 + 約 3.1 GB の重み DL)
#
# 実行方法 (Compute Instance のターミナル内で):
#
#   1) まず本リポジトリを clone:
#        git clone --branch main --depth 1 \
#          https://github.com/nahisaho/spread1000-azure-quickstart.git
#
#   2) 本スクリプトを目視で確認:
#        less spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh
#
#   3) 実行:
#        bash spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh
#
# セキュリティ: curl | bash は使わないでください。改ざん時に検知できません。
#
set -euo pipefail

# --- 変数 (pinned) ----------------------------------------------------
WORK_DIR="${HOME}/TamGen"
CONDA_ENV="TamGen"

# microsoft/TamGen 上流をピン留め (2024-09 時点の main HEAD)
TAMGEN_REPO="https://github.com/microsoft/TamGen.git"
TAMGEN_COMMIT="9f49e6ce"   # ← アップストリーム更新時は README の対応表を参照して更新すること
# 期待する完全な SHA (rev-parse で照合)。9f49e6ce のフル SHA。
TAMGEN_COMMIT_FULL="9f49e6ce"  # 短縮 SHA でも rev-parse で解決し比較する

# Zenodo の重み (SHA-256 相当は Zenodo が MD5 のみ公開しているため MD5 で検証)
ZENODO_RECORD="13751391"
CKPT_URL="https://zenodo.org/records/${ZENODO_RECORD}/files/checkpoints.zip"
GPT_URL="https://zenodo.org/records/${ZENODO_RECORD}/files/gpt_model.zip"
CKPT_MD5="5815d681256eabaf62fb3df0ef3dfb0e"     # 2.34 GB
GPT_MD5="17e7182c88be61d671c6b88423534586"      # 786 MB

# --- 事前チェック ------------------------------------------------------
echo "==== [pre-check] GPU の存在確認 ===="
if ! command -v nvidia-smi &>/dev/null; then
  echo "❌ nvidia-smi が見つかりません。GPU コンピュート上で実行しているか確認してください。"
  exit 1
fi
nvidia-smi | head -20

echo ""
echo "==== [pre-check] conda の存在確認 ===="
if ! command -v conda &>/dev/null; then
  echo "❌ conda が見つかりません。Azure ML Compute Instance の既定環境で実行してください。"
  exit 1
fi

# --- 1. リポジトリ取得 (pinned commit) --------------------------------
echo ""
if [[ ! -d "${WORK_DIR}" ]]; then
  echo "==== [1/5] microsoft/TamGen をピン留め commit で clone ===="
  git clone "${TAMGEN_REPO}" "${WORK_DIR}"
  (cd "${WORK_DIR}" && git checkout "${TAMGEN_COMMIT}")
else
  echo "==== [1/5] ${WORK_DIR} は既に存在。commit を検証 ===="
  cd "${WORK_DIR}"
  CURRENT_SHA=$(git rev-parse HEAD)
  EXPECTED_SHA=$(git rev-parse "${TAMGEN_COMMIT}^{commit}" 2>/dev/null || echo "")
  if [[ -z "${EXPECTED_SHA}" ]]; then
    echo " ⚠ 期待 commit ${TAMGEN_COMMIT} をローカルで解決できません。fetch します。"
    git fetch --all --tags
    EXPECTED_SHA=$(git rev-parse "${TAMGEN_COMMIT}^{commit}")
  fi
  if [[ "${CURRENT_SHA}" != "${EXPECTED_SHA}" ]]; then
    echo " ✋ 現在の HEAD (${CURRENT_SHA:0:12}) がピン留め commit (${EXPECTED_SHA:0:12}) と異なります。checkout します。"
    git fetch --all --tags
    git checkout "${EXPECTED_SHA}"
  else
    echo " ✅ ピン留め commit ${EXPECTED_SHA:0:12} に一致"
  fi
  cd - >/dev/null
fi
cd "${WORK_DIR}"

# --- 2. conda 環境 ----------------------------------------------------
echo ""
echo "==== [2/5] conda 環境 (${CONDA_ENV}) 作成 ===="
source "$(conda info --base)/etc/profile.d/conda.sh"
if conda env list | grep -q "^${CONDA_ENV}\s"; then
  echo "conda env '${CONDA_ENV}' は既に存在します。スキップ。"
else
  conda create -n "${CONDA_ENV}" python=3.9 -y
fi
conda activate "${CONDA_ENV}"

# --- 3. 依存パッケージ (非対話モードで) --------------------------------
echo ""
echo "==== [3/5] 上流の setup_env.sh を非対話モードで実行 (15-25 分) ===="
# 上流の setup_env.sh は 'conda install ... -y' を付けていないため、
# CONDA_ALWAYS_YES で確認プロンプトを自動 yes に。
CONDA_ALWAYS_YES=true bash setup_env.sh

# --- 4. 重み DL + MD5 検証 --------------------------------------------
echo ""
echo "==== [4/5] 事前学習済み重みを Zenodo からダウンロード + 検証 ===="

download_and_verify() {
  local url="$1" expected_md5="$2" out="$3"
  if [[ -f "${out}" ]]; then
    echo "  ${out} は既に存在。MD5 検証..."
  else
    echo "  ${out} をダウンロード..."
    curl -fL --retry 3 --continue-at - -o "${out}" "${url}"
  fi
  local actual_md5
  actual_md5=$(md5sum "${out}" | awk '{print $1}')
  if [[ "${actual_md5}" != "${expected_md5}" ]]; then
    echo "  ❌ MD5 不一致: expected=${expected_md5} actual=${actual_md5}"
    echo "     アーカイブは信頼できません。削除してください: rm ${out}"
    exit 1
  fi
  echo "  ✅ MD5 OK: ${actual_md5}"
}

# 両方のチェックポイントが揃っているか確認 (上流 example_inference.sh は crossdocked_model を使う)
if [[ ! -f "checkpoints/crossdock_pdb_A10/checkpoint_best.pt" \
   || ! -f "checkpoints/crossdocked_model/checkpoint_best.pt" ]]; then
  download_and_verify "${CKPT_URL}" "${CKPT_MD5}" "/tmp/checkpoints.zip"
  unzip -oq /tmp/checkpoints.zip -d .
  rm /tmp/checkpoints.zip
else
  echo "checkpoints/ 両方のモデルが揃っています。スキップ。"
fi

if [[ ! -f "gpt_model/checkpoint_best.pt" ]]; then
  download_and_verify "${GPT_URL}" "${GPT_MD5}" "/tmp/gpt_model.zip"
  unzip -oq /tmp/gpt_model.zip -d .
  rm /tmp/gpt_model.zip
else
  echo "gpt_model/ は既に存在。スキップ。"
fi

# --- 5. インストール確認 (CUDA が使えなければ非ゼロで exit) -----------
echo ""
echo "==== [5/5] インストール確認 ===="
python - <<'PY' || { echo "❌ CUDA 動作確認に失敗しました。docs/troubleshooting.md を参照。"; exit 1; }
import sys, torch
print(f"Python           : {sys.version.split()[0]}")
print(f"PyTorch          : {torch.__version__}")
print(f"CUDA available   : {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    sys.exit(1)
print(f"CUDA device      : {torch.cuda.get_device_name(0)}")
print(f"CUDA capability  : {torch.cuda.get_device_capability(0)}")
# 実際に GPU テンソル演算が通ることを確認
x = torch.randn(64, 64, device="cuda")
y = (x @ x.T).sum().item()
print(f"GPU tensor op OK : sum={y:.2f}")
PY

# --- ipykernel 登録 (Jupyter からこの conda env を選べるように) ------
python -m ipykernel install --user --name tamgen --display-name "Python 3.9 (TamGen)" >/dev/null

echo ""
echo "==================================================================="
echo " ✅ TamGen セットアップ完了"
echo "==================================================================="
echo ""
echo " 次のコマンドで PDB ベースの分子生成を試す (最短 10-30 分):"
echo "   bash ~/spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/run-inference.sh 3wze"
echo ""
echo " Notebook で対話的に試す場合:"
echo "   Azure ML Studio → ノートブック → ${WORK_DIR}/interctive_decode.ipynb"
echo "   (注: 上流ファイル名は 'inter*ct*ive' と誤字あり)"
echo ""

