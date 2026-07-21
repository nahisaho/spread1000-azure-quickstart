#!/usr/bin/env bash
#
# ESMFold セットアップスクリプト
# Azure ML Compute Instance の Jupyter ターミナル (Ubuntu 20.04, conda 済) 用
#
# 動作内容:
#   1. conda env 'esmfold' (Python 3.10) を作成
#   2. PyTorch 2.3.0 + CUDA 12.1 + transformers/accelerate インストール
#   3. HuggingFace キャッシュを ~/cloudfiles/hf_cache (永続領域) に設定
#   4. facebook/esmfold_v1 (8.44 GB) を事前ダウンロード
#   5. ipykernel に 'Python 3.10 (esmfold)' として登録
#
# 使い方 (Compute Instance のターミナルで実行):
#   cd ~/spread1000-azure-quickstart/research-fields/life-pharma-science/02-protein-structure-esmfold
#   bash scripts/setup-esmfold.sh
#
# 実行時間: 約 10-15 分 (ダウンロード時間依存)
#
set -euo pipefail

# --- 変数 ---------------------------------------------------------------
CONDA_ENV="esmfold"
PY_VERSION="3.10"
HF_CACHE="${HOME}/cloudfiles/hf_cache"
MODEL_ID="facebook/esmfold_v1"

# --- 事前チェック ------------------------------------------------------
echo "==== [0/5] 事前チェック ===="
if ! command -v conda >/dev/null 2>&1; then
  echo "❌ conda が見つかりません。Azure ML Compute Instance の既定環境で実行してください。"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "❌ nvidia-smi が見つかりません。GPU 付き Compute Instance で実行してください。"
  exit 1
fi
nvidia-smi -L

if [[ ! -d "${HOME}/cloudfiles" ]]; then
  echo "⚠️  ${HOME}/cloudfiles が存在しません。Compute Instance の Workspace 共有 Storage が"
  echo "   マウントされていない可能性があります。HF_HOME はローカルディスクに設定します。"
  HF_CACHE="${HOME}/.cache/huggingface"
fi

# --- 1. conda 環境 -----------------------------------------------------
echo ""
echo "==== [1/5] conda 環境 (${CONDA_ENV}) 作成 ===="
source "$(conda info --base)/etc/profile.d/conda.sh"
if conda env list | grep -qE "^${CONDA_ENV}\s"; then
  echo "conda env '${CONDA_ENV}' は既に存在します。スキップ。"
else
  conda create -n "${CONDA_ENV}" python="${PY_VERSION}" -y
fi
conda activate "${CONDA_ENV}"
python --version

# --- 2. PyTorch + transformers -----------------------------------------
echo ""
echo "==== [2/5] PyTorch 2.6.0 (CUDA 12.4) をインストール ===="
# NOTE: transformers 4.47+ は CVE-2025-32434 対策として .bin 重みのロードに
# torch>=2.6 を要求する。ESMFold は pytorch_model.bin のみ配布のため必須。
# PyTorch 2.6.0 は cu121 wheel を提供しない (cu118 / cu124 / cu126 のみ)。
# Azure ML Compute Instance の GPU ドライバは NVIDIA 550+ (CUDA 12.4 相当) 以上のため cu124 を採用。
pip install --quiet --upgrade pip
pip install --quiet \
  torch==2.6.0 torchvision==0.21.0 \
  --index-url https://download.pytorch.org/whl/cu124

echo ""
echo "==== [3/5] transformers, accelerate, 可視化ライブラリをインストール ===="
# transformers はテスト済み範囲でピン留め (4.46–4.57 で動作確認)
pip install --quiet \
  "transformers>=4.46,<4.58" \
  "accelerate>=0.30" \
  "biopython>=1.83" \
  "py3Dmol>=2.0" \
  "matplotlib>=3.8" \
  "pandas>=2.0" \
  "ipykernel>=6.29" \
  "hf_transfer>=0.1" \
  "huggingface_hub>=0.24"

# --- 3. HuggingFace キャッシュ設定 ---------------------------------------
echo ""
echo "==== [4/5] HuggingFace キャッシュ設定 (${HF_CACHE}) ===="
mkdir -p "${HF_CACHE}"

# .bashrc に環境変数を永続設定 (既存の設定を綺麗に置き換える)
BASHRC="${HOME}/.bashrc"
MARKER_BEGIN="# BEGIN esmfold-quickstart HF settings"
MARKER_END="# END esmfold-quickstart HF settings"
if [[ -f "${BASHRC}" ]]; then
  # 既存ブロックを削除 (安全: 完全一致マーカーで囲まれた範囲のみ)
  sed -i "/^${MARKER_BEGIN}$/,/^${MARKER_END}$/d" "${BASHRC}"
fi
{
  echo ""
  echo "${MARKER_BEGIN}"
  echo "export HF_HOME=${HF_CACHE}"
  echo "export HF_HUB_ENABLE_HF_TRANSFER=1"
  echo "export HF_HUB_DOWNLOAD_TIMEOUT=600"
  echo "${MARKER_END}"
} >> "${BASHRC}"
echo "✅ .bashrc に HF_HOME=${HF_CACHE} を追記 (既存ブロックがあれば上書き)"
export HF_HOME="${HF_CACHE}"
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DOWNLOAD_TIMEOUT=600

# --- 4. facebook/esmfold_v1 の事前ダウンロード --------------------------
echo ""
echo "==== [5/5] ${MODEL_ID} を事前ダウンロード (約 8.44 GB) ===="
# NOTE: cache_dir を渡さないことで from_pretrained と同じ ${HF_HOME}/hub/... を使う。
# cache_dir="${HF_HOME}" と指定すると ${HF_HOME}/models--... に置かれ、後段の
# from_pretrained (デフォルト ${HF_HOME}/hub/models--...) と別位置に二重展開される。
python - <<PY
import os
os.environ["HF_HOME"] = "${HF_CACHE}"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import snapshot_download
path = snapshot_download(repo_id="${MODEL_ID}")
print(f"✅ ダウンロード完了: {path}")
PY

# --- 5. ipykernel 登録 --------------------------------------------------
echo ""
echo "==== ipykernel を登録 ===="
python -m ipykernel install --user --name "${CONDA_ENV}" \
  --display-name "Python ${PY_VERSION} (${CONDA_ENV})" >/dev/null
echo "✅ Jupyter で 'Python ${PY_VERSION} (${CONDA_ENV})' カーネルが選択できます"

# --- 6. サニティチェック ------------------------------------------------
echo ""
echo "==== 動作確認 (import + CUDA + モデルロード) ===="
python - <<'PY'
import os, sys, torch
os.environ.setdefault("HF_HOME", os.path.expanduser("~/cloudfiles/hf_cache"))
from transformers import EsmForProteinFolding, AutoTokenizer
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
assert torch.cuda.is_available(), "CUDA が使えません。GPU 付き Compute Instance を確認してください"
print("Loading facebook/esmfold_v1 (キャッシュ済みなら数秒) ...")
_ = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
_ = EsmForProteinFolding.from_pretrained("facebook/esmfold_v1", low_cpu_mem_usage=True)
print("✅ EsmForProteinFolding のロードに成功")
PY

echo ""
echo "==================================================================="
echo " ✅ ESMFold セットアップ完了"
echo "==================================================================="
echo ""
echo " 次のステップ:"
echo "   conda activate esmfold"
echo "   python scripts/run-inference.py \\"
echo "     --input scripts/examples/ubiquitin.fasta \\"
echo "     --output ./output/ \\"
echo "     --half-precision --chunk-size 64"
echo ""
