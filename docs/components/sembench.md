# Sembench Component

The Sembench component is a Python-based semantic processing engine that provides scheduled data processing and transformation capabilities using the [py-sema](https://github.com/vliz-be-opsci/py-sema) library.

## Overview

Sembench acts as an orchestration layer for automated knowledge graph processing tasks, including:
- Scheduled data processing pipelines
- Data transformation and enrichment
- Quality assurance checks
- Automated workflows
- Integration with GraphDB and other components

**Base Image**: `python:3.10`  
**Container Name**: `test_kgap_sembench` (in test setup)

## Features

- **Scheduled Execution**: Run processing tasks at regular intervals
- **Configuration-Driven**: Define workflows via YAML configuration
- **GraphDB Integration**: Direct access to SPARQL endpoint
- **py-sema Integration**: Leverage semantic processing capabilities
- **Extensible**: Add custom processing modules

## Architecture

```
┌────────────────────────────────────────┐
│       Sembench Container               │
├────────────────────────────────────────┤
│                                        │
│  main.py (entrypoint)                 │
│       │                                │
│       ├─▶ Load Configuration          │
│       │   - sembench.yaml              │
│       │   - Environment variables       │
│       │                                │
│       ├─▶ Initialize Sembench          │
│       │   - Set up locations           │
│       │   - Configure scheduler         │
│       │                                │
│       └─▶ Process Data                 │
│           - Execute workflows          │
│           - Scheduled intervals         │
│                                        │
│  Dependencies:                         │
│  - py-sema (from GitHub)               │
│  - pyyaml                              │
│                                        │
│  Volumes:                              │
│  - ./data → /data                     │
│                                        │
└────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEMBENCH_INPUT_PATH` | `/data` | Input data directory |
| `SEMBENCH_OUTPUT_PATH` | `/data` | Output data directory |
| `SEMBENCH_HOME_PATH` | `/data` | Sembench home directory |
| `SEMBENCH_CONFIG_PATH` | `/data/sembench.yaml` | Configuration file path |
| `SCHEDULER_INTERVAL_SECONDS` | `86400` | Processing interval (24 hours) |

**Note**: The old environment variable names (`INPUT_DATA_LOCATION`, `OUTPUT_DATA_LOCATION`, `SEMBENCH_DATA_LOCATION`) are deprecated. Use the new `*_PATH` variants.

### Dependencies

The Sembench image includes (defined in `sembench/kgap/requirements.txt`):

```
git+https://github.com/vliz-be-opsci/py-sema.git@main
pyyaml
```

## File Structure

```
sembench/
├── Dockerfile            # Image definition
└── kgap/
    ├── main.py          # Main entrypoint script
    └── requirements.txt # Python dependencies
```

### main.py

The entrypoint script initializes and runs Sembench:

```python
#!/usr/bin/env python
import os
from pathlib import Path
from sema.bench import Sembench
from sema.bench.core import locations_from_environ

sb = Sembench(
    locations=locations_from_environ(),
    sembench_config_path=os.getenv("SEMBENCH_CONFIG_PATH"),
    scheduler_interval_seconds=os.getenv("SCHEDULER_INTERVAL_SECONDS"),
)

sb.process()
```

Key components:
- **locations_from_environ()**: Reads `SEMBENCH_INPUT_PATH`, `SEMBENCH_OUTPUT_PATH`, `SEMBENCH_HOME_PATH` from environment
- **sembench_config_path**: Path to YAML configuration file
- **scheduler_interval_seconds**: How often to run processing tasks
- **sb.process()**: Starts the processing loop

## Usage

### Configuration File

Create a `data/sembench.yaml` file to define processing workflows. The exact schema depends on your py-sema configuration needs.

**Basic structure**:
```yaml
# Sembench configuration
workflows:
  - name: my-workflow
    steps:
      - type: extract
        # ... step configuration
      
      - type: transform
        # ... step configuration
      
      - type: load
        # ... step configuration
```

For detailed configuration options, refer to the [py-sema documentation](https://github.com/vliz-be-opsci/py-sema).

### Starting Sembench

Sembench starts automatically when the container launches and runs in a continuous loop:

```bash
docker compose up -d sembench
```

### Viewing Logs

Monitor processing activity:

```bash
docker compose logs -f sembench
```

### Manual Processing Trigger

To trigger processing manually (outside the scheduled interval):

```bash
# Restart the container to trigger immediate processing
docker compose restart sembench
```

## Integration with GraphDB

Sembench can query and update the GraphDB repository. Configuration typically happens in your `sembench.yaml`:

```yaml
# Example GraphDB connection in workflow
sparql_endpoint: http://graphdb:7200/repositories/kgap
```

## Common Use Cases

### Use Case 1: Scheduled Data Enrichment

Automatically enrich incoming LDES data on a schedule:

```yaml
workflows:
  - name: enrich-data
    schedule: daily
    steps:
      - type: sparql_query
        endpoint: http://graphdb:7200/repositories/kgap
        query: |
          SELECT ?subject ?predicate ?object
          WHERE {
            ?subject a <http://example.org/NeedsEnrichment> .
            ?subject ?predicate ?object .
          }
      
      - type: enrichment
        # enrichment logic
      
      - type: sparql_update
        endpoint: http://graphdb:7200/repositories/kgap
        # update query
```

### Use Case 2: Data Quality Checks

Run periodic quality assurance:

```yaml
workflows:
  - name: quality-checks
    schedule: hourly
    steps:
      - type: validation
        rules:
          - check: required_properties
            properties: [rdfs:label, dc:created]
          
          - check: data_types
            # type checking rules
      
      - type: report
        output: /data/qa-reports/
```

### Use Case 3: Data Transformation

Transform RDF data from one vocabulary to another:

```yaml
workflows:
  - name: vocabulary-mapping
    steps:
      - type: sparql_construct
        endpoint: http://graphdb:7200/repositories/kgap
        query: |
          CONSTRUCT {
            ?s <http://new-vocab.org/property> ?o .
          }
          WHERE {
            ?s <http://old-vocab.org/property> ?o .
          }
      
      - type: load
        target: http://graphdb:7200/repositories/kgap/statements
```

## Processing Workflow

1. **Startup**: Container starts and loads configuration
2. **Initialization**: Sembench reads environment variables and config file
3. **Processing Loop**:
   - Execute configured workflows
   - Wait for `SCHEDULER_INTERVAL_SECONDS`
   - Repeat
4. **Shutdown**: Graceful shutdown on container stop

```
┌─────────────────────────────────────┐
│          Sembench Lifecycle         │
└─────────────────────────────────────┘
         │
         ▼
    Load Config
         │
         ▼
    ┌─────────────┐
    │  Process    │◀─────┐
    │  Workflows  │      │
    └─────────────┘      │
         │               │
         ▼               │
    Wait (interval)      │
         │               │
         └───────────────┘
```

## Extending Sembench

### Adding Custom Processing Modules

1. **Extend py-sema**: Create custom processing modules in py-sema
2. **Update Configuration**: Reference custom modules in `sembench.yaml`
3. **Rebuild Image**: If custom code is needed, extend the Dockerfile

**Example Dockerfile extension**:
```dockerfile
FROM python:3.10
COPY ./kgap /kgap
RUN python -m pip install -r /kgap/requirements.txt

# Add custom modules
COPY ./custom_modules /custom_modules
RUN python -m pip install -e /custom_modules

RUN chmod +x /kgap/main.py
ENTRYPOINT ["/kgap/main.py"]
```

### Custom main.py

For advanced use cases, you can customize `main.py`:

```python
#!/usr/bin/env python
import os
import logging
from sema.bench import Sembench
from sema.bench.core import locations_from_environ

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom initialization
logger.info("Starting custom Sembench configuration")

# Initialize with custom settings
sb = Sembench(
    locations=locations_from_environ(),
    sembench_config_path=os.getenv("SEMBENCH_CONFIG_PATH"),
    scheduler_interval_seconds=int(os.getenv("SCHEDULER_INTERVAL_SECONDS", 86400)),
    # Add custom parameters here
)

# Custom pre-processing
logger.info("Running custom pre-processing")
# ... custom logic ...

# Start processing
logger.info("Starting Sembench processing loop")
sb.process()
```

## Troubleshooting

### Container Exits Immediately

**Check logs**:
```bash
docker compose logs sembench
```

**Common causes**:
- Missing or invalid `sembench.yaml` configuration
- Incorrect environment variable values
- py-sema import errors

**Solution**: Verify configuration file exists and is valid YAML.

### Configuration Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: '/data/sembench.yaml'`

**Solution**: Ensure `sembench.yaml` exists in the `./data` directory on the host.

```bash
ls -la ./data/sembench.yaml
```

### Cannot Connect to GraphDB

**Check network connectivity**:
```bash
docker compose exec sembench curl http://graphdb:7200/
```

**Verify GraphDB is healthy**:
```bash
docker compose ps graphdb
```

**Solution**: Ensure GraphDB is running and healthy before starting Sembench.

### Processing Not Running on Schedule

**Check logs for errors**:
```bash
docker compose logs -f sembench
```

**Verify interval setting**:
```bash
docker compose exec sembench printenv SCHEDULER_INTERVAL_SECONDS
```

### Memory Issues

For large-scale processing, you may need to allocate more memory:

**In docker-compose.yml**:
```yaml
sembench:
  # ... other config ...
  deploy:
    resources:
      limits:
        memory: 4G
```

## Best Practices

1. **Configuration Management**: Store `sembench.yaml` in version control
2. **Logging**: Monitor logs regularly for processing errors
3. **Incremental Processing**: Design workflows to handle incremental updates
4. **Error Handling**: Configure retry logic for transient failures
5. **Testing**: Test workflows with small datasets before production
6. **Documentation**: Document custom workflows and processing logic
7. **Monitoring**: Set up alerts for processing failures

## Performance Optimization

### Optimize Processing Intervals

Balance between data freshness and resource usage:

```bash
# More frequent updates (every 1 hour)
SCHEDULER_INTERVAL_SECONDS=3600

# Daily processing (default)
SCHEDULER_INTERVAL_SECONDS=86400

# Weekly processing
SCHEDULER_INTERVAL_SECONDS=604800
```

### Batch Processing

For large datasets, process in batches:

```yaml
workflows:
  - name: batch-processing
    steps:
      - type: batch_query
        batch_size: 1000  # Process 1000 items at a time
        # ... configuration
```

### Parallel Processing

Consider parallelizing independent workflows (requires custom implementation or py-sema features).

## py-sema Integration

Sembench is built on py-sema, which provides:

- **Data Source Connectors**: SPARQL endpoints, files, APIs
- **Processing Pipelines**: Extract, Transform, Load (ETL) patterns
- **Workflow Orchestration**: Dependency management, scheduling
- **Validation**: Data quality checks

For full capabilities, refer to:
- [py-sema Repository](https://github.com/vliz-be-opsci/py-sema)
- [py-sema Documentation](https://github.com/vliz-be-opsci/py-sema/tree/main/docs)

## Related Documentation

- [Main Documentation](../index.md)
- [GraphDB Component](./graphdb.md) - Data storage
- [LDES Consumer Component](./ldes-consumer.md) - Data ingestion
- [Jupyter Component](./jupyter.md) - Interactive analysis
- [py-sema](https://github.com/vliz-be-opsci/py-sema) - Processing library
