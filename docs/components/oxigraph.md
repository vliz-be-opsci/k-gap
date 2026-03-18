---
title: Oxigraph Component
parent: Components
nav_order: 5
---

# Oxigraph Component

Oxigraph is a lightweight, high-performance RDF graph database written in Rust. It provides a SPARQL 1.1 compatible triple store that can serve as an alternative to GraphDB in the K-GAP stack.

## Overview

Oxigraph is a single-store server — all triples are stored together in one database. Use named graphs to organise project data within the store.

- SPARQL 1.1 Query and Update support
- SPARQL Graph Store HTTP Protocol
- Fast startup and low memory footprint
- No database creation step required (the store is auto-initialised)

**Base Image**: [`ghcr.io/oxigraph/oxigraph`](https://github.com/oxigraph/oxigraph)  
**Exposed Port**: 7878 (HTTP)  
**Container Name**: `test_kgap_oxigraph` (in test setup)  

## Architecture

```
┌────────────────────────────────────────┐
│        Oxigraph Container              │
├────────────────────────────────────────┤
│                                        │
│  CMD: oxigraph serve                  │
│       --location /data                │
│       --bind 0.0.0.0:7878             │
│                                        │
│  Endpoints:                            │
│  - /query   → SPARQL Query            │
│  - /update  → SPARQL Update           │
│  - /store   → Graph Store Protocol    │
│                                        │
│  Volumes:                              │
│  - ./data/oxigraph → /data            │
│                                        │
└────────────────────────────────────────┘
```

## SPARQL Endpoints

After startup, the following endpoints are available:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `http://localhost:7878/query` | GET / POST | SPARQL 1.1 Query |
| `http://localhost:7878/update` | POST | SPARQL 1.1 Update |
| `http://localhost:7878/store` | GET / POST / PUT / DELETE | Graph Store Protocol |

## Usage

### Starting with Oxigraph

```bash
# Copy and configure environment
cp dotenv-example .env
# Edit .env as needed (GDB_REPO is not used by Oxigraph)

# Create data directories
mkdir -p ./data/oxigraph ./notebooks

# Start the full K-GAP stack with Oxigraph
docker compose -f docker-compose.oxigraph.yml up -d
```

### Accessing Services

- **Oxigraph SPARQL UI**: http://localhost:7878
- **Jupyter Notebooks**: http://localhost:8889
- **YASGUI**: http://localhost:8080

### Example SPARQL Query

```bash
# Query all triples
curl -X POST http://localhost:7878/query \
  -H 'Content-Type: application/sparql-query' \
  -d 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'
```

### Loading Data

```bash
# Insert triples via SPARQL Update
curl -X POST http://localhost:7878/update \
  -H 'Content-Type: application/sparql-update' \
  -d 'INSERT DATA { <http://example.org/s> <http://example.org/p> "hello" }'

# Load a Turtle file via Graph Store Protocol
curl -X POST http://localhost:7878/store?default \
  -H 'Content-Type: text/turtle' \
  --data-binary @my-data.ttl
```

## Configuration

### Environment Variables

Oxigraph does not use named repositories. There are no repository-specific environment variables. Data is stored at the location specified in the `CMD` (`/data` by default).

### Data Persistence

Data is stored in the Docker volume mapped to `/data`. Configure the host path in `docker-compose.oxigraph.yml`:

```yaml
volumes:
  - ./data/oxigraph:/data
```

### Health Check

The container includes a health check script (`healthy.sh`) that verifies Oxigraph is ready by running a minimal SPARQL ASK query:

```yaml
healthcheck:
  start_period: 2s
  interval: 5s
  timeout: 3s
  retries: 3
```

## File Structure

```
oxigraph/
├── Dockerfile                    # Image definition
└── kgap/
    └── healthy.sh               # Health check script
```

### healthy.sh

Sends a minimal `ASK {}` SPARQL query to confirm the server is ready and accepting queries:

```bash
#!/bin/sh
HEALTH_CHECK_URI="http://localhost:7878/query?query=ASK+%7B+%7D"
curl --fail -X GET --url ${HEALTH_CHECK_URI}
```

## Comparison with GraphDB

| Feature | Oxigraph | GraphDB |
|---------|----------|---------|
| Named repositories | No (use named graphs) | Yes |
| SPARQL 1.1 Query | ✓ | ✓ |
| SPARQL 1.1 Update | ✓ | ✓ |
| Full-text search | Limited | ✓ |
| Inference / reasoning | Limited | ✓ (configurable rulesets) |
| Web UI | Minimal | Full workbench |
| Memory footprint | Low | Higher |
| License | Apache 2.0 | Free tier available; commercial for full features |

## Troubleshooting

### Container exits immediately

Check the data directory is writable:
```bash
ls -la ./data/oxigraph
docker compose -f docker-compose.oxigraph.yml logs oxigraph
```

### SPARQL queries return errors

Verify the server is healthy:
```bash
curl http://localhost:7878/query?query=ASK+%7B+%7D
```
