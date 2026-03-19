FROM ghcr.io/oxigraph/oxigraph:latest

# The upstream image is shell-less, so keep this Dockerfile shell-free.
# This liveness check confirms the CLI binary is executable inside the container.
HEALTHCHECK --start-period=2s --interval=5s --timeout=3s --retries=3 CMD ["oxigraph", "--version"]
ENTRYPOINT [ "/usr/local/bin/oxigraph" ]
# Oxigraph serves data from --location; bind on all interfaces
CMD ["serve", "--location", "/data", "--bind", "0.0.0.0:7878"]
