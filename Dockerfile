# Sử dụng base image CUDA 12.4 Runtime trên nền Ubuntu 22.04 LTS
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# Ngăn prompt tương tác khi apt-get cài gói
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cài đặt Python và các thư viện xử lý âm thanh tầng hệ điều hành
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập Python 3.11 làm mặc định
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Thiết lập user không phải root (UID 1000) chuẩn cho Linux/Kubernetes
RUN useradd -m -u 1000 appuser

# Tạo thư mục làm việc và cấp quyền sở hữu
WORKDIR /app
RUN mkdir -p /app/cache /app/models && chown -R appuser:appuser /app

# Đặt biến môi trường Cache trỏ về thư mục đã cấp quyền
ENV HF_HOME=/app/cache
ENV TRANSFORMERS_CACHE=/app/cache

# Cài đặt PyTorch hỗ trợ CUDA 12.8/12.4 và các dependencies cố định
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128 && \
    pip install --no-cache-dir "transformers==4.57.6" && \
    pip install --no-cache-dir "vieneu[cuda]" fastapi uvicorn pydantic soundfile requests

# Chuyển quyền thực thi sang appuser
USER appuser

# Copy mã nguồn dự án vào container
COPY --chown=appuser:appuser . /app

# Khai báo cổng phục vụ
EXPOSE 7865

# Khởi chạy server
CMD ["python", "app.py"]