FROM redpencil/virtuoso:1.3.2-test

COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh

# Healthcheck configuration
# Virtuoso can take longer to start; increase start-period for large databases
HEALTHCHECK --start-period=10s --interval=10s --timeout=5s --retries=5 CMD /kgap/healthy.sh

ENTRYPOINT ["/kgap/entrypoint-wrap.sh"]
