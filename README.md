# K-GAP

**Knowledge Graph Analysis Platform**

A microservices-based platform for building, managing, and analyzing knowledge graphs using SPARQL and linked data technologies.

## 📚 Documentation

**[→ Full Documentation](docs/index.md)**

Comprehensive documentation is available in the `docs/` directory:
- [Getting Started Guide](docs/index.md#getting-started)
- [Architecture Overview](docs/index.md#architecture)
- [Configuration Guide](docs/index.md#configuration)
- [Component Documentation](docs/index.md#components)

### Component-Specific Documentation

- [GraphDB Component](docs/components/graphdb.md) - RDF triple store and SPARQL endpoint
- [Jupyter Component](docs/components/jupyter.md) - Interactive notebooks for data analysis
- [Sembench Component](docs/components/sembench.md) - Automated semantic processing
- [LDES Consumer Component](docs/components/ldes-consumer.md) - Multi-feed LDES harvesting

## Overview

K-GAP provides a complete, containerized environment for working with knowledge graphs. It combines specialized microservices that work together to:

- **Store and query** RDF data using GraphDB
- **Harvest and ingest** data from LDES (Linked Data Event Streams) feeds
- **Analyze and process** knowledge graphs using Python tools (Sembench)
- **Explore data** interactively through Jupyter notebooks

### Key Features

- **Microservices Architecture**: Each component runs as an independent Docker container
- **LDES Integration**: Automated harvesting from multiple Linked Data Event Streams
- **Interactive Analysis**: Jupyter notebooks for data exploration and visualization
- **Scalable Storage**: GraphDB repository with configurable resources
- **Automated Processing**: Scheduled data processing pipelines via Sembench

## Quick Start

### Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 16GB RAM recommended

### Start Up

```bash
# 1. Clone the repository
git clone https://github.com/vliz-be-opsci/k-gap.git
cd k-gap

# 2. Configure environment
cp dotenv-example .env
# Edit .env to customize settings if needed

# 3. Create data directories
mkdir -p ./data ./notebooks

# 4. Start all services
docker compose up -d
```

### Access Services

Once started, access the following services:

- **GraphDB Workbench**: http://localhost:7200
- **Jupyter Notebooks**: http://localhost:8889
- **YASGUI (SPARQL UI)**: http://localhost:8080

## Components

K-GAP consists of four main Docker images:

### kgap-graphdb

GraphDB is the core RDF triple store providing SPARQL query capabilities, persistent storage, and SHACL validation.

- **Base**: `ontotext/graphdb:10.4.4`
- **Port**: 7200
- **Features**: SPARQL queries, SHACL validation, full-text search
- **Docs**: [GraphDB Component](docs/components/graphdb.md)

### kgap-jupyter

Interactive notebook environment for data analysis with pre-installed RDF/SPARQL tools.

- **Base**: `jupyter/base-notebook`
- **Port**: 8889
- **Docs**: [Jupyter Component](docs/components/jupyter.md)

### kgap-sembench

Python-based semantic processing engine for scheduled data processing tasks.

- **Base**: `python:3.10`
- **Docs**: [Sembench Component](docs/components/sembench.md)

### kgap-ldes-consumer

Multi-feed LDES harvesting service that wraps [ldes2sparql](https://github.com/rdf-connect/ldes2sparql).

- **Base**: `python:3.10-slim`
- **Docs**: [LDES Consumer Component](docs/components/ldes-consumer.md) | [README](ldes-consumer/README.md)

## Building Images

Build all Docker images locally:

```bash
make docker-build
```

Build with a specific tag:

```bash
make BUILD_TAG=0.2.0 docker-build
```

## Publishing Images

Build and push images to a container registry:

```bash
make REG_NS=ghcr.io/vliz-be-opsci/kgap docker-push
```

## Published Docker Images

Images are automatically built and published to GitHub Container Registry on release:

- `ghcr.io/vliz-be-opsci/kgap/kgap_graphdb:latest`
- `ghcr.io/vliz-be-opsci/kgap/kgap_jupyter:latest`
- `ghcr.io/vliz-be-opsci/kgap/kgap_sembench:latest`
- `ghcr.io/vliz-be-opsci/kgap/kgap_ldes-consumer:latest`

## Configuration

K-GAP is configured through environment variables in a `.env` file. See [Configuration Guide](docs/index.md#configuration) for details.

Key configuration areas:
- GraphDB repository settings
- LDES feed configuration
- Sembench processing schedules
- Resource allocation

## Usage Examples

### Query Data with SPARQL

Using YASGUI web interface:
```
Navigate to http://localhost:8080 and run SPARQL queries
```

Using Jupyter notebooks:
```python
from kgap_tools import execute_to_df

df = execute_to_df('my_query', param1='value1')
display(df)
```

### Manage LDES Feeds

Edit `data/ldes-feeds.yaml` to add/remove feeds, then:
```bash
docker compose restart ldes-consumer
```

### View Logs

```bash
docker compose logs -f graphdb
docker compose logs -f jupyter
docker compose logs -f sembench
docker compose logs -f ldes-consumer
```

## Development

See the [Development section](docs/index.md#development) in the documentation for:
- Project structure
- Adding new components
- Contributing guidelines

## Related Projects

- [py-sema](https://github.com/vliz-be-opsci/py-sema) - Python semantic processing library
- [ldes2sparql](https://github.com/rdf-connect/ldes2sparql) - LDES harvesting tool
- [GraphDB](https://graphdb.ontotext.com/) - RDF database
- [Jupyter](https://jupyter.org/) - Interactive computing

## License

K-GAP is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Support

For issues and questions:
- **GitHub Issues**: https://github.com/vliz-be-opsci/k-gap/issues
- **Organization**: https://github.com/vliz-be-opsci
