---
title: GraphDB Component
parent: Components
nav_order: 1
---

# GraphDB Component

The GraphDB component is the core RDF triple store for K-GAP, providing SPARQL query capabilities and persistent storage for knowledge graphs.

## Overview

GraphDB is a semantic graph database that stores RDF triples and provides:
- SPARQL 1.1 query support
- Full-text search indexing
- REST API access
- Web-based workbench interface
- High-performance querying

**Base Image**: `ontotext/graphdb:10.4.4`  
**Exposed Port**: 7200 (HTTP)  
**Container Name**: `test_kgap_graphdb` (in test setup)

## Architecture

```
┌────────────────────────────────────────┐
│         GraphDB Container              │
├────────────────────────────────────────┤
│                                        │
│  entrypoint-wrap.sh                   │
│       │                                │
│       ├─▶ Check/Create Repository     │
│       │   - template-repo-config.ttl  │
│       │   - Apply environment vars     │
│       │                                │
│       └─▶ Start GraphDB               │
│           - SPARQL endpoint            │
│           - Web workbench              │
│           - REST API                   │
│                                        │
│  Volumes:                              │
│  - ./data → /root/graphdb-import/data │
│                                        │
└────────────────────────────────────────┘
```

## Configuration

### Environment Variables

These variables are defined in the repository root `.env` file (copy `dotenv-example` to `.env` and adjust values for your deployment).

The following environment variables configure the GraphDB instance:

| Variable | Default | Description |
|----------|---------|-------------|
| `GDB_REPO` | `kgap` | Repository name |
| `REPOLABEL` | `label_repo_here` | Human-readable repository label |
| `GDB_HOME_FOLDER` | `/opt/graphdb/home` | GraphDB home directory |
| `GDB_MAX_HEADER` | `65536` | Maximum HTTP header size |
| `GDB_JAVA_OPTS` | `-Xms8g -Xmx16g -Dcom.ontotext.graphdb.monitoring.jmx=true` | Java options for memory and monitoring |

### Repository Configuration

The repository is automatically created on first startup using the template at `graphdb/kgap/template-repo-config.ttl`. The template is processed with environment variable substitution:

```turtle
<#${REPONAME}> a rep:Repository ;
    rep:repositoryID "${REPONAME}" ;
    rdfs:label "${REPOLABEL}" ;
    # ... configuration continues
```

Key repository settings:

- **Base URL**: `http://example.org/owlim#`
- **Entity Index Size**: 10,000,000 entities
- **Entity ID Size**: 32-bit
- **Repository Type**: File-based repository
- **Ruleset**: Empty (no inference)
- **Storage Folder**: `storage` (within repository directory)

#### Indexing Configuration

- **Context Index**: Disabled (`enable-context-index: false`)
- **Full-Text Search**: Enabled (`enable-fts-index: true`)
  - IRI indexing: Default
  - String literals indexing: Default
  - Available indexes: `default`, `iri`
- **Literal Index**: Enabled (`enable-literal-index: true`)
- **Predicate List**: Enabled (`enablePredicateList: true`)
- **In-Memory Literal Properties**: Enabled

#### Query and Consistency Settings

- **Check for Inconsistencies**: Disabled
- **sameAs Reasoning**: Disabled (`disable-sameAs: true`)
- **Query Timeout**: Unlimited (`0`)
- **Query Result Limit**: Unlimited (`0`)
- **Read-Only Mode**: Disabled

### Resource Allocation

GraphDB is configured for high-performance operations:

```yaml
cpus: 4                    # CPU cores allocated
GDB_JAVA_OPTS: "-Xms8g -Xmx16g ..."  # 8GB min, 16GB max heap
```

Adjust these values based on your system resources and workload.

### Configuration Examples

#### Minimal Setup (Development)

For development or testing environments:

```bash
# .env file
COMPOSE_PROJECT_NAME=kgap
GDB_REPO=kgap
REPOLABEL=Development Repository
GDB_MAX_HEADER=65536
GDB_JAVA_OPTS="-Xms2g -Xmx4g"
```

#### Standard Setup (Production)

For typical production deployments:

```bash
# .env file
COMPOSE_PROJECT_NAME=kgap-prod
GDB_REPO=kgap_production
REPOLABEL=K-GAP Production Repository
GDB_MAX_HEADER=65536
GDB_HOME_FOLDER=/data/graphdb
GDB_JAVA_OPTS="-Xms8g -Xmx16g -Dcom.ontotext.graphdb.monitoring.jmx=true"
```

#### Large-Scale Setup (High Volume)

For high-volume triple stores with many concurrent queries:

```bash
# .env file
COMPOSE_PROJECT_NAME=kgap-enterprise
GDB_REPO=kgap_enterprise
REPOLABEL=K-GAP Enterprise Repository
GDB_MAX_HEADER=131072  # Increased for large query results
GDB_HOME_FOLDER=/data/graphdb  # Persist data
GDB_JAVA_OPTS="-Xms32g -Xmx64g -Dcom.ontotext.graphdb.monitoring.jmx=true -XX:+UseG1GC"
```

