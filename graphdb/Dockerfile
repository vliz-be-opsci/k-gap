FROM ontotext/graphdb:10.0.2

RUN mkdir -p /root/graphdb-import/data
WORKDIR /root/graphdb-import/data

# ensure we can use envsubst on the underlying alpine image 
RUN apk update && apk add gettext 

COPY ./kgap /kgap
ENTRYPOINT [ "/kgap/rundb.sh" ] 