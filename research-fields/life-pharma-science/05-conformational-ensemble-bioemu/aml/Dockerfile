# BioEmu 1.4.1 CUDA/JAX 実行環境
# base: AML openmpi5.0-cuda12.4-ubuntu22.04 (2026-07-15 immutable tag)
FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    XLA_PYTHON_CLIENT_PREALLOCATE=false \
    HF_HUB_DISABLE_TELEMETRY=1

# Python 3.11+ が base image に含まれる想定 (openmpi5.0-cuda12.4-ubuntu22.04 は 3.10 の場合があるため確認)。
# bioemu 1.4.1 は Python >=3.11 を要求。base image が 3.10 なら 3.11 を追加する。
RUN if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"; then \
      echo "Python 3.11+ OK"; \
    else \
      apt-get update && \
      apt-get install -y --no-install-recommends software-properties-common && \
      add-apt-repository -y ppa:deadsnakes/ppa && \
      apt-get install -y --no-install-recommends python3.11 python3.11-venv python3.11-distutils && \
      update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 100 && \
      update-alternatives --install /usr/bin/python python /usr/bin/python3.11 100 && \
      curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 && \
      rm -rf /var/lib/apt/lists/*; \
    fi

# NOTE: bioemu 1.4.1 pins torch to 2.6.x for the CUDA 12.4 wheels shipped by
# PyTorch. Do not upgrade torch here — 2.13.0+cu130 wheels are NOT compatible
# with this base image's cuDNN/CUDA runtime and will fail with symbol errors
# at import time. If a future bioemu release relaxes the pin, re-verify.
RUN python3 -m pip install --upgrade pip setuptools wheel \
 && python3 -m pip install \
      "torch>=2.6,<2.7" \
      "bioemu[cuda]==1.4.1" \
      "scikit-learn>=1.6,<2" \
      "matplotlib>=3.10,<4"

# smoke test (import のみ; モデルダウンロードは実行時)
RUN python3 -c "import bioemu, torch, jax; print('bioemu', bioemu.__version__, 'torch', torch.__version__, 'jax', jax.__version__)"
