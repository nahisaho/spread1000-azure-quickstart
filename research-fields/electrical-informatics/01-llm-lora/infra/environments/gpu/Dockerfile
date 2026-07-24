# Dockerfile for spread-lora-gpu AML custom environment
# Base: MCR openmpi5.0-cuda12.4-ubuntu22.04 (2026-07-15 release)
FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1

WORKDIR /app

COPY requirements-gpu.lock ./requirements-gpu.lock

# Install Python dependencies with hash verification
RUN pip install --no-cache-dir --require-hashes -r requirements-gpu.lock

# AML expects this label for custom environments
LABEL maintainer="SPReAD-1000 E-1 LLM LoRA"
