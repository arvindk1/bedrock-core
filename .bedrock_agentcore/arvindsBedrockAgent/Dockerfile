FROM python:3.13-slim-bookworm
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    AWS_REGION=us-east-1 \
    AWS_DEFAULT_REGION=us-east-1

# Install system dependencies needed by scipy/numpy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        gfortran \
        libopenblas-dev \
        pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Copy project files and install
COPY . .
RUN pip install --no-cache-dir . && \
    python -c "from strands_agents import Agent; print('strands_agents OK')" && \
    python -c "import scipy; print('scipy OK')" && \
    python -c "import pandas; print('pandas OK')"

RUN pip install --no-cache-dir aws-opentelemetry-distro==0.12.2

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
RUN chown -R bedrock_agentcore:bedrock_agentcore /app
USER bedrock_agentcore

EXPOSE 9000
EXPOSE 8000
EXPOSE 8080

CMD ["opentelemetry-instrument", "python", "app.py"]
