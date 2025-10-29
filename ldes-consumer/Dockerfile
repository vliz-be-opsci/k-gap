FROM debian:bookworm-slim

# Install required tools
# - Docker CLI to spawn ldes2sparql containers
# - git and curl for direct mode
# - inotify-tools for file watching in folder mode
# - bash for the entrypoint script
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg git inotify-tools bash && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Copy wrapper script
COPY ./kgap/entrypoint.sh /kgap/entrypoint.sh
RUN chmod +x /kgap/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/kgap/entrypoint.sh"]
