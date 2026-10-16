FROM python:3.11-slim AS builder

WORKDIR /app

# Install Poetry.
RUN pip install --no-cache-dir poetry==2.4.1

# Copy dependency files.
COPY pyproject.toml poetry.lock* ./

# Configure poetry to create the virtual environment in the project root (.venv).
RUN poetry config virtualenvs.in-project true \
    && poetry install --only main --no-root

FROM python:3.11-slim AS runner

WORKDIR /app

# Install system libraries required by OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# Copy built virtual environment from the builder stage.
COPY --from=builder /app/.venv /app/.venv

# Copy application source code.
COPY camera_traps/ ./camera_traps/

# Add the virtual environment to PATH.
ENV PATH="/app/.venv/bin:$PATH"

# Expose FastAPI backend port.
EXPOSE 8000

# Run Uvicorn directly as the primary process.
CMD ["uvicorn", "camera_traps.main:app", "--host", "0.0.0.0", "--port", "8000"]