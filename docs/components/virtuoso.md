---
title: Virtuoso Component
parent: Components
nav_order: 7
---

# Virtuoso Component

OpenLink Virtuoso is a high-performance multi-model database with built-in SPARQL 1.1 support. It can serve as an alternative to GraphDB in the K-GAP stack, particularly where large-scale RDF storage and Linked Data publishing are needed.

## Overview

Virtuoso exposes a single SPARQL endpoint (`/sparql`) that accepts both queries and updates. The "database per project" concept in Virtuoso maps to **named graphs** — a named graph URI is set via `VIRTUOSO_GRAPH` and used as the default graph for project data. Named graphs are created automatically when data is first inserted.

- SPARQL 1.1 Query and Update support
- Single SPARQL endpoint for all operations
- Named-graph based data organisation
- Conductor web admin UI
- High performance for large triple stores

**Base Image**: [`redpencil/virtuoso`](https://hub.docker.com/r/redpencil/virtuoso)  
**Exposed Ports**: 8890 (HTTP), 1111 (ISQL)  
**Container Name**: `test_kgap_virtuoso` (in test setup)  

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Virtuoso Container                      │
├──────────────────────────────────────────────────┤
│                                                   │
│  entrypoint-wrap.sh                              │
│       │                                           │
│       ├─▶ Set DEFAULT_GRAPH from KGAP_REPO      │
│       │   (e.g. http://kgap.vliz.be/graph/kgap) │
│       │                                           │
│       └─▶ Start Virtuoso                         │
│           - SPARQL endpoint at /sparql            │
│           - Conductor UI at /conductor            │
│           - ISQL on port 1111                    │
│                                                   │
│  Volumes:                                         │
│  - ./data/virtuoso → /data                       │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

These variables are defined in the repository root `.env` file (copy `dotenv-example` to `.env` and adjust values).

| Variable | Default | Description |
|----------|---------|-------------|
| `KGAP_REPO` | `kgap` | Used to construct the default named graph URI |
| `VIRTUOSO_GRAPH` | `http://kgap.vliz.be/graph/<KGAP_REPO>` | Named graph URI for project data |
| `VIRTUOSO_DBA_PASSWORD` | `dba` | Admin (DBA) password for Virtuoso |

### Named Graph (Project Database)

Unlike GraphDB, Virtuoso does not use separate repository databases. Instead, project data is stored in a **named graph**. The graph URI is set via:

```bash
# .env file
KGAP_REPO=my_project
# Results in DEFAULT_GRAPH=http://kgap.vliz.be/graph/my_project

# Or set the graph URI directly:
VIRTUOSO_GRAPH=http://example.org/my-custom-graph
```

Named graphs are created automatically in Virtuoso when data is first inserted — no explicit creation step is needed.

### Health Check

The health check sends a minimal SPARQL ASK query to the `/sparql` endpoint:

```yaml
healthcheck:
  start_period: 10s
  interval: 10s
  timeout: 5s
  retries: 5
```

Virtuoso can take longer to start than lighter stores; adjust `start_period` for large databases:

```yaml
healthcheck:
  start_period: 60s
  interval: 10s
  timeout: 5s
  retries: 5
```

## SPARQL Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `http://localhost:8890/sparql` | GET / POST | SPARQL 1.1 Query and Update |
| `http://localhost:8890/conductor` | GET | Admin web UI (login: dba / DBA_PASSWORD) |
| `localhost:1111` | TCP | ISQL admin port |

### Querying a Specific Named Graph

To query data within the project named graph:

```sparql
SELECT * FROM <http://kgap.vliz.be/graph/kgap>
WHERE { ?s ?p ?o }
LIMIT 10
```

Or use the `default-graph-uri` parameter:

```bash
curl "http://localhost:8890/sparql?default-graph-uri=http%3A%2F%2Fkgap.vliz.be%2Fgraph%2Fkgap&query=SELECT+*+WHERE+%7B+%3Fs+%3Fp+%3Fo+%7D+LIMIT+10"
```

## Usage

### Starting with Virtuoso

```bash
# Copy and configure environment
cp dotenv-example .env
# Edit .env: set KGAP_REPO and VIRTUOSO_DBA_PASSWORD

# Create data directories
mkdir -p ./data/virtuoso ./notebooks

# Start the full K-GAP stack with Virtuoso
docker compose -f docker-compose.virtuoso.yml up -d
```

### Accessing Services

- **Virtuoso SPARQL endpoint**: http://localhost:8890/sparql
- **Virtuoso Conductor (admin)**: http://localhost:8890/conductor
- **Jupyter Notebooks**: http://localhost:8889
- **YASGUI**: http://localhost:8080

### Loading Data

```bash
# Insert triples into the project named graph via SPARQL Update
curl -X POST http://localhost:8890/sparql \
  -H 'Content-Type: application/sparql-update' \
  -d 'INSERT DATA INTO <http://kgap.vliz.be/graph/kgap> { <http://example.org/s> <http://example.org/p> "hello" }'
```

## File Structure

```
virtuoso/
├── Dockerfile                    # Image definition
└── kgap/
    ├── entrypoint-wrap.sh       # Startup script (sets DEFAULT_GRAPH)
    └── healthy.sh               # Health check script
```

### entrypoint-wrap.sh

Sets the `DEFAULT_GRAPH` environment variable (used by `redpencil/virtuoso`) from `KGAP_REPO` or `VIRTUOSO_GRAPH`, then delegates to the original image entrypoint.

### healthy.sh

Sends a minimal SPARQL ASK query to confirm Virtuoso is ready:

```bash
#!/bin/bash
HEALTH_CHECK_URI="http://localhost:8890/sparql?query=ASK+%7B+%7D"
curl --fail -X GET --url ${HEALTH_CHECK_URI}
```

## Comparison with GraphDB

| Feature | Virtuoso | GraphDB |
|---------|----------|---------|
| Project isolation | Named graphs | Named repositories |
| SPARQL 1.1 Query | ✓ | ✓ |
| SPARQL 1.1 Update | ✓ | ✓ |
| Full-text search | ✓ | ✓ |
| Inference / reasoning | ✓ (OWL) | ✓ (configurable rulesets) |
| Web UI | Conductor | Full workbench |
| Multi-model | Yes (SQL + RDF) | No |
| License | Open source (AGPLv2) / commercial | Free tier; commercial for full features |

## Troubleshooting

### Slow startup

Virtuoso performs a database recovery check on startup. Increase `start_period` in the healthcheck if needed:

```yaml
healthcheck:
  start_period: 60s
```

### SPARQL Update permission denied

By default, Virtuoso restricts SPARQL updates. Enable updates via the Conductor UI under `System Admin → SQL → Execute`:

```sql
GRANT SPARQL_UPDATE TO "SPARQL";
```

Or set this via the `DBA_PASSWORD` and `isql` tool:

```bash
docker exec -it test_kgap_virtuoso isql 1111 dba <password> \
  "GRANT SPARQL_UPDATE TO 'SPARQL';"
```

### Data not persisting

Ensure the data volume is correctly mapped:

```yaml
volumes:
  - ./data/virtuoso:/data
```

Check permissions on the host directory:

```bash
ls -la ./data/virtuoso
```
