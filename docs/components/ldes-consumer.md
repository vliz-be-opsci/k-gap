# LDES Consumer Component

The LDES Consumer is a multi-feed harvesting service that wraps [ldes2sparql](https://github.com/maregraph-eu/ldes2sparql) to automatically ingest data from multiple Linked Data Event Streams (LDES) into GraphDB.

## Overview

The LDES Consumer service reads a YAML configuration file containing multiple LDES feeds and spawns a separate `ldes2sparql` Docker container for each feed. This allows K-GAP to harvest data from multiple heterogeneous sources simultaneously.

**Base Image**: `python:3.10-slim` (with Docker CLI)  
**Container Name**: `test_kgap_ldes_consumer` (in test setup)  
**Requires**: Docker socket access (`/var/run/docker.sock`)

## Key Features

- **Multi-Feed Support**: Harvest from multiple LDES sources simultaneously
- **Container Spawning**: Dynamically creates ldes2sparql containers
- **Network Integration**: Spawned containers join the same Docker network
- **Configurable Polling**: Set different polling intervals per feed
- **Structured Logging**: Configurable log levels for debugging
- **Automatic Monitoring**: Tracks spawned container health

## Architecture

```
┌────────────────────────────────────────────────────────┐
│           LDES Consumer Container                      │
├────────────────────────────────────────────────────────┤
│                                                         │
│  entrypoint.sh                                         │
│       │                                                 │
│       └─▶ spawn_instances.py                           │
│              │                                          │
│              ├─▶ Load ldes-feeds.yaml                  │
│              │                                          │
│              ├─▶ For each feed:                        │
│              │    └─▶ docker run ldes2sparql           │
│              │        (new container)                  │
│              │                                          │
│              └─▶ Monitor containers                    │
│                                                         │
└────────────────────────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Spawned Containers         │
        ├─────────────────────────────┤
        │                             │
        │  ldes-consumer-feed1        │
        │    (ldes2sparql)            │
        │      └─▶ GraphDB            │
        │                             │
        │  ldes-consumer-feed2        │
        │    (ldes2sparql)            │
        │      └─▶ GraphDB            │
        │                             │
        │  ldes-consumer-feed3        │
        │    (ldes2sparql)            │
        │      └─▶ GraphDB            │
        │                             │
        └─────────────────────────────┘
```

## How It Works

1. **Startup**: The LDES Consumer container starts and reads the configuration file
2. **Container Spawning**: For each feed in the configuration:
   - Spawns a new Docker container running `ldes2sparql`
   - Configures the container with feed-specific parameters
   - Attaches the container to the Docker Compose network
   - Labels the container with the Docker Compose project name
3. **Monitoring**: The service monitors spawned containers
4. **Data Harvesting**: Each `ldes2sparql` container:
   - Polls its assigned LDES feed at the configured interval
   - Ingests new data into the GraphDB SPARQL endpoint
   - Maintains state to track harvested items
5. **Graceful Shutdown**: All spawned containers are stopped when the service terminates

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LDES_CONFIG_FILE` | `/data/ldes-feeds.yaml` | Path to YAML configuration file |
| `LDES2SPARQL_IMAGE` | `ghcr.io/maregraph-eu/ldes2sparql:latest` | Docker image for ldes2sparql |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `DOCKER_NETWORK` | `${COMPOSE_PROJECT_NAME}_default` | Docker network for spawned containers |
| `COMPOSE_PROJECT_NAME` | `kgap` | Docker Compose project name |

### LDES Feeds Configuration File

Create a `data/ldes-feeds.yaml` file with the following structure:

```yaml
feeds:
  - name: example-feed-1
    url: http://example.com/ldes-feed-1
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 60  # seconds (optional, defaults to 60)
    environment:  # optional additional environment variables
      # Add any additional environment variables needed by ldes2sparql here
      # EXAMPLE_VAR: value

  - name: example-feed-2
    url: http://example.com/ldes-feed-2
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 120
```

#### Required Fields

- **name**: Unique identifier for the feed (used in container naming)
- **url**: URL of the LDES feed
- **sparql_endpoint**: SPARQL endpoint where data should be ingested

#### Optional Fields

- **polling_interval**: How often to poll the feed in seconds (default: 60)
  - Note: Converted to milliseconds internally as `POLLING_FREQUENCY`
- **environment**: Additional environment variables to pass to the ldes2sparql container

### Example Configuration

```yaml
feeds:
  # Marine data from IOC
  - name: marine-observations
    url: https://marinedata.org/ldes/observations
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 300  # Poll every 5 minutes
    environment:
      CUSTOM_HEADER: "Bearer token123"
  
  # Biodiversity data
  - name: biodiversity-specimens
    url: https://biodiversity.org/ldes/specimens
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 600  # Poll every 10 minutes
  
  # Research publications
  - name: research-publications
    url: https://research.org/ldes/publications
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 3600  # Poll every hour
```

## File Structure

```
ldes-consumer/
├── Dockerfile                    # Image definition
├── README.md                     # Component-specific README
├── ldes-feeds.yaml.example       # Example configuration
└── kgap/
    ├── entrypoint.sh            # Container entrypoint
    ├── spawn_instances.py       # Main spawner script
    ├── logger.py                # Logging utilities
    └── requirements.txt         # Python dependencies
```

### spawn_instances.py

The core script that:
- Loads the YAML configuration
- Spawns Docker containers for each feed
- Monitors container health
- Handles graceful shutdown

Key functions:
- **load_config()**: Parse YAML configuration
- **spawn_ldes2sparql_instance()**: Create and start a container for a feed
- **signal_handler()**: Handle shutdown signals (SIGTERM, SIGINT)
- **main()**: Orchestrate the spawning and monitoring loop

### logger.py

Provides structured logging with configurable levels:

```python
import logging

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Set up a logger with the specified name and level"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

## Usage

### Initial Setup

1. **Copy example configuration**:
   ```bash
   cp ldes-consumer/ldes-feeds.yaml.example data/ldes-feeds.yaml
   ```

2. **Edit configuration** with your LDES feeds:
   ```bash
   nano data/ldes-feeds.yaml
   ```

3. **Ensure ldes2sparql image is available**:
   ```bash
   docker pull ghcr.io/maregraph-eu/ldes2sparql:latest
   ```

### Starting the Service

```bash
docker compose up -d ldes-consumer
```

### Viewing Logs

**LDES Consumer service logs**:
```bash
docker compose logs -f ldes-consumer
```

**Individual feed container logs**:
```bash
docker logs ldes-consumer-{feed-name}

# Example:
docker logs ldes-consumer-marine-observations
```

### Managing Feeds

**Add a new feed**:
1. Edit `data/ldes-feeds.yaml` and add a new feed entry
2. Restart the LDES consumer:
   ```bash
   docker compose restart ldes-consumer
   ```

**Remove a feed**:
1. Stop and remove the specific container:
   ```bash
   docker stop ldes-consumer-{feed-name}
   docker rm ldes-consumer-{feed-name}
   ```
2. Remove the feed from `data/ldes-feeds.yaml`
3. Restart the LDES consumer

**Modify feed configuration**:
1. Update `data/ldes-feeds.yaml`
2. Stop the old container:
   ```bash
   docker stop ldes-consumer-{feed-name}
   docker rm ldes-consumer-{feed-name}
   ```
3. Restart the LDES consumer to spawn with new configuration:
   ```bash
   docker compose restart ldes-consumer
   ```

### Container Naming Convention

Spawned containers follow the naming convention:
```
ldes-consumer-{feed-name}
```

For example, a feed named `marine-observations` will create a container named:
```
ldes-consumer-marine-observations
```

### Network Integration

All spawned `ldes2sparql` containers are attached to the same Docker network as the main K-GAP stack (typically `kgap_default`), allowing them to:
- Communicate with GraphDB
- Access other K-GAP services
- Operate within the same network security boundary

## State Management

Each LDES feed container maintains its own state in a Docker volume:
```
/data/ldes-state-{feed-name}
```

This state includes:
- Last processed item
- Harvesting metadata
- Continuation tokens

State persists across container restarts, ensuring:
- No duplicate data ingestion
- Efficient incremental updates
- Recovery from failures

## Troubleshooting

### Service Won't Start

**Check configuration file**:
```bash
cat data/ldes-feeds.yaml
# Verify YAML syntax
python -c "import yaml; yaml.safe_load(open('data/ldes-feeds.yaml'))"
```

**Check Docker socket access**:
```bash
docker compose exec ldes-consumer docker ps
```

### Feed Container Fails to Start

**Check individual container logs**:
```bash
docker logs ldes-consumer-{feed-name}
```

**Common issues**:
- Invalid LDES URL (404, unreachable)
- Invalid SPARQL endpoint
- Network connectivity issues
- Insufficient resources

**Verify LDES feed is accessible**:
```bash
curl -I {ldes-feed-url}
```

**Verify GraphDB endpoint**:
```bash
curl http://localhost:7200/repositories/kgap/statements
```

### No Data Being Ingested

**Check feed container logs**:
```bash
docker logs -f ldes-consumer-{feed-name}
```

**Verify LDES feed has data**:
```bash
curl {ldes-feed-url} | head -n 50
```

**Check GraphDB repository**:
```sparql
SELECT (COUNT(*) as ?count)
WHERE { ?s ?p ?o }
```

### Container Keeps Restarting

**Check for errors in logs**:
```bash
docker logs ldes-consumer-{feed-name}
```

**Possible causes**:
- Memory limits
- Invalid configuration passed to ldes2sparql
- Network timeouts
- LDES endpoint unavailable

### Debugging Mode

Enable detailed logging:

```bash
# In .env file:
LOG_LEVEL=DEBUG

# Restart service:
docker compose restart ldes-consumer
```

This will show:
- Docker commands being executed
- Container creation details
- State checking results

## Performance Tuning

### Polling Intervals

Balance between data freshness and load:

```yaml
# High-frequency updates (every minute)
polling_interval: 60

# Moderate updates (every 5 minutes)
polling_interval: 300

# Low-frequency updates (every hour)
polling_interval: 3600
```

### Resource Allocation

For many feeds or high-volume feeds, increase resources:

```yaml
# In docker-compose.yml
ldes-consumer:
  # ... other config ...
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '2'
```

### Concurrent Harvesting

The service spawns one container per feed, enabling parallel harvesting. Each container operates independently.

## Security Considerations

### Docker Socket Access

The LDES Consumer requires access to `/var/run/docker.sock` to spawn containers. This grants significant privileges. In production:

- Limit access to trusted configuration files
- Use read-only mounts where possible
- Consider using Docker API over TCP with TLS
- Monitor spawned containers

### Network Security

- Spawned containers join the Docker Compose network
- Ensure network policies restrict access appropriately
- Use HTTPS for LDES feed URLs when available
- Authenticate GraphDB endpoint if needed

## Best Practices

1. **Test Feeds Individually**: Before adding to production, test each feed URL
2. **Monitor Logs**: Regularly check logs for errors or warnings
3. **Set Appropriate Intervals**: Balance freshness vs. load
4. **Use Descriptive Names**: Name feeds clearly for easy identification
5. **Document Custom Variables**: If using `environment`, document their purpose
6. **Version Configuration**: Keep `ldes-feeds.yaml` in version control
7. **State Backups**: Backup state volumes to prevent re-harvesting all data

## Integration with Other Components

### GraphDB

All harvested data flows into GraphDB:
```
LDES Feed → ldes2sparql → GraphDB SPARQL Endpoint
```

### Sembench

Sembench can process LDES-harvested data:
- Run transformation workflows after ingestion
- Enrich LDES data with additional context
- Validate incoming data quality

### Jupyter

Analyze harvested data interactively:
```python
from kgap_tools import execute_to_df

# Query recently ingested data
df = execute_to_df('recent_ldes_data')
display(df)
```

## Advanced Configuration

### Custom ldes2sparql Image

Use a custom or specific version of ldes2sparql:

```bash
# In .env:
LDES2SPARQL_IMAGE=ghcr.io/maregraph-eu/ldes2sparql:v1.2.3
```

### Feed-Specific Environment Variables

Pass additional configuration to individual feeds:

```yaml
feeds:
  - name: authenticated-feed
    url: https://secure.example.com/ldes
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      AUTH_TOKEN: "Bearer xyz123"
      CUSTOM_HEADER: "X-API-Key: abc456"
```

## Related Documentation

- [Main Documentation](../index.md)
- [LDES Consumer README](../../ldes-consumer/README.md) - Detailed component documentation
- [GraphDB Component](./graphdb.md) - Target data store
- [ldes2sparql](https://github.com/maregraph-eu/ldes2sparql) - Underlying harvesting tool
- [LDES Specification](https://w3id.org/ldes/specification) - LDES protocol details
