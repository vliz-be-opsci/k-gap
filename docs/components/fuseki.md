---
title: Apache Jena Fuseki Component
parent: Components
nav_order: 6
---

# Apache Jena Fuseki Component

Apache Jena Fuseki is a SPARQL server that provides SPARQL 1.1 query and update endpoints over persistent TDB2 datasets. It can serve as an alternative to GraphDB in the K-GAP stack.

## Overview

Fuseki exposes each dataset as a named endpoint (e.g. `/kgap/sparql`). The K-GAP wrapper automatically creates a TDB2 persistent dataset on startup using environment-variable substitution — comparable to how GraphDB creates its repository.

- SPARQL 1.1 Query and Update support
- SPARQL Graph Store HTTP Protocol
- Named dataset per project (auto-created on startup)
- Persistent TDB2 storage
- Web admin UI at `/$/`

**Base Image**: [`apache/jena-fuseki`](https://jena.apache.org/documentation/fuseki2/fuseki-docker.html)  
**Exposed Port**: 3030 (HTTP)  
**Container Name**: `test_kgap_fuseki` (in test setup)  

## Architecture

```
┌──────────────────────────────────────────────┐
│          Fuseki Container                     │
├──────────────────────────────────────────────┤
│                                               │
│  entrypoint-wrap.sh                          │
│       │                                       │
│       ├─▶ Check/Create dataset config        │
│       │   - template-dataset-config.ttl      │
│       │   - Apply environment vars (envsubst) │
│       │   - Write to /fuseki/configuration/  │
│       │                                       │
│       └─▶ Start Fuseki                       │
│           - SPARQL endpoint per dataset       │
│           - TDB2 persistent storage           │
│           - Admin UI at /$/                   │
│                                               │
│  Volumes:                                     │
│  - ./data/fuseki → /fuseki/databases         │
│                                               │
└──────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

These variables are defined in the repository root `.env` file (copy `dotenv-example` to `.env` and adjust values).

| Variable | Default | Description |
|----------|---------|-------------|
| `FUSEKI_DATASET` | `kgap` | Dataset (repository) name |
| `FUSEKI_ADMIN_PASSWORD` | `admin` | Password for the Fuseki admin UI |

### Dataset Configuration

The dataset is automatically created on first startup using the template at `fuseki/kgap/template-dataset-config.ttl`. The template is processed with environment variable substitution:

```turtle
:service a fuseki:Service ;
    fuseki:name "${FUSEKI_DATASET}" ;
    ...

:dataset rdf:type tdb2:DatasetTDB2 ;
    tdb2:location "/fuseki/databases/${FUSEKI_DATASET}" ;
```

The configuration file is written to `/fuseki/configuration/${FUSEKI_DATASET}.ttl` before Fuseki starts.

### Health Check

The health check queries the dataset-specific SPARQL endpoint with a minimal `ASK {}` query, confirming both the server and the dataset are ready:

```yaml
healthcheck:
  start_period: 5s
  interval: 5s
  timeout: 3s
  retries: 3
```

## SPARQL Endpoints

After startup (with `FUSEKI_DATASET=kgap`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `http://localhost:3030/kgap/sparql` | GET / POST | SPARQL 1.1 Query |
| `http://localhost:3030/kgap/query` | GET / POST | SPARQL 1.1 Query (alias) |
| `http://localhost:3030/kgap/update` | POST | SPARQL 1.1 Update |
| `http://localhost:3030/kgap/get` | GET | Graph Store Protocol (read) |
| `http://localhost:3030/kgap/data` | GET / POST / PUT / DELETE | Graph Store Protocol (read/write) |
| `http://localhost:3030/kgap/upload` | POST | File upload |
| `http://localhost:3030/$/` | GET | Admin UI |

## Usage

### Starting with Fuseki

```bash
# Copy and configure environment
cp dotenv-example .env
# Edit .env if needed (FUSEKI_DATASET defaults to 'kgap')

# Create data directories
mkdir -p ./data/fuseki ./notebooks

# Start the full K-GAP stack with Fuseki
docker compose -f docker-compose.fuseki.yml up -d
```

### Accessing Services

- **Fuseki Admin UI**: http://localhost:3030
- **Jupyter Notebooks**: http://localhost:8889
- **YASGUI**: http://localhost:8080

### Example SPARQL Query

```bash
# Query all triples in the dataset
curl -X POST http://localhost:3030/kgap/sparql \
  -H 'Content-Type: application/sparql-query' \
  -d 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'
```

### Loading Data

```bash
# Insert triples via SPARQL Update
curl -X POST http://localhost:3030/kgap/update \
  -H 'Content-Type: application/sparql-update' \
  -d 'INSERT DATA { <http://example.org/s> <http://example.org/p> "hello" }'

# Upload a Turtle file
curl -X POST http://localhost:3030/kgap/data \
  -H 'Content-Type: text/turtle' \
  --data-binary @my-data.ttl
```

## File Structure

```
fuseki/
├── Dockerfile                        # Image definition
└── kgap/
    ├── entrypoint-wrap.sh           # Startup script (creates dataset config)
    ├── healthy.sh                   # Health check script
    └── template-dataset-config.ttl # Dataset configuration template
```

### entrypoint-wrap.sh

Runs on container startup:

1. Reads `FUSEKI_DATASET` environment variable (default: `kgap`)
2. Checks if dataset configuration exists at `/fuseki/configuration/${FUSEKI_DATASET}.ttl`
3. If not, creates it from the template using `envsubst`
4. Delegates to the original Fuseki Docker entrypoint

### healthy.sh

Queries the dataset-specific SPARQL endpoint to confirm Fuseki is ready:

```bash
#!/bin/bash
FUSEKI_DATASET=${FUSEKI_DATASET:-kgap}
HEALTH_CHECK_URI="http://localhost:3030/${FUSEKI_DATASET}/sparql?query=ASK+%7B+%7D"
curl --fail -X GET --url ${HEALTH_CHECK_URI}
```

## Comparison with GraphDB

| Feature | Fuseki | GraphDB |
|---------|--------|---------|
| Named datasets | Yes (per endpoint path) | Yes (repositories) |
| SPARQL 1.1 Query | ✓ | ✓ |
| SPARQL 1.1 Update | ✓ | ✓ |
| Full-text search | Via Lucene plugin | ✓ (built-in) |
| Inference / reasoning | Via OWL/rule reasoners | ✓ (configurable rulesets) |
| Web UI | Admin UI at `/$/` | Full workbench |
| License | Apache 2.0 | Free tier available |

## Troubleshooting

### Dataset not found (404 on SPARQL endpoint)

The dataset may not have been created yet. Check the startup logs:
```bash
docker compose -f docker-compose.fuseki.yml logs fuseki
```

If the config file was not generated, verify that `FUSEKI_DATASET` is set and the container has write access to `/fuseki/configuration/`.

### Permission errors on startup

The Fuseki image runs as the `fuseki` user. Ensure the volume directories are writable:
```bash
mkdir -p ./data/fuseki
chmod 777 ./data/fuseki
```

### Admin UI access

Navigate to http://localhost:3030 and log in with username `admin` and the password set via `FUSEKI_ADMIN_PASSWORD` (default: `admin`).
