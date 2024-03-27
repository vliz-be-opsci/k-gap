FROM ontotext/graphdb:10.4.4

COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh

# ensure we can use envsubst on the underlying alpine image 
RUN apk update && apk add gettext 

RUN mkdir -p /root/graphdb-import/data
WORKDIR /root/graphdb-import/data

HEALTHCHECK --start-period=1s --interval=0.5s CMD /kgap/healthy.sh

ENTRYPOINT [ "/kgap/entrypoint-wrap.sh" ] 