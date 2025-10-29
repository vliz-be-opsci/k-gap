# K-GAP Documentation

**Knowledge Graph Analysis Platform**

K-GAP is a microservices-based platform for building, managing, and analyzing knowledge graphs using SPARQL and linked data technologies.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)

## Overview

K-GAP (Knowledge Graph Analysis Platform) is designed to provide a comprehensive, containerized environment for working with knowledge graphs. It combines several specialized microservices that work together to:

- Store and query RDF data using GraphDB
- Harvest and ingest data from LDES (Linked Data Event Streams) feeds
- Analyze and process knowledge graphs using Python tools (Sembench)
- Explore data interactively through Jupyter notebooks

### Key Features

- **Microservices Architecture**: Each component runs as an independent Docker container
- **LDES Integration**: Automated harvesting from multiple Linked Data Event Streams
- **Interactive Analysis**: Jupyter notebooks for data exploration and visualization
- **Scalable Storage**: GraphDB repository with configurable resources
- **Automated Processing**: Scheduled data processing pipelines via Sembench

## Architecture

K-GAP follows a microservices architecture pattern where each component is:
- Packaged as a Docker container
- Independently deployable
- Connected through a shared Docker network
- Configured via environment variables

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        K-GAP Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐        ┌──────────────┐                   │
│  │   Jupyter    │───────▶│   GraphDB    │                   │
│  │  Notebooks   │        │  Repository  │                   │
│  └──────────────┘        └──────────────┘                   │
│         │                        ▲                           │
│         │                        │                           │
│         ▼                        │                           │
│  ┌──────────────┐        ┌──────────────┐                   │
│  │   Sembench   │───────▶│ LDES Consumer│                   │
│  │  Processing  │        │   (spawns)   │                   │
│  └──────────────┘        └──────┬───────┘                   │
│                                  │                           │
│                          ┌───────▼───────┐                   │
│                          │ ldes2sparql   │                   │
│                          │  containers   │                   │
│                          └───────────────┘                   │
│                                                               │
│  ┌──────────────┐                                            │
│  │   YASGUI     │──────▶ GraphDB SPARQL Endpoint            │
│  │   Web UI     │                                            │
│  └──────────────┘                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion**: LDES Consumer harvests data from external LDES feeds and ingests into GraphDB
2. **Storage**: GraphDB stores RDF triples in a SPARQL-queryable repository
3. **Processing**: Sembench runs scheduled tasks to process and transform data
4. **Analysis**: Jupyter notebooks query and analyze the knowledge graph
5. **Exploration**: YASGUI provides a web interface for SPARQL queries

## Components

K-GAP consists of four main Docker images and one optional web UI:

### 1. GraphDB (`kgap_graphdb`)

GraphDB is the core RDF triple store that provides:
- SPARQL 1.1 query endpoint
- Repository management
- Full-text search indexing
- REST API access

**Base Image**: `ontotext/graphdb:10.4.4`  
**Port**: 7200 (HTTP)  
**Documentation**: [GraphDB Component](./components/graphdb.md)

### 2. Jupyter (`kgap_jupyter`)

Interactive notebook environment for data analysis:
- Pre-installed Python packages for RDF/SPARQL
- Access to GraphDB endpoint
- Template notebooks for common tasks
- Shared volumes for data and notebooks

**Base Image**: `jupyter/base-notebook`  
**Port**: 8889 (mapped to internal 8888)  
**Documentation**: [Jupyter Component](./components/jupyter.md)

### 3. Sembench (`kgap_sembench`)

