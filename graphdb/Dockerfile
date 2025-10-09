FROM ontotext/graphdb:10.4.4

COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh

# ensure we can use envsubst on the underlying alpine image 
RUN apk update && apk add gettext 

RUN mkdir -p /root/graphdb-import/data
WORKDIR /root/graphdb-import/data

HEALTHCHECK --start-period=30s --interval=5s --timeout=3s --retries=3 CMD /kgap/healthy.sh

ENTRYPOINT [ "/kgap/entrypoint-wrap.sh" ] 