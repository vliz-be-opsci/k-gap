# LDES Consumer Component

The LDES Consumer is a multi-feed harvesting service that wraps [ldes2sparql](https://github.com/maregraph-eu/ldes2sparql) to automatically ingest data from multiple Linked Data Event Streams (LDES) into GraphDB.

## Overview

The LDES Consumer service reads a YAML configuration file containing multiple LDES feeds and spawns a separate `ldes2sparql` Docker container for each feed. This allows K-GAP to harvest data from multiple heterogeneous sources simultaneously.

**Base Image**: `python:3.11-slim`  
**Container Name**: `test_kgap_ldes_consumer` (in test setup)  
**Requires**: Docker socket access (`/var/run/docker.sock`)

## Key Features

- **Multi-Feed Support**: Harvest from multiple LDES sources simultaneously
- **Container Spawning**: Dynamically creates ldes2sparql containers
- **Network Integration**: Spawned containers join the same Docker network as the K-GAP stack
- **Event-Based Monitoring**: Real-time monitoring via Docker event stream (efficient, zero-polling)
- **Configurable Polling**: Set different polling intervals per feed (passed to ldes2sparql)
- **Structured Logging**: Configurable log levels for debugging
- **Log Capture**: Automatically captures and archives container logs on shutdown
- **Orphan Cleanup**: Optional removal of containers not in current configuration
- **Docker Compose Integration**: Automatically detects and applies Compose project labels

## Architecture

```
┌────────────────────────────────────────────────────────┐
│           LDES Consumer Container                      │
├────────────────────────────────────────────────────────┤
│                                                         │
│  app.py                                                │
│       │                                                 │
│       ├─▶ Load ldes-feeds.yaml                        │
│       │   (from /data/)                               │
│       │                                                 │
│       ├─▶ Detect Docker Compose Project labels        │
│       │                                                 │
│       ├─▶ Detect Parent Container Network             │
│       │                                                 │
│       ├─▶ For each feed in config:                    │
│       │    ├─▶ Create state directory                 │
│       │    └─▶ docker run ldes2sparql                 │
│       │        (new container)                        │
│       │                                                 │
│       └─▶ Monitor containers                          │
│           ├─▶ Event Stream Listener                   │
│           │   (Docker events in real-time)            │
│           └─▶ Fallback Status Checker                 │
│               (every 10 seconds)                       │
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
        │      └─▶ Polls LDES URL     │
        │      └─▶ GraphDB            │
        │                             │
        │  ldes-consumer-feed2        │
        │    (ldes2sparql)            │
        │      └─▶ Polls LDES URL     │
        │      └─▶ GraphDB            │
        │                             │
        │  ldes-consumer-feed3        │
        │    (ldes2sparql)            │
        │      └─▶ Polls LDES URL     │
        │      └─▶ GraphDB            │
        │                             │
        └─────────────────────────────┘
```

## How It Works

1. **Startup**: The LDES Consumer container reads the configuration file and detects Docker Compose project labels and network
2. **Container Spawning**: For each feed in the configuration:
   - Creates a state directory at `/data/ldes-consumer/state/{feed-name}/`
   - Spawns a new Docker container running `ldes2sparql`
   - Configures the container with feed-specific parameters and environment variables
   - Mounts the state directory at `/state` in the container
   - Attaches the container to the detected Docker network
   - Applies Compose project labels if available
3. **Event-Based Monitoring**: Subscribes to Docker's event stream for real-time container status tracking
   - Listens for events: start, stop, die, health_status, destroy
   - Automatically captures logs when a container dies
   - Displays real-time status updates
   - Falls back to periodic status checks (every 10 seconds) if events fail
4. **Data Harvesting**: Each `ldes2sparql` container:
   - Polls its assigned LDES feed at the configured interval (via `POLLING_FREQUENCY` environment variable)
   - Ingests new data into the GraphDB SPARQL endpoint
   - Maintains state in `/state` to track harvested items and resumable position
5. **Graceful Shutdown**: When the service terminates:
   - Captures logs from all running containers
   - Stops all spawned containers (with 10-second timeout)
   - Removes containers if configured to do so

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LDES_CONFIG_PATH` | `/data/ldes-feeds.yaml` | Path to YAML configuration file |
| `LDES2SPARQL_IMAGE` | `ghcr.io/maregraph-eu/ldes2sparql:latest` | Docker image for ldes2sparql |
| `LOG_LEVEL` | `INFO` | Logging level for LDES Consumer (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `DOCKER_NETWORK` | Auto-detected | Docker network for spawned containers (auto-detected from parent) |
| `COMPOSE_PROJECT_NAME` | `kgap` | Docker Compose project name (used for labels) |
| `GRAPH_PREFIX` | `ldes` | Prefix for default target graph URIs |
| `GDB_REPO` | `kgap` | GraphDB repository name |
| `DEFAULT_SPARQL_ENDPOINT` | `http://graphdb:7200/repositories/{GDB_REPO}/statements` | Default SPARQL endpoint for ingestion |
| `REMOVE_ORPHANS` | `false` | Remove containers not in current configuration (true/false) |
| `LDES_LOG_LEVEL` | (inherits from LOG_LEVEL) | Log level passed to ldes2sparql containers |
| `RESTART` | `no` | Default restart policy for spawned containers |

#### Path Resolution

The LDES Consumer automatically resolves host paths for state directories using **container mount introspection**. It inspects the `/proc/self/cgroup` file and Docker container mounts to determine the host path backing the `/data` volume, eliminating the need for manual `HOST_PWD` configuration.

This approach works seamlessly with:
- **Bind mounts** (e.g., `./data:/data` in Docker Compose) → resolves to the host filesystem path
- **Named volumes** (e.g., Docker-managed volumes) → resolves to the Docker volume location
- **Any container orchestration** that exposes mount metadata via the Docker API

If mount introspection fails in unusual environments, you can set `HOST_PWD` as a fallback, but this is rarely needed.

### LDES Feeds Configuration File

Create a `data/ldes-feeds.yaml` file with the following structure:

```yaml
feeds:
  example-feed-1:
    url: http://example.com/ldes-feed-1
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:  # optional additional environment variables
      POLLING_FREQUENCY: 60000  # in milliseconds (optional, defaults to 60000)
      # Add any additional environment variables needed by ldes2sparql here
      # EXAMPLE_VAR: value

  example-feed-2:
    url: http://example.com/ldes-feed-2
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      POLLING_FREQUENCY: 120000  # 2 minutes
```

#### Required Fields

- **feed-key**: Unique identifier for the feed (used in container naming, `ldes-consumer-{feed-key}`)
- **url**: URL of the LDES feed
- **sparql_endpoint**: SPARQL endpoint where data should be ingested (or use `DEFAULT_SPARQL_ENDPOINT` env var)

#### Optional Fields

- **environment**: Dictionary of additional environment variables for the ldes2sparql container
  - **POLLING_FREQUENCY**: How often to poll the feed in **milliseconds** (default: 60000 = 60 seconds)
  - See [ldes2sparql documentation](https://github.com/maregraph-eu/ldes2sparql) for other available variables
  - **RESTART**: Docker restart policy for this specific feed (overrides default)
  - **REMOVE**: Remove container when it exits (default: false)
  - **TARGET_GRAPH**: Named graph for ingesting data (default: `urn:kgap:{GRAPH_PREFIX}:{feed-key}`)

### Example Configuration

```yaml
feeds:
  # Marine data from IOC
  marine-observations:
    url: https://marinedata.org/ldes/observations
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      POLLING_FREQUENCY: 300000  # Poll every 5 minutes
      RESTART: "always"
  
  # Biodiversity data
  biodiversity-specimens:
    url: https://biodiversity.org/ldes/specimens
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      POLLING_FREQUENCY: 600000  # Poll every 10 minutes
  
  # Research publications
  research-publications:
    url: https://research.org/ldes/publications
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      POLLING_FREQUENCY: 3600000  # Poll every hour
```

## File Structure

```
ldes-consumer/
├── Dockerfile                    # Image definition
├── README.md                     # Component-specific README
├── requirements.txt              # Python dependencies (PyYAML, docker)
└── app.py                        # Main application (loads config, spawns containers, monitors)
```

### app.py

The main application that:
- Loads the YAML configuration from `/data/ldes-feeds.yaml`
- Detects Docker Compose project labels and parent network
- Spawns Docker containers for each feed in the configuration
- Monitors container health via Docker event stream (real-time) with fallback status checks
- Handles graceful shutdown and log capture
- Manages orphaned containers (optional)

Key functions:
- **load_ldes_feeds()**: Parse YAML configuration
- **process_feeds()**: Create and start a container for each feed
- **monitor_containers_with_events()**: Listen to Docker events for real-time status (runs in background thread)
- **capture_container_logs()**: Save container logs to file on exit
- **cleanup_containers()**: Gracefully stop and remove spawned containers
- **main()**: Orchestrate the loading, spawning, and monitoring loop

## Usage

### Initial Setup

1. **Create configuration file** in `data/ldes-feeds.yaml`:
   ```bash
   mkdir -p data
   ```
   Create `data/ldes-feeds.yaml` with your LDES feeds (see [Configuration](#ldes-feeds-configuration-file) section for structure)

2. **Verify ldes2sparql image is available**:
   ```bash
   docker pull ghcr.io/maregraph-eu/ldes2sparql:latest
   ```

3. **Verify Docker socket mount** in docker-compose.yml:
   ```yaml
   ldes-consumer:
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock  # Required!
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
1. Edit `data/ldes-feeds.yaml` and add a new feed entry (add a new key to the `feeds` dictionary)
2. Restart the LDES consumer:
   ```bash
   docker compose restart ldes-consumer
   ```
   The new feed's container will be spawned automatically

**Remove a feed**:

*Option 1: Manual cleanup*
1. Stop and remove the specific container:
   ```bash
   docker stop ldes-consumer-{feed-key}
   docker rm ldes-consumer-{feed-key}
   ```
2. Remove the feed from `data/ldes-feeds.yaml`
3. Restart the LDES consumer

*Option 2: Automatic cleanup (recommended)*
1. Remove the feed from `data/ldes-feeds.yaml`
2. Enable `REMOVE_ORPHANS=true` and restart:
   ```bash
   docker compose restart -e REMOVE_ORPHANS=true ldes-consumer
   ```
   Orphaned containers will be automatically removed

**Modify feed configuration**:
1. Update the feed entry in `data/ldes-feeds.yaml`
2. Restart the LDES consumer:
   ```bash
   docker compose restart ldes-consumer
   ```
   The old container will be stopped and a new one spawned with the updated configuration

### Container Naming Convention

Spawned containers follow the naming convention:
```
ldes-consumer-{feed-key}
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

Each LDES feed container maintains its own state directory for tracking progress:

```
data/
├── ldes-feeds.yaml                 # Configuration file
└── ldes-consumer/
    ├── state/                      # State directories for each feed
    │   ├── marine-observations/    # State files for marine-observations feed
    │   ├── biodiversity-specimens/ # State files for biodiversity-specimens feed
    │   └── research-publications/  # State files for research-publications feed
    └── logs/                       # Archived container logs (on shutdown)
        ├── marine-observations_20260315-120000.log
        └── biodiversity-specimens_20260315-120000.log
```

**State Persist & Recovery**:
- Each feed maintains its own state directory at `/data/ldes-consumer/state/{feed-key}/`
- This is mounted as `/state` inside each ldes2sparql container
- State includes last processed item, harvesting metadata, and continuation tokens
- State persists across container restarts, ensuring:
  - No duplicate data ingestion
  - Efficient incremental updates
  - Recovery from failures

**Log Archive**:
- When containers are stopped or die, their logs are captured and saved to `/data/ldes-consumer/logs/`
- Log files are named as `{feed-key}_{timestamp}.log`
- This provides visibility into container lifecycle and troubleshooting

## Monitoring & Logging

### Event-Based Container Monitoring

The LDES Consumer uses **real-time Docker event streaming** for efficient container monitoring:

**Real-Time Events Tracked**:
- `CREATE` - Container created
- `START ✓` - Container started (transition to running)
- `STOP ⊘` - Container stopped gracefully
- `DIE ✗` - Container exited unexpectedly (includes exit code)
- `HEALTH` - Container health check status changed
- `DESTROY ←` - Container was removed

**Event Listener Features**:
- Listens to Docker event stream in background thread
- Zero polling overhead—responds instantly to changes
- Automatically captures logs when a container dies (for diagnostics)
- Displays running container count: `[Status] X/Y containers running`

**Fallback Monitoring**:
- If Docker events are not being received, fallback mechanism activates
- Periodic status checks run every 10 seconds
- Displays status changes: `[Fallback] Status change: container-name - running → exited`
- Ensures visibility even if event stream has issues

### Log Views

**Service Logs**:
```bash
# View LDES Consumer service logs (spawner, orchestrator)
docker compose logs -f ldes-consumer
```

**Individual Feed Container Logs**:
```bash
# View logs from a specific feed container (real-time)
docker logs -f ldes-consumer-{feed-key}

# Example:
docker logs -f ldes-consumer-marine-observations
```

**Archived Logs**:
```bash
# View logs captured on container exit
ls -la data/ldes-consumer/logs/
cat data/ldes-consumer/logs/marine-observations_20260315-120000.log
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# In .env file:
LOG_LEVEL=DEBUG

# Restart service:
docker compose restart ldes-consumer
```

This shows:
- Docker container creation details
- Feed configuration details
- Event listener diagnostics
- Network and Compose project detection

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

Balance between data freshness and load. Set `POLLING_FREQUENCY` in **milliseconds** per feed:

```yaml
feeds:
  # High-frequency updates (every minute = 60,000 ms)
  fast-feed:
    url: https://example.com/ldes/fast
    environment:
      POLLING_FREQUENCY: 60000

  # Moderate updates (every 5 minutes = 300,000 ms)
  moderate-feed:
    url: https://example.com/ldes/moderate
    environment:
      POLLING_FREQUENCY: 300000

  # Low-frequency updates (every hour = 3,600,000 ms)
  slow-feed:
    url: https://example.com/ldes/slow
    environment:
      POLLING_FREQUENCY: 3600000
```

**Note**: `POLLING_FREQUENCY` is in **milliseconds**, not seconds. Default is 60000 (60 seconds).

### Resource Allocation

For many feeds or high-volume feeds, increase resources in `docker-compose.yml`:

```yaml
ldes-consumer:
  # ... other config ...
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '2'
```

### Concurrent Harvesting

The service spawns one container per feed, enabling parallel harvesting. Each container:
- Operates independently
- Maintains its own state
- Polls its LDES source at configured intervals
- Ingests into GraphDB simultaneously with other feeds

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

Pass additional configuration to individual feeds. All [ldes2sparql environment variables](https://github.com/maregraph-eu/ldes2sparql) are supported:

```yaml
feeds:
  authenticated-feed:
    url: https://secure.example.com/ldes
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    environment:
      POLLING_FREQUENCY: 120000
      RESTART: "always"         # Docker restart policy
      FOLLOW: "true"            # Keep following updates
      MEMBER_BATCH_SIZE: "1000" # Batch size for member processing
      MATERIALIZE: "true"       # Materialize results
      FAILURE_IS_FATAL: "false" # Don't exit on failures
      TARGET_GRAPH: "urn:custom:graph"  # Override default target graph

  complex-feed:
    url: https://example.com/ldes
    environment:
      POLLING_FREQUENCY: 300000
      SHAPE: "https://example.com/shapes"  # Validation shape
      LOG_LEVEL: "DEBUG"        # Feed-specific log level
```

### Orphan Container Cleanup

Automatically remove containers from previous configurations that are no longer in the current `ldes-feeds.yaml`:

```bash
# In .env file or docker-compose.yml environment:
REMOVE_ORPHANS=true

# Or pass when running:
docker compose up -d -e REMOVE_ORPHANS=true ldes-consumer
```

When enabled:
- Scans for any `ldes-consumer-*` containers not listed in current configuration
- Captures their logs before removal
- Removes them to clean up stale containers

### Custom Feed Container Restart Policy

Set Docker restart policy per feed or globally:

```yaml
feeds:
  important-feed:
    url: https://example.com/ldes
    environment:
      RESTART: "always"    # Always restart on failure
  
  optional-feed:
    url: https://example.com/ldes2
    environment:
      RESTART: "no"        # Don't restart
```

Valid values: `no`, `always`, `unless-stopped`, `on-failure`

## Related Documentation

- [Main Documentation](../index.md)
- [LDES Consumer README](../../ldes-consumer/README.md) - Detailed component documentation
- [GraphDB Component](./graphdb.md) - Target data store
- [ldes2sparql](https://github.com/maregraph-eu/ldes2sparql) - Underlying harvesting tool
- [LDES Specification](https://w3id.org/ldes/specification) - LDES protocol details
