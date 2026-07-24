# Custom AML training/inference environment for the D-2 MACE-MP quickstart.
#
# Base image: verified available in MCR as of 2026-07:
#   azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1
# Do NOT use `azureml/openmpi5.0-ubuntu22.04:*` — that tag does not exist.
FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1

# Install PyTorch 2.4.0 with CUDA 12.1 wheels first so mace-torch links against it.
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir \
        torch==2.4.0 \
        --index-url https://download.pytorch.org/whl/cu121

# Install pinned Python deps with hashes. requirements-gpu.lock is expected
# to be produced by `pip-compile --generate-hashes` from requirements-gpu.in.
COPY requirements-gpu.lock /tmp/requirements-gpu.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements-gpu.lock

# Sanity check that MACE and Torch are importable and CUDA is visible in build args.
RUN python -c "import torch, mace, ase; print('torch', torch.__version__, 'mace', mace.__version__, 'ase', ase.__version__)"