#### Persistent Data Storage

To persist GraphDB data across container restarts:

```bash
# 1. Create persistent directory
mkdir -p ./data/graphdb

# 2. Set in .env
GDB_HOME_FOLDER=/data/graphdb

# 3. Verify in docker-compose.yml:
# volumes:
#   - ./data/graphdb:/opt/graphdb/home
```

### Health Check

The container includes a health check script (`healthy.sh`) that verifies GraphDB is running:

```yaml
healthcheck:
  start_period: 1s         # Time to wait before first check
  interval: 5s             # Time between checks
  timeout: 3s              # Timeout for each check
  retries: 3               # Number of retries before unhealthy
```

For repositories with heavy features (e.g., extensive inference), you may need to increase `start_period`:

```yaml
healthcheck:
  start_period: 30s
  interval: 5s
  timeout: 3s
  retries: 3
```

## Usage

### Accessing GraphDB

#### Web Workbench

Navigate to http://localhost:7200 in your browser to access:
- Repository management
- SPARQL query editor
- Import/export tools
- Repository statistics

For detailed Workbench usage, see the official GraphDB documentation: [Working with Workbench](https://graphdb.ontotext.com/documentation/11.2/working-with-workbench.html) (version-specific; adapt to your deployed GraphDB version if needed).

#### SPARQL Endpoint

The SPARQL endpoint is available at:
```
http://localhost:7200/repositories/{repository-name}
```

For the default setup:
```
http://localhost:7200/repositories/kgap
```

Or for statements endpoint:
```
http://localhost:7200/repositories/kgap/statements
```

### Querying with SPARQL

#### Using curl

```bash
curl -X POST \
  http://localhost:7200/repositories/kgap \
  -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/sparql-results+json' \
  -d 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'
```

#### Using Python (from Jupyter)

```python
from kgap_tools import execute_to_df

# Execute SPARQL query and get DataFrame
df = execute_to_df('my_query_template', param1='value1')
```

### Importing Data

#### Via Web Interface

1. Navigate to http://localhost:7200
2. Select your repository
3. Go to "Import" → "RDF"
4. Upload RDF files (TTL, RDF/XML, N-Triples, etc.)

#### Via REST API

```bash
curl -X POST \
  http://localhost:7200/repositories/kgap/statements \
  -H 'Content-Type: text/turtle' \
  --data-binary '@data.ttl'
```

#### Via Mounted Volume

Place RDF files in the `./data` directory, which is mounted at `/root/graphdb-import/data` in the container. Files are not imported automatically from this mount; import them via the web interface or REST API. See [FAQ: How do I import RDF data?](../faq.md#how-do-i-import-rdf-data) for the detailed options.

### Exporting Data

Export repository data:

```bash
curl -X GET \
  'http://localhost:7200/repositories/kgap/statements' \
  -H 'Accept: text/turtle' \
  > export.ttl
```

## File Structure

```
graphdb/
├── Dockerfile                    # Image definition
└── kgap/
    ├── entrypoint-wrap.sh       # Startup script
    ├── healthy.sh               # Health check script
    └── template-repo-config.ttl # Repository configuration template
```

### entrypoint-wrap.sh

This script runs on container startup and:

1. Reads environment variables for configuration
2. Checks if repository configuration exists
3. If not, creates repository config from template using `envsubst`
4. Starts GraphDB with configured parameters

```bash
#!/bin/bash
REPONAME=${GDB_REPO:-kgap}
REPOLABEL=${REPOLABEL:-"KGAP repo for ${REPONAME}"}
# ... repository setup logic
/opt/graphdb/dist/bin/graphdb -Dgraphdb.home=${GDB_HOME_FOLDER} ...
```

### healthy.sh

Verifies GraphDB is responding to requests by checking the health endpoint.

## Troubleshooting

### Container Won't Start

**Symptom**: Container exits immediately with exit code 1

**Solutions**:
1. Check logs: `docker compose logs graphdb`
2. Verify disk space: `df -h`
3. Check Java options for syntax errors: `echo $GDB_JAVA_OPTS`
4. Verify `.env` file exists: `cat .env`

### Out of Memory

**Symptom**: Container crashes with "java.lang.OutOfMemoryError"

**Solution**:
```bash
# Increase heap size in .env
GDB_JAVA_OPTS="-Xms16g -Xmx32g"

# Restart GraphDB
docker compose down
docker compose up -d graphdb
```

### Slow Queries

**Symptom**: SPARQL queries take minutes to execute

**Solutions**:
1. Add indexes to frequently queried properties
2. Increase Java heap: `GDB_JAVA_OPTS="-Xms16g -Xmx32g"`
3. Check repository statistics: http://localhost:7200 → Your Repository → Queries
4. Review query execution plan in Workbench

### Connection Refused

**Symptom**: Cannot connect to http://localhost:7200

**Solutions**:
```bash
# Verify container is running
docker compose ps graphdb

# Check if port is available
lsof -i :7200

# Verify network connectivity
docker compose exec graphdb curl http://localhost:7200/healthy
```

## Environment Variables Reference

### Complete Table

| Variable | Default | Min | Max | Description |
|----------|---------|-----|-----|-------------|
| `GDB_REPO` | `kgap` | N/A | N/A | Repository identifier (alphanumeric, no spaces) |
| `REPOLABEL` | `label_repo_here` | N/A | N/A | Human-readable repository name |
| `GDB_HOME_FOLDER` | `/opt/graphdb/home` | N/A | N/A | Directory for repository storage |
| `GDB_MAX_HEADER` | `65536` | `8192` | `262144` | Max HTTP header size in bytes |
| `GDB_JAVA_OPTS` | `-Xms8g -Xmx16g ...` | N/A | N/A | Java runtime options |

### Java Options (`GDB_JAVA_OPTS`) Components

| Option | Purpose | Example |
|--------|---------|----------|
| `-Xms` | Initial heap size | `-Xms8g` (8GB) |
| `-Xmx` | Maximum heap size | `-Xmx16g` (16GB) |
| `-Dcom.ontotext.graphdb.monitoring.jmx=true` | Enable JMX monitoring | Needed for monitoring tools |
| `-XX:+UseG1GC` | Use G1 garbage collector | Better for large heaps (>12GB) |
| `-XX:+PerfDisableSharedMem` | Disable shared memory perf | Helps in Kubernetes/containerized environments |

Simple health check that verifies GraphDB is responding:

```bash
#!/bin/bash
# Checks if GraphDB is responding to HTTP requests
curl -f http://localhost:7200/ > /dev/null 2>&1
```

## Common Operations

### Viewing Repository Statistics

```bash
curl http://localhost:7200/rest/repositories/kgap/size
```

### Clearing a Repository

```bash
curl -X DELETE http://localhost:7200/repositories/kgap/statements
```

### Backup and Restore

**Backup**:
```bash
# Export all data
curl 'http://localhost:7200/repositories/kgap/statements' \
  -H 'Accept: application/x-trig' \
  > backup.trig
```

**Restore**:
```bash
# Clear existing data (optional)
curl -X DELETE http://localhost:7200/repositories/kgap/statements

# Import backup
curl -X POST \
  http://localhost:7200/repositories/kgap/statements \
  -H 'Content-Type: application/x-trig' \
  --data-binary '@backup.trig'
```

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
docker compose logs graphdb
```

**Common issues**:
- Insufficient memory: Increase `GDB_JAVA_OPTS` heap size or system RAM
- Port 7200 already in use: Change port mapping in `docker-compose.yml`
- Invalid repository configuration: Check `template-repo-config.ttl` syntax

### Out of Memory Errors

Increase Java heap size in `.env`:
```bash
GDB_JAVA_OPTS="-Xms16g -Xmx32g -Dcom.ontotext.graphdb.monitoring.jmx=true"
```

### Slow Queries

Consider:
- Adding indexes to frequently queried predicates
- Enabling context indexing if you use named graphs extensively
- Optimizing SPARQL queries (use FILTER instead of OPTIONAL where possible)
- Increasing CPU allocation

### Repository Not Found

Check that the repository was created:
```bash
curl http://localhost:7200/rest/repositories
```

If missing, check the entrypoint logs for errors during repository creation.

## Performance Tuning

### For Large Datasets (>10M triples)

```bash
# Increase entity index size
# Edit template-repo-config.ttl:
graphdb:entity-index-size "100000000" ;  # 100M entities
graphdb:entity-id-size "40" ;             # 40-bit IDs
```

### For Heavy Query Load

```bash
# Increase CPU and memory allocation in docker-compose.yml:
cpus: 8
GDB_JAVA_OPTS: "-Xms16g -Xmx32g ..."
```

### For Full-Text Search

If you need advanced full-text search, configure additional FTS indexes in the repository template.

## API Reference

For complete GraphDB REST API documentation, see:
- [GraphDB Documentation](https://graphdb.ontotext.com/documentation/)
- [SPARQL 1.1 Protocol](https://www.w3.org/TR/sparql11-protocol/)

## Security Considerations

**Default Setup**: GraphDB runs without authentication (suitable for development).

**Production**: 
- Enable authentication in GraphDB settings
- Use reverse proxy with SSL/TLS
- Restrict network access
- Regular backups
- Monitor access logs

## Related Documentation

- [Main Documentation](../index.md)
- [LDES Consumer Component](./ldes-consumer.md) - Data ingestion
- [Jupyter Component](./jupyter.md) - Data analysis
- [Sembench Component](./sembench.md) - Data processing
