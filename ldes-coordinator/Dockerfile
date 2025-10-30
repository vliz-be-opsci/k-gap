FROM ghcr.io/rdf-connect/ldes2sparql:latest

# Install docker and jq for container management and JSON parsing
RUN apk update && apk add docker jq

# Copy our custom entrypoint and spawner
COPY ./kgap /kgap

RUN chmod +x /kgap/entrypoint.sh

# Override the entrypoint
ENTRYPOINT ["/kgap/entrypoint.sh"]