Python-based semantic processing engine:
- Scheduled data processing tasks
- Integration with [py-sema](https://github.com/vliz-be-opsci/py-sema) library
- Configurable processing pipelines
- Automated workflows

**Base Image**: `python:3.10`  
**Documentation**: [Sembench Component](./components/sembench.md)

### 4. LDES Consumer (`kgap_ldes-consumer`)

Multi-feed LDES harvesting service:
- Wraps [ldes2sparql](https://github.com/rdf-connect/ldes2sparql)
- Spawns separate containers for each LDES feed
- Configurable polling intervals
- Automatic restart on failure

**Base Image**: `python:3.10-slim`  
**Documentation**: [LDES Consumer Component](./components/ldes-consumer.md)

### 5. YASGUI (Optional)

Web-based SPARQL query interface:
- Visual query builder
- Results visualization
- Query history
- NOT built from this repository (uses `redpencil/yasgui:latest`)

**Port**: 8080

## Getting Started

### Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 16GB RAM recommended
- 20GB free disk space

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/vliz-be-opsci/k-gap.git
   cd k-gap
   ```

2. **Configure environment**:
   ```bash
   cp dotenv-example .env
   # Edit .env to customize settings
   ```

3. **Create data directories**:
   ```bash
   mkdir -p ./data
   mkdir -p ./notebooks
   ```

4. **Start the platform**:
   ```bash
   docker compose up -d
   ```

5. **Access services**:
   - GraphDB Workbench: http://localhost:7200
   - Jupyter Notebooks: http://localhost:8889
   - YASGUI: http://localhost:8080

### Building Images Locally

To build all Docker images locally:

```bash
make docker-build
```

This builds images with the default tag. To specify a custom tag:

```bash
make BUILD_TAG=0.2.0 docker-build
```

### Pushing to Registry

To build and push images to a container registry:

```bash
make REG_NS=ghcr.io/vliz-be-opsci/kgap docker-push
```

## Configuration

K-GAP is configured through environment variables defined in a `.env` file.

### Core Configuration

```bash
# Docker Compose
COMPOSE_PROJECT_NAME=kgap

# GraphDB Configuration
GDB_REPO=kgap                    # Repository name
REPOLABEL=label_repo_here        # Repository label
GDB_HOME_FOLDER=/opt/graphdb/home
GDB_MAX_HEADER=65536
GDB_JAVA_OPTS="-Xms8g -Xmx16g -Dcom.ontotext.graphdb.monitoring.jmx=true"

# Jupyter Configuration
SRC_FOLDER=/kgap/notebooks

# Sembench Configuration
SEMBENCH_INPUT_PATH=/data
SEMBENCH_OUTPUT_PATH=/data
SEMBENCH_HOME_PATH=/data
SEMBENCH_CONFIG_PATH=/data/sembench.yaml
SCHEDULER_INTERVAL_SECONDS=86400  # 24 hours

# LDES Consumer Configuration
LDES_CONFIG_FILE=/data/ldes-feeds.yaml
LDES2SPARQL_IMAGE=ghcr.io/rdf-connect/ldes2sparql:latest
LOG_LEVEL=INFO
```

### GraphDB Repository Configuration

The GraphDB repository is automatically configured on first startup using the template at `graphdb/kgap/template-repo-config.ttl`. Key settings:

- **Base URL**: `http://example.org/owlim#`
- **Entity Index Size**: 10,000,000
- **Full-Text Search**: Enabled
- **Ruleset**: Empty (no inference by default)
- **Context Index**: Disabled
- **Predicate List**: Enabled

To customize the repository configuration, modify the template before starting GraphDB.

### LDES Feeds Configuration

Create a `data/ldes-feeds.yaml` file to configure LDES feed harvesting:

```yaml
feeds:
  - name: my-feed
    url: https://example.com/ldes-endpoint
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 60  # seconds
    environment:
      # Optional additional variables
      CUSTOM_VAR: value
```

See [LDES Consumer Documentation](./components/ldes-consumer.md) for details.

### Sembench Configuration

Create a `data/sembench.yaml` file to configure processing pipelines. Refer to the [py-sema documentation](https://github.com/vliz-be-opsci/py-sema) for configuration schema.

## Usage

### Querying Data with SPARQL

Using YASGUI (Web Interface):
1. Navigate to http://localhost:8080
2. Enter your SPARQL query
3. Execute and visualize results

Using Jupyter Notebooks:
```python
from kgap_tools import execute_to_df

# Execute a SPARQL query and get results as a DataFrame
df = execute_to_df('my_query', var1='value1', var2='value2')
```

### Managing LDES Feeds

1. Edit `data/ldes-feeds.yaml` to add/remove feeds
2. Restart the LDES consumer:
   ```bash
   docker compose restart ldes-consumer
   ```

### Viewing Logs

View logs for a specific service:
```bash
docker compose logs -f graphdb
docker compose logs -f jupyter
docker compose logs -f sembench
docker compose logs -f ldes-consumer
```

View logs for an LDES feed container:
```bash
docker logs ldes-consumer-{feed-name}
```

### Stopping and Cleaning Up

Stop all services:
```bash
docker compose down
```

Remove all containers and clean up:
```bash
make docker-stop
make docker-clean
```

## Development

### Project Structure

```
k-gap/
├── docker-compose.yml          # Service orchestration
├── Makefile                    # Build and deployment tasks
├── .env                        # Environment configuration
├── data/                       # Shared data directory
├── notebooks/                  # Jupyter notebooks
├── docs/                       # Documentation
│   ├── index.md               # This file
│   └── components/            # Component-specific docs
├── graphdb/                   # GraphDB image
│   ├── Dockerfile
│   └── kgap/
│       ├── entrypoint-wrap.sh
│       ├── healthy.sh
│       └── template-repo-config.ttl
├── jupyter/                   # Jupyter image
│   ├── Dockerfile
│   └── kgap/
│       ├── entrypoint-wrap.sh
│       ├── requirements.txt
│       └── notebooks/
│           ├── kgap_tools.py
│           └── kgap_template.ipynb
├── sembench/                  # Sembench image
│   ├── Dockerfile
│   └── kgap/
│       ├── main.py
│       └── requirements.txt
└── ldes-consumer/            # LDES Consumer image
    ├── Dockerfile
    ├── README.md
    ├── ldes-feeds.yaml.example
    └── kgap/
        ├── entrypoint.sh
        ├── spawn_instances.py
        ├── logger.py
        └── requirements.txt
```

### Adding a New Component

1. Create a new directory: `{component}/`
2. Add a `Dockerfile`
3. Add component files under `{component}/kgap/`
4. Update `docker-compose.yml` to include the service
5. Update `Makefile` DIMGS variable
6. Create documentation in `docs/components/{component}.md`

### Contributing

See the main repository for contribution guidelines.

## Related Projects

- [py-sema](https://github.com/vliz-be-opsci/py-sema): Python semantic processing library used by Sembench
- [ldes2sparql](https://github.com/rdf-connect/ldes2sparql): LDES harvesting tool
- [GraphDB](https://graphdb.ontotext.com/): RDF database
- [Jupyter](https://jupyter.org/): Interactive computing environment

## License

K-GAP is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/vliz-be-opsci/k-gap/issues
- Organization: https://github.com/vliz-be-opsci
