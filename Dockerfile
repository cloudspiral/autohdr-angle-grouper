FROM python:3.11-slim@sha256:78b39ef14d8e2b4d71f8dc304f1328c37df95fe0ef99477c2ae6bd3d03784553

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

COPY requirements.lock .
RUN python -m pip install --no-cache-dir --requirement requirements.lock

COPY autohdr_eval ./autohdr_eval
COPY configs ./configs
COPY solution.py .

CMD ["python", "solution.py"]
