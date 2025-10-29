FROM ghcr.io/rdf-connect/ldes2sparql:latest

# Copy our custom entrypoint and spawner
COPY ./kgap/entrypoint.sh /kgap/entrypoint.sh
COPY ./kgap/spawn_instances.js /kgap/spawn_instances.js

RUN chmod +x /kgap/entrypoint.sh

# Override the entrypoint
ENTRYPOINT ["/kgap/entrypoint.sh"]
