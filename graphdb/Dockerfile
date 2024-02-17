FROM ontotext/graphdb:10.0.2

COPY ./kgap /kgap

# ensure we can use envsubst on the underlying alpine image 
RUN apk update && apk add gettext 

RUN mkdir -p /root/graphdb-import/data
WORKDIR /root/graphdb-import/data

ENTRYPOINT [ "/kgap/entrypoint-wrap.sh" ] 