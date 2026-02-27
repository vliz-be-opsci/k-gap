---
title: FAQ
nav_order: 6
---

# Frequently Asked Questions (FAQ)

Common questions and answers about K-GAP.

## General Questions

### What is K-GAP?

K-GAP (Knowledge Graph Analysis Platform) is a microservices-based platform for building, managing, and analyzing knowledge graphs. It provides a complete containerized environment with GraphDB for storage, Jupyter for analysis, Sembench for processing, and LDES Consumer for data harvesting.

### Who should use K-GAP?

K-GAP is designed for:
- Data scientists working with linked data
- Researchers building knowledge graphs
- Organizations harvesting LDES feeds
- Teams needing SPARQL query and analysis capabilities
- Anyone working with RDF/semantic web technologies

### What are the system requirements?

**Minimum**:
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM
- 10GB free disk space

**Recommended**:
- 16GB+ RAM
- 20GB+ free disk space
- 4+ CPU cores
- SSD storage

### Is K-GAP production-ready?

K-GAP is designed as a development and analysis platform. For production use:
- Enable GraphDB authentication
- Use persistent volumes for data
- Set up SSL/TLS for web interfaces
- Configure appropriate resource limits
- Implement backup strategies
- Monitor logs and performance

## Installation and Setup

### How do I install K-GAP?

```bash
git clone https://github.com/vliz-be-opsci/k-gap.git
cd k-gap
cp dotenv-example .env
mkdir -p ./data ./notebooks
docker compose up -d
```

