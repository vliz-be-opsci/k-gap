FROM apache/jena-fuseki:4.10.0

USER root

COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh

# ensure we can use envsubst on the underlying image
RUN apt-get update && apt-get install -y gettext-base curl && rm -rf /var/lib/apt/lists/*

# Healthcheck configuration
# Fuseki starts faster than GraphDB; adjust start-period if needed
HEALTHCHECK --start-period=5s --interval=5s --timeout=3s --retries=3 CMD /kgap/healthy.sh

USER fuseki

ENTRYPOINT ["/kgap/entrypoint-wrap.sh"]
