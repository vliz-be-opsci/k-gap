# k-gap
Knowledge Graph Analysis Platform



## intro
todo general statements about the ambition and pupose of this
its focus on microservices
and its relation to sembench (as the py package that combines things)

## build your own
todo commands to build docker images locally

## start up
```bash
$ cp dotenv-example .env
$ docker compose up
```

# published docker images from this repo

todo list available images & purpose

## kgap-jupyter
## kgap-graphdb
## kgap-sembench
## kgap-ldes-consumer

LDES (Linked Data Event Streams) consumer service that wraps [ldes2sparql](https://github.com/rdf-connect/ldes2sparql) to harvest multiple LDES feeds. See [ldes-consumer/README.md](ldes-consumer/README.md) for details.

## no longer: kgap-ingest 
todo follow up on latest idea to redo this as py-sync-files-to-store by itself, and then re-wrap it under the sembench as a recurring action to execute
