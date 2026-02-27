---
title: Quick Reference
nav_order: 4
---

# K-GAP Quick Reference

Quick reference guide for common K-GAP operations.

## Quick Start

```bash
# Clone and start
git clone https://github.com/vliz-be-opsci/k-gap.git
cd k-gap
cp dotenv-example .env
mkdir -p ./data ./notebooks
docker compose up -d

# Access
# GraphDB: http://localhost:7200
# Jupyter: http://localhost:8889
# YASGUI:  http://localhost:8080
```

## Docker Commands

### Start/Stop Services

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a specific service
docker compose restart graphdb
docker compose restart jupyter
docker compose restart sembench
docker compose restart ldes-consumer

# View running containers
docker compose ps
```

### Logs

```bash
# Follow all logs
docker compose logs -f

# Specific service logs
docker compose logs -f graphdb
docker compose logs -f jupyter

# LDES feed container logs
docker logs ldes-consumer-{feed-name}
```

### Rebuilding

```bash
# Rebuild all images
make docker-build

# Rebuild specific service
docker compose build graphdb
docker compose build jupyter

# Rebuild and restart
docker compose up -d --build
```

## Configuration Quick Reference

### Environment Variables (.env)

```bash
# Docker Compose
COMPOSE_PROJECT_NAME=kgap

# GraphDB
GDB_REPO=kgap
GDB_JAVA_OPTS="-Xms8g -Xmx16g"

# Sembench
SEMBENCH_CONFIG_PATH=/data/sembench.yaml
SCHEDULER_INTERVAL_SECONDS=86400

# LDES Consumer
LDES_CONFIG_FILE=/data/ldes-feeds.yaml
LOG_LEVEL=INFO
```

### LDES Feeds (data/ldes-feeds.yaml)

```yaml
feeds:
  - name: my-feed
    url: https://example.com/ldes
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 60
```

## SPARQL Queries

### Basic Queries

```sparql
# Count all triples
SELECT (COUNT(*) as ?count)
WHERE { ?s ?p ?o }

# List all types
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?type (COUNT(?s) as ?count)
WHERE { ?s rdf:type ?type }
GROUP BY ?type
ORDER BY DESC(?count)

# List all predicates
SELECT DISTINCT ?p (COUNT(*) as ?count)
WHERE { ?s ?p ?o }
GROUP BY ?p
ORDER BY DESC(?count)
```

### Data Queries

```sparql
# Get entities with labels
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?label
WHERE {
  ?entity rdfs:label ?label .
}
LIMIT 100

# Full-text search
PREFIX luc: <http://www.ontotext.com/owlim/lucene#>
SELECT ?entity ?score
WHERE {
  ?entity luc:searchIndex "marine" ;
          luc:score ?score .
}
ORDER BY DESC(?score)
```

### Updates

```sparql
# Insert data
PREFIX ex: <http://example.org/>
INSERT DATA {
  ex:entity1 ex:property "value" .
}

# Delete data
PREFIX ex: <http://example.org/>
DELETE DATA {
  ex:entity1 ex:property "value" .
}

# Update (delete + insert)
PREFIX ex: <http://example.org/>
DELETE { ?s ex:oldProp ?o }
INSERT { ?s ex:newProp ?o }
WHERE { ?s ex:oldProp ?o }
```

## Jupyter Notebook Commands

### Query GraphDB

```python
from kgap_tools import execute_to_df, GDB

# Using templates
df = execute_to_df('my_query', param1='value')

# Direct SPARQL
sparql = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
result = GDB.query(sparql=sparql)
df = result.to_dataframe()
```

### Working with Data

```python
import pandas as pd

# Read data
df = pd.read_csv('/data/input.csv')

# Process and query
for idx, row in df.iterrows():
    # Query GraphDB based on row data
    results = execute_to_df('template', value=row['column'])
    # Process results

# Write results
df.to_csv('/data/output.csv', index=False)
```

## Common Patterns

### Add LDES Feed

```bash
# 1. Edit config
nano data/ldes-feeds.yaml

# 2. Add feed entry
# feeds:
#   - name: new-feed
#     url: https://example.com/ldes
#     sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
#     polling_interval: 300

# 3. Restart consumer
docker compose restart ldes-consumer
```

### Export Data

```bash
# Export all data to TTL
curl 'http://localhost:7200/repositories/kgap/statements' \
  -H 'Accept: text/turtle' \
  > export.ttl

