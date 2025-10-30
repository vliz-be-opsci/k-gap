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

Place RDF files in the `./data` directory, which is mounted at `/root/graphdb-import/data` in the container. You can then import them via the web interface or REST API.

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
    ├── validate-shacl.sh        # SHACL validation script
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

Simple health check that verifies GraphDB is responding:

```bash
#!/bin/bash
# Checks if GraphDB is responding to HTTP requests
curl -f http://localhost:7200/ > /dev/null 2>&1
```

### validate-shacl.sh

SHACL validation script that triggers GraphDB's validation endpoint:

```bash
#!/bin/bash
# Triggers SHACL validation and displays the validation report
# Usage: validate-shacl.sh [REPOSITORY] [NAMED_GRAPH]
# Environment variables: GDB_HOST, GDB_PORT, GDB_REPO
```

This script:
1. Accepts optional repository name and named graph parameters
2. Calls GraphDB's `/repositories/{repo}/shacl/validate` endpoint
3. Displays the validation report in Turtle format
4. Returns appropriate exit codes (0 for success, 1 for violations/errors)

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

### SHACL Validation

GraphDB provides built-in SHACL validation capabilities. K-GAP includes convenient scripts to trigger SHACL validation and retrieve validation reports.

#### Using the Host Script

From the host machine (outside the container), use the provided script:

```bash
# Validate the default repository (all graphs)
./validate-shacl-host.sh

# Validate a specific repository
./validate-shacl-host.sh kgap

# Validate a specific named graph within a repository
./validate-shacl-host.sh kgap http://example.org/my-graph
```

The script will:
1. Execute validation inside the GraphDB container
2. Display the validation report in Turtle format
3. Return exit code 0 if validation passes (no violations)
4. Return exit code 1 if validation finds constraint violations

#### Using the Container Script

From inside the GraphDB container:

```bash
# Validate the default repository
docker exec test_kgap_graphdb /kgap/validate-shacl.sh

# Validate with parameters
docker exec test_kgap_graphdb /kgap/validate-shacl.sh kgap http://example.org/my-graph
```

#### Using the REST API Directly

Trigger SHACL validation via the GraphDB REST API:

```bash
# Validate all graphs
curl -X POST \
  http://localhost:7200/repositories/kgap/shacl/validate \
  -H 'Accept: text/turtle'

# Validate a specific named graph
curl -X POST \
  http://localhost:7200/repositories/kgap/shacl/validate \
  -H 'Accept: text/turtle' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'context=http://example.org/my-graph'
```

The validation report is returned in the requested RDF format (Turtle, RDF/XML, JSON-LD, etc.).

#### SHACL Shapes

To use SHACL validation, you need to have SHACL shapes defined in your repository. SHACL shapes define the constraints that your RDF data should conform to.

**Example SHACL shape:**
```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:name ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path ex:email ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:pattern "^.+@.+\\..+$" ;
    ] .
```

Import your SHACL shapes into GraphDB using any of the standard import methods (web interface, REST API, etc.).

#### Validation Report Format

The validation report follows the SHACL specification and includes:
- `sh:conforms`: Boolean indicating if data conforms to all shapes
- `sh:result`: List of validation results (constraint violations)
- Each result includes:
  - `sh:focusNode`: The node that violates the constraint
  - `sh:resultPath`: The property path where the violation occurred
  - `sh:resultSeverity`: Severity level (Violation, Warning, Info)
  - `sh:resultMessage`: Human-readable description of the violation

**Example validation report:**
```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .

[]
    a sh:ValidationReport ;
    sh:conforms false ;
    sh:result [
        a sh:ValidationResult ;
        sh:focusNode <http://example.org/person1> ;
        sh:resultPath <http://example.org/name> ;
        sh:resultSeverity sh:Violation ;
        sh:sourceConstraintComponent sh:MinCountConstraintComponent ;
        sh:resultMessage "MinCount constraint violation: expected 1, found 0" ;
    ] .
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
