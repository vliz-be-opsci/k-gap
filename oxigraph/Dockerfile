FROM ghcr.io/oxigraph/oxigraph:latest

# Install curl for the health check script
# The oxigraph image is based on debian:bookworm-slim
USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh

# Healthcheck configuration
# Defaults: start-period=2s, interval=5s, timeout=3s, retries=3
HEALTHCHECK --start-period=2s --interval=5s --timeout=3s --retries=3 CMD /kgap/healthy.sh

# Oxigraph serves data from --location; bind on all interfaces
CMD ["serve", "--location", "/data", "--bind", "0.0.0.0:7878"]