# Export specific graph
curl 'http://localhost:7200/repositories/kgap/statements?context=%3Chttp://example.org/graph%3E' \
  -H 'Accept: text/turtle' \
  > graph-export.ttl
```

### Import Data

```bash
# Import TTL file
curl -X POST \
  http://localhost:7200/repositories/kgap/statements \
  -H 'Content-Type: text/turtle' \
  --data-binary '@import.ttl'

# Import to named graph
curl -X POST \
  'http://localhost:7200/repositories/kgap/statements?context=%3Chttp://example.org/graph%3E' \
  -H 'Content-Type: text/turtle' \
  --data-binary '@import.ttl'
```

### Clear Repository

```bash
# Clear all data
curl -X DELETE http://localhost:7200/repositories/kgap/statements

# Clear specific graph
curl -X DELETE 'http://localhost:7200/repositories/kgap/statements?context=%3Chttp://example.org/graph%3E'
```

## Troubleshooting

### GraphDB Won't Start

```bash
# Check logs
docker compose logs graphdb

# Common fixes
# 1. Increase memory in .env:
#    GDB_JAVA_OPTS="-Xms16g -Xmx32g"
# 2. Check port 7200 not in use:
#    lsof -i :7200
# 3. Remove and recreate:
#    docker compose down
#    docker volume prune
#    docker compose up -d
```

### Jupyter Can't Connect to GraphDB

```python
# Test connection
import os
from pykg2tbl import KGSource

endpoint = f"{os.getenv('GDB_BASE')}repositories/{os.getenv('GDB_REPO')}"
print(f"Testing: {endpoint}")

try:
    kg = KGSource.build(endpoint)
    result = kg.query("ASK { ?s ?p ?o }")
    print("✓ Connection successful")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### LDES Feed Not Working

```bash
# Check feed container
docker ps | grep ldes-consumer
docker logs ldes-consumer-{feed-name}

# Test feed URL
curl -I {feed-url}

# Check GraphDB endpoint
curl http://localhost:7200/repositories/kgap/statements

# Restart feed
docker stop ldes-consumer-{feed-name}
docker rm ldes-consumer-{feed-name}
docker compose restart ldes-consumer
```

### Out of Memory

```yaml
# Increase limits in docker-compose.yml
services:
  graphdb:
    environment:
      GDB_JAVA_OPTS: "-Xms16g -Xmx32g"
    deploy:
      resources:
        limits:
          memory: 40G
```

## Useful Endpoints

### GraphDB REST API

```bash
# Repository info
curl http://localhost:7200/rest/repositories/kgap

# Repository size
curl http://localhost:7200/rest/repositories/kgap/size

# Namespaces
curl http://localhost:7200/repositories/kgap/namespaces

# Contexts (graphs)
curl http://localhost:7200/repositories/kgap/contexts
```

### Health Checks

```bash
# GraphDB health
curl http://localhost:7200/

# Jupyter health
curl http://localhost:8889/

# Check all services
docker compose ps
```

## File Locations

```
k-gap/
├── data/                    # Shared data volume
│   ├── ldes-feeds.yaml     # LDES configuration
│   ├── sembench.yaml       # Sembench configuration
│   └── *.ttl, *.csv, etc.  # Data files
├── notebooks/              # Jupyter notebooks
│   └── queries/            # SPARQL query templates
├── .env                    # Environment configuration
└── docker-compose.yml      # Service definitions
```

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| GraphDB | 7200 | http://localhost:7200 |
| Jupyter | 8889 | http://localhost:8889 |
| YASGUI  | 8080 | http://localhost:8080 |

## Resource Allocation Defaults

| Service | CPU | Memory |
|---------|-----|--------|
| GraphDB | 4 cores | 8-16GB (configurable) |
| Jupyter | unlimited | unlimited |
| Sembench | unlimited | unlimited |
| LDES Consumer | unlimited | unlimited |

## Links

- [Full Documentation](./index.md)
- [GraphDB Component](./components/graphdb.md)
- [Jupyter Component](./components/jupyter.md)
- [Sembench Component](./components/sembench.md)
- [LDES Consumer](./components/ldes-consumer.md)
- [Advanced Topics](./advanced-topics.md)
- [GitHub Pages Setup](./GITHUB_PAGES.md)
