FROM python:3.10-slim

# Install Docker CLI to spawn ldes2sparql containers
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Copy wrapper scripts
COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh /kgap/*.py

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r /kgap/requirements.txt

# Set the entrypoint
ENTRYPOINT ["/kgap/entrypoint.sh"]
