# infra/environments/gpu/Dockerfile
# Verified MCR GPU base image (CUDA 12.4, OpenMPI 5.0, Ubuntu 22.04)
# Ref: https://mcr.microsoft.com/en-us/product/azureml/openmpi5.0-cuda12.4-ubuntu22.04
FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1

WORKDIR /opt/microseg

# Copy the hash-pinned lockfile (generate with: pip-compile --generate-hashes)
COPY requirements-gpu.lock /opt/microseg/

# Install all packages reproducibly from the lockfile
RUN pip install --no-cache-dir --require-hashes -r /opt/microseg/requirements-gpu.lock

# Copy source code
COPY src/ /opt/microseg/src/

ENV PYTHONPATH="/opt/microseg:${PYTHONPATH:-}"
