FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

# Install system deps (curl required for healthcheck)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aws-opentelemetry-distro==0.10.1

# Region defaults
ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore

# Copy application code
COPY . .
RUN chown -R bedrock_agentcore:bedrock_agentcore /app

USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ping || exit 1

CMD ["opentelemetry-instrument", "python", "-m", "app"]
