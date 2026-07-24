# GPU environment for E-3 Image-Restoration U-Net
# Base: verified MCR GPU image (OpenMPI 5.0 + CUDA 12.4 + Ubuntu 22.04)
# Tag:  20260715.v1 (do NOT use openmpi5.0-ubuntu22.04:* — does not exist)
FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1

# Copy only the supplementary requirements (torch/torchvision already in base)
COPY requirements-gpu.in /tmp/req/requirements-gpu.in

RUN pip install --no-cache-dir \
        scikit-image==0.24.0 \
        scipy==1.13.1 \
        numpy==1.26.4 \
        matplotlib==3.9.2 \
        torchmetrics==1.4.3 \
    && rm -rf /tmp/req

# Smoke-test: verify key imports succeed
RUN python -c "import torch; import torchmetrics; import skimage; print('env OK')"
