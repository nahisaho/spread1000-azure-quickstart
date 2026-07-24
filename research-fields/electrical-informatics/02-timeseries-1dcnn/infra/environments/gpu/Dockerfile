FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:20260715.v1
WORKDIR /opt/app
COPY requirements-gpu.lock /opt/app/requirements-gpu.lock
RUN pip install --no-cache-dir --require-hashes -r /opt/app/requirements-gpu.lock