See [Getting Started](./index.md#getting-started) for details.

### Why does GraphDB take so long to start?

GraphDB needs time to:
- Initialize the repository
- Build indexes
- Load configuration

For repositories with complex rulesets or inference, increase the health check `start_period` in `docker-compose.yml`:

```yaml
healthcheck:
  start_period: 30s  # Increase from default 1s
```

### Can I use my own GraphDB installation?

Yes, but you'll need to configure the connection in each component:
- Update `GDB_BASE` in `.env`
- Ensure network connectivity
- Configure authentication if needed

### How do I persist data across restarts?

Data in the `./data` directory is automatically persisted. For GraphDB data:

```yaml
# Add to docker-compose.yml
services:
  graphdb:
    volumes:
      - ./data:/root/graphdb-import/data
      - graphdb-home:/opt/graphdb/home  # Add this

volumes:
  graphdb-home:  # Define volume
```

## Configuration

### How do I change GraphDB memory settings?

Edit `.env`:
```bash
GDB_JAVA_OPTS="-Xms16g -Xmx32g -Dcom.ontotext.graphdb.monitoring.jmx=true"
```

Then restart:
```bash
docker compose restart graphdb
```

### How do I add a new LDES feed?

1. Edit `data/ldes-feeds.yaml`:
```yaml
feeds:
  - name: new-feed
    url: https://example.com/ldes
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 300
```

2. Restart the consumer:
```bash
docker compose restart ldes-consumer
```

### Can I run multiple GraphDB repositories?

Yes, see [Multi-Repository Setup](./advanced-topics.md#multi-repository-setup) in the advanced topics.

### How do I change the Jupyter port?

Edit `docker-compose.yml`:
```yaml
jupyter:
  ports:
    - "9999:8888"  # Change from 8889:8888
```

### Where do I put Sembench configuration?

Create `data/sembench.yaml` with your workflow configuration. See [Sembench Component](./components/sembench.md) for details.

## Usage

### How do I query GraphDB?

Three ways:

1. **YASGUI Web UI**: http://localhost:8080
2. **GraphDB Workbench**: http://localhost:7200
3. **Jupyter Notebooks**:
```python
from kgap_tools import execute_to_df
df = execute_to_df('my_query')
```

### How do I import RDF data?

**Via GraphDB Workbench**:
1. Navigate to http://localhost:7200
2. Select repository
3. Go to Import → RDF
4. Upload files

**Via REST API**:
```bash
curl -X POST \
  http://localhost:7200/repositories/kgap/statements \
  -H 'Content-Type: text/turtle' \
  --data-binary '@data.ttl'
```

**Via Mounted Volume**:
Place files in `./data` and import via workbench.

### How do I export data?

```bash
# Export all data
curl 'http://localhost:7200/repositories/kgap/statements' \
  -H 'Accept: text/turtle' \
  > export.ttl

# Export as JSON-LD
curl 'http://localhost:7200/repositories/kgap/statements' \
  -H 'Accept: application/ld+json' \
  > export.jsonld
```

### How do I clear all data?

```bash
# Via REST API
curl -X DELETE http://localhost:7200/repositories/kgap/statements

# Or via SPARQL
# In YASGUI or workbench:
# DELETE WHERE { ?s ?p ?o }
```

### How do I create custom query templates?

1. Create `notebooks/queries/my_query.sparql`:
```sparql
SELECT ?entity ?label
WHERE {
  ?entity rdfs:label ?label .
  FILTER(CONTAINS(?label, "${search_term}"))
}
LIMIT ${limit}
```

2. Use in Jupyter:
```python
from kgap_tools import execute_to_df
df = execute_to_df('my_query', search_term='marine', limit=100)
```

## Troubleshooting

### GraphDB is running but I can't access the workbench

Check:
1. Container is running: `docker compose ps graphdb`
2. Port is exposed: `curl http://localhost:7200`
3. Firewall allows port 7200
4. No other service using port 7200: `lsof -i :7200`

### Jupyter notebooks won't connect to GraphDB

Verify in a notebook:
```python
import os
print(f"GDB_BASE: {os.getenv('GDB_BASE')}")
print(f"GDB_REPO: {os.getenv('GDB_REPO')}")

from kgap_tools import GDB
result = GDB.query("ASK { ?s ?p ?o }")
print(result)
```

If it fails:
- Ensure GraphDB is healthy: `docker compose ps`
- Check network connectivity
- Verify environment variables in `.env`

### LDES feed isn't harvesting data

Debug steps:

1. Check feed container logs:
```bash
docker logs ldes-consumer-{feed-name}
```

2. Verify feed URL:
```bash
curl -I {feed-url}
```

3. Check GraphDB endpoint:
```bash
curl http://localhost:7200/repositories/kgap/statements
```

4. Verify configuration:
```bash
cat data/ldes-feeds.yaml
```

### Out of memory errors

Increase memory allocation:

**For GraphDB**:
```bash
# In .env
GDB_JAVA_OPTS="-Xms16g -Xmx32g"
```

**For Docker**:
```yaml
# In docker-compose.yml
services:
  graphdb:
    deploy:
      resources:
        limits:
          memory: 40G
```

### Container exits immediately

Check logs:
```bash
docker compose logs {service-name}
```

Common causes:
- Configuration file missing (sembench, ldes-consumer)
- Invalid environment variables
- Port already in use
- Insufficient memory

### Slow SPARQL queries

Optimization strategies:

1. Add indexes to GraphDB repository configuration
2. Use `LIMIT` clauses
3. Filter early in queries
4. Avoid `OPTIONAL` when possible
5. Use specific predicates instead of `?p`
6. Enable query logging to identify bottlenecks

See [Performance Optimization](./advanced-topics.md#performance-optimization).

### Can't build Docker images

Issues and solutions:

**Docker daemon not running**:
```bash
sudo systemctl start docker
```

**Insufficient disk space**:
```bash
docker system prune -a
```

**Network issues during build**:
- Check internet connection
- Try again (transient failures)
- Use local mirror for packages

## Data and LDES

### What LDES feeds are supported?

Any LDES feed that follows the [LDES specification](https://w3id.org/ldes/specification). The underlying `ldes2sparql` tool handles:
- Pagination
- Version materialization
- State management

### How do I monitor LDES harvesting?

```bash
# View consumer logs
docker compose logs -f ldes-consumer

# View specific feed logs
docker logs -f ldes-consumer-{feed-name}

# Check GraphDB for new data
# Query recent additions by timestamp if available
```

### Can I pause LDES harvesting?

```bash
# Stop specific feed
docker stop ldes-consumer-{feed-name}

# Stop all feeds
docker compose stop ldes-consumer

# Resume
docker compose start ldes-consumer
```

### How do I handle LDES authentication?

Add to feed configuration in `data/ldes-feeds.yaml`:
```yaml
feeds:
  - name: authenticated-feed
    url: https://secure.example.com/ldes
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      AUTH_TOKEN: "Bearer your-token-here"
```

## Integration

### Can I integrate with other tools?

Yes! K-GAP components expose standard interfaces:

- **GraphDB**: SPARQL 1.1 endpoint
- **Jupyter**: Standard Jupyter notebook server
- **Docker**: Standard Docker containers

You can integrate with:
- Python scripts
- R (via SPARQL)
- Other RDF tools
- CI/CD pipelines
- Monitoring systems

### How do I use K-GAP in a CI/CD pipeline?

Example GitHub Actions workflow:

```yaml
name: Test Knowledge Graph
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start K-GAP
        run: |
          cp dotenv-example .env
          docker compose up -d
          sleep 30  # Wait for services
      - name: Run tests
        run: |
          # Your SPARQL tests here
          curl http://localhost:7200/repositories/kgap
```

### Can I connect external tools to GraphDB?

Yes, use the SPARQL endpoint:
```
http://localhost:7200/repositories/kgap
```

Works with:
- Apache Jena
- RDF4J applications
- Protégé
- Any SPARQL 1.1 client

## Performance

### How much data can K-GAP handle?

Depends on resources:

- **Small** (< 1M triples): Default settings work fine
- **Medium** (1M - 10M triples): Increase GraphDB memory to 16-32GB
- **Large** (10M - 100M triples): Increase memory to 64GB+, consider scaling
- **Very Large** (> 100M triples): Consider GraphDB cluster or specialized setup

### How do I scale K-GAP?

For larger deployments:

1. **Vertical scaling**: Increase resources (CPU, memory)
2. **GraphDB clustering**: Use GraphDB Enterprise cluster
3. **Separate services**: Run components on different machines
4. **Load balancing**: Use reverse proxy for query load
5. **Optimize queries**: Index frequently-used predicates

## Security

### Is K-GAP secure by default?

No. The default configuration is for development:
- No authentication on Jupyter
- No authentication on GraphDB
- Exposed ports

For production:
- Enable authentication
- Use SSL/TLS
- Restrict network access
- Use secrets management
- Regular updates

### How do I enable authentication?

**GraphDB**: Configure in workbench under Setup → Users and Access
**Jupyter**: Remove `NOTEBOOK_ARGS` token disabling in `.env`

### Should I expose K-GAP to the internet?

Not with default settings. For public access:
- Use reverse proxy (nginx, Traefik)
- Enable SSL/TLS
- Configure authentication
- Implement rate limiting
- Monitor access logs

## Community and Support

### Where can I get help?

- **Documentation**: https://vliz-be-opsci.github.io/k-gap/
- **GitHub Issues**: https://github.com/vliz-be-opsci/k-gap/issues
- **Organization**: https://github.com/vliz-be-opsci

### How do I report bugs?

Open an issue on GitHub with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Logs (if relevant)
- Environment details

### Can I contribute?

Yes! Contributions welcome:
- Bug reports
- Feature requests
- Documentation improvements
- Code contributions
- Example notebooks

See the repository for contribution guidelines.

### What license is K-GAP under?

MIT License. See [LICENSE](../LICENSE).

## Related Documentation

- [Main Documentation](./index.md)
- [Quick Reference](./quick-reference.md)
- [GraphDB Component](./components/graphdb.md)
- [Jupyter Component](./components/jupyter.md)
- [Sembench Component](./components/sembench.md)
- [LDES Consumer](./components/ldes-consumer.md)
- [Advanced Topics](./advanced-topics.md)
