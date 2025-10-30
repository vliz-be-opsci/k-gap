# LDES Consumer Service

This service is a wrapper around the [ldes2sparql](https://github.com/rdf-connect/ldes2sparql) tool that enables harvesting LDES (Linked Data Event Streams) feeds. It supports three operation modes for maximum flexibility.

## Overview

The LDES consumer service can operate in three modes:

1. **Folder Mode** (Recommended): Watches a directory for YAML configuration files and dynamically spawns/stops containers
2. **Legacy Single File Mode**: Reads a single YAML file with multiple feed configurations
3. **Direct Mode**: Runs as a direct ldes2sparql container using environment variables

## Operation Modes

### Mode 1: Folder Mode (Recommended)

In folder mode, the service monitors a directory for YAML files. Each YAML file represents a single LDES feed configuration. When a YAML file is added, modified, or removed, the service automatically spawns, updates, or stops the corresponding container.

**Benefits:**
- Dynamic configuration: Add/remove feeds without restarting the service
- Easy management: Each feed has its own configuration file
- Automatic recovery: Containers are automatically restarted if they fail

**Configuration:**
- Set `LDES_CONFIG_PATH` to a directory path (e.g., `/data/ldes-feeds`)
- Place individual YAML configuration files in this directory
- Each YAML file will spawn a separate ldes2sparql container

**Example directory structure:**
```
/data/ldes-feeds/
  ├── marine-observations.yaml
  ├── weather-data.yaml
  └── sensor-readings.yaml
```

### Mode 2: Legacy Single File Mode

In legacy mode, the service reads a single YAML file containing multiple feed configurations and spawns a container for each feed defined in the file.

**Configuration:**
- Set `LDES_CONFIG_PATH` to a file path (e.g., `/data/ldes-feeds.yaml`)
- The YAML file should contain a `feeds` list with multiple feed configurations

**Example YAML structure:**
```yaml
feeds:
  - name: feed1
    url: http://example.com/ldes-feed-1
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
  - name: feed2
    url: http://example.com/ldes-feed-2
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
```

### Mode 3: Direct Mode

In direct mode, the service runs as a direct ldes2sparql container without spawning subcontainers. Configuration is provided entirely through environment variables.

**Configuration:**
- Do not set `LDES_CONFIG_PATH` (or leave it empty)
- Set required environment variables: `LDES`, `SPARQL_ENDPOINT`
- Optionally set additional environment variables for fine-tuning

**Use case:** Simple single-feed deployments where dynamic configuration is not needed

## Configuration

### Environment Variables (Docker Compose)

The following environment variables can be configured in your `.env` file or docker-compose.yml:

#### General Configuration

- `LDES_CONFIG_PATH`: Path to configuration file or directory
  - If **directory**: Folder mode (watches for YAML files)
  - If **file**: Legacy single file mode
  - If **empty/unset**: Direct mode (uses env vars directly)
  - Default: Not set

- `LDES2SPARQL_IMAGE`: Docker image to use for ldes2sparql containers (folder/legacy modes only)
  - Default: `ghcr.io/rdf-connect/ldes2sparql:latest`

- `LOG_LEVEL`: Logging level for the LDES consumer service
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Default: `INFO`

- `DOCKER_NETWORK`: Docker network name for spawned containers (folder/legacy modes only)
  - Default: `kgap_default`

#### Direct Mode Environment Variables

These variables are only used when `LDES_CONFIG_PATH` is not set (direct mode):

**Required:**
- `LDES`: URL of the LDES feed
- `SPARQL_ENDPOINT`: SPARQL endpoint URL where data should be ingested

**Optional:**
- `SHAPE`: Path to SHACL shape file for validation (default: empty)
- `TARGET_GRAPH`: Target named graph in the SPARQL endpoint (default: empty, uses default graph)
- `FOLLOW`: Follow the LDES stream continuously (default: `true`)
- `MATERIALIZE`: Materialize LDES members (default: `false`)
- `ORDER`: Ordering mode - `none`, `asc`, or `desc` (default: `none`)
- `POLLING_FREQUENCY`: Polling interval in milliseconds (default: `5000`)
- `FAILURE_IS_FATAL`: Stop container on failure (default: `false`)
- `CONCURRENT_FETCHES`: Number of concurrent HTTP fetches (default: `10`)
- `FOR_VIRTUOSO`: Use Virtuoso-specific optimizations (default: `false`)
- `QUERY_TIMEOUT`: SPARQL query timeout in seconds (default: `1800`)
- `LAST_VERSION_ONLY`: Only keep the last version of each member (default: `false`)
- `BEFORE`: Filter members before this timestamp (ISO 8601 format)
- `AFTER`: Filter members after this timestamp (ISO 8601 format)
- `ACCESS_TOKEN`: Access token for endpoints requiring authentication (e.g., Qlever)
- `PERF_NAME`: Name for performance monitoring metrics

### Individual Feed Configuration Files (Folder Mode)

When using folder mode, each YAML file should contain configuration for a single LDES feed.

**Example:** `marine-observations.yaml`

```yaml
# Required fields
url: http://example.com/marine-ldes
sparql_endpoint: http://graphdb:7200/repositories/kgap/statements

# Optional fields
polling_interval: 60          # Seconds (converted to POLLING_FREQUENCY in milliseconds)
shape: ""                     # SHACL shape file path
target_graph: ""              # Named graph (empty = default graph)
follow: true                  # Follow the stream continuously
materialize: false            # Materialize members
order: none                   # Ordering: none, asc, desc
last_version_only: false      # Only keep latest version
failure_is_fatal: false       # Stop on failure
concurrent_fetches: 10        # Concurrent HTTP requests
for_virtuoso: false          # Virtuoso optimizations
query_timeout: 1800          # Timeout in seconds

# Optional: Timestamp filters (ISO 8601 format)
# before: "2025-12-31T23:59:59.000Z"
# after: "2024-01-01T00:00:00.000Z"

# Optional: Authentication
# access_token: "your-token-here"

# Optional: Performance monitoring
# perf_name: "marine-observations"

# Optional: Additional custom environment variables
environment:
  # CUSTOM_VAR: "value"
```

**Field Reference:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | URL of the LDES feed |
| `sparql_endpoint` | string | Yes | - | SPARQL endpoint URL for data ingestion |
| `polling_interval` | integer | No | 5 | Polling interval in seconds |
| `shape` | string | No | "" | Path to SHACL shape file for validation |
| `target_graph` | string | No | "" | Target named graph (empty for default) |
| `follow` | boolean | No | true | Continuously follow the LDES stream |
| `materialize` | boolean | No | false | Materialize LDES members |
| `order` | string | No | none | Ordering mode: `none`, `asc`, `desc` |
| `last_version_only` | boolean | No | false | Only process last version of members |
| `failure_is_fatal` | boolean | No | false | Stop container on processing failure |
| `concurrent_fetches` | integer | No | 10 | Number of concurrent HTTP requests |
| `for_virtuoso` | boolean | No | false | Enable Virtuoso-specific optimizations |
| `query_timeout` | integer | No | 1800 | SPARQL query timeout in seconds |
| `before` | string | No | - | Process members before this timestamp (ISO 8601) |
| `after` | string | No | - | Process members after this timestamp (ISO 8601) |
| `access_token` | string | No | - | Authentication token for secured endpoints |
| `perf_name` | string | No | - | Name for performance metrics |
| `environment` | object | No | {} | Additional custom environment variables |

### Legacy Single File Configuration

**Example:** `ldes-feeds.yaml`

```yaml
feeds:
  - name: example-feed-1
    url: http://example.com/ldes-feed-1
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 60
    environment:
      CUSTOM_VAR: value

  - name: example-feed-2
    url: http://example.com/ldes-feed-2
    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
    polling_interval: 120
```

## Usage

### Using Folder Mode (Recommended)

1. Create a directory for your feed configurations:
   ```bash
   mkdir -p ./data/ldes-feeds
   ```

2. Create individual YAML files for each feed:
   ```bash
   cp ldes-consumer/feed-config.yaml.example ./data/ldes-feeds/my-feed.yaml
   nano ./data/ldes-feeds/my-feed.yaml  # Edit with your configuration
   ```

3. Configure the `.env` file:
   ```bash
   LDES_CONFIG_PATH=/data/ldes-feeds
   ```

4. Start the service:
   ```bash
   docker compose up ldes-consumer
   ```

5. Add/remove/modify feeds dynamically:
   - **Add feed**: Copy a new YAML file to the directory
   - **Remove feed**: Delete the YAML file
   - **Update feed**: Modify the YAML file (container will restart automatically)

### Using Legacy Single File Mode

1. Create a configuration file:
   ```bash
   cp ldes-consumer/ldes-feeds.yaml.example data/ldes-feeds.yaml
   nano data/ldes-feeds.yaml  # Edit with your feeds
   ```

2. Configure the `.env` file:
   ```bash
   LDES_CONFIG_PATH=/data/ldes-feeds.yaml
   ```

3. Start the service:
   ```bash
   docker compose up ldes-consumer
   ```

### Using Direct Mode

1. Configure the `.env` file with direct environment variables:
   ```bash
   # Leave LDES_CONFIG_PATH empty or unset
   LDES_CONFIG_PATH=
   
   # Set required variables
   LDES=http://example.com/ldes-feed
   SPARQL_ENDPOINT=http://graphdb:7200/repositories/kgap/statements
   
   # Optional variables
   FOLLOW=true
   POLLING_FREQUENCY=5000
   ```

2. Or set in docker-compose.yml:
   ```yaml
   ldes-consumer:
     environment:
       - LDES=http://example.com/ldes-feed
       - SPARQL_ENDPOINT=http://graphdb:7200/repositories/kgap/statements
       # Do not set LDES_CONFIG_PATH
   ```

3. Start the service:
   ```bash
   docker compose up ldes-consumer
   ```

## How It Works

### Folder Mode
1. Service monitors the configured directory for YAML files
2. When a YAML file is detected, a new ldes2sparql container is spawned
3. Container is named `ldes-consumer-{filename}` (without extension)
4. If a file is modified, the container is stopped and recreated
5. If a file is deleted, the corresponding container is stopped and removed
6. Health checks ensure containers are restarted if they fail

### Legacy Mode
1. Service reads the YAML configuration file on startup
2. For each feed in the configuration, spawns a new ldes2sparql container
3. Containers are named `ldes-consumer-{feed-name}`
4. Containers run until the service is stopped

### Direct Mode
1. Service installs Node.js and ldes2sparql dependencies
2. Runs the ldes2sparql pipeline directly using environment variables
3. No container spawning - runs as a single process

## Container Naming

- **Folder mode**: `ldes-consumer-{filename-without-extension}`
  - Example: `marine-observations.yaml` → `ldes-consumer-marine-observations`
  
- **Legacy mode**: `ldes-consumer-{feed-name}`
  - Example: Feed with `name: my-feed` → `ldes-consumer-my-feed`

## Network Integration

All spawned ldes2sparql containers (folder and legacy modes) are attached to the same Docker network as the main stack (typically `kgap_default`), allowing them to communicate with other services like GraphDB.

## Logging

The LDES consumer service uses structured logging with configurable log levels.

### Log Levels

Set the `LOG_LEVEL` environment variable:
- `DEBUG`: Detailed information for debugging (includes Docker commands)
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that prevent operation

### Viewing Logs

**Main service logs:**
```bash
docker compose logs ldes-consumer
```

**Individual container logs (folder/legacy modes):**
```bash
docker logs ldes-consumer-{name}
```

**Follow logs in real-time:**
```bash
docker compose logs -f ldes-consumer
```

### Log Format

```
2025-10-29 10:30:00 - ldes-consumer - INFO - Starting LDES consumer for feed: marine-observations
```

## Troubleshooting

### Container fails to start

Check the logs:
```bash
docker compose logs ldes-consumer
docker logs ldes-consumer-{name}
```

Common issues:
- SPARQL endpoint not reachable
- Invalid YAML configuration
- Network configuration issues

### Feed not updating

- Verify the LDES URL is accessible
- Check `polling_interval` / `POLLING_FREQUENCY` setting
- Ensure `follow: true` for continuous streaming
- Check SPARQL endpoint is accepting updates

### High memory usage

- Reduce `concurrent_fetches`
- Enable `last_version_only: true` if you only need latest data
- Adjust `query_timeout` if queries are timing out

## Environment Variable Reference

For complete details on all environment variables supported by ldes2sparql, see:
https://github.com/rdf-connect/ldes2sparql

### Summary of Key Variables

| Variable | Direct Mode | YAML Config | Description |
|----------|-------------|-------------|-------------|
| LDES | ✓ | url | LDES feed URL |
| SPARQL_ENDPOINT | ✓ | sparql_endpoint | SPARQL endpoint URL |
| SHAPE | ✓ | shape | SHACL shape file |
| TARGET_GRAPH | ✓ | target_graph | Named graph |
| FOLLOW | ✓ | follow | Follow stream |
| MATERIALIZE | ✓ | materialize | Materialize members |
| ORDER | ✓ | order | Ordering mode |
| POLLING_FREQUENCY | ✓ | polling_interval* | Polling interval (ms / sec*) |
| FAILURE_IS_FATAL | ✓ | failure_is_fatal | Fatal on error |
| CONCURRENT_FETCHES | ✓ | concurrent_fetches | Concurrent requests |
| FOR_VIRTUOSO | ✓ | for_virtuoso | Virtuoso optimizations |
| QUERY_TIMEOUT | ✓ | query_timeout | Query timeout (seconds) |
| LAST_VERSION_ONLY | ✓ | last_version_only | Latest version only |
| BEFORE | ✓ | before | Before timestamp |
| AFTER | ✓ | after | After timestamp |
| ACCESS_TOKEN | ✓ | access_token | Auth token |

*Note: In YAML config files, use `polling_interval` in seconds. It's automatically converted to `POLLING_FREQUENCY` in milliseconds for ldes2sparql.

## Examples

### Example 1: Multiple Marine Data Feeds (Folder Mode)

```bash
# Create directory
mkdir -p ./data/ldes-feeds

# Create feed 1: Marine observations
cat > ./data/ldes-feeds/marine-obs.yaml << EOF
url: http://marine-data.org/ldes/observations
sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
polling_interval: 300
target_graph: http://example.org/marine-observations
EOF

# Create feed 2: Oceanographic data
cat > ./data/ldes-feeds/oceanographic.yaml << EOF
url: http://ocean-data.org/ldes/measurements
sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
polling_interval: 600
target_graph: http://example.org/oceanographic
EOF

# Start service
docker compose up ldes-consumer
```

### Example 2: Single Feed Direct Mode

```bash
# Configure in .env
cat > .env << EOF
LDES=http://example.com/ldes-feed
SPARQL_ENDPOINT=http://graphdb:7200/repositories/kgap/statements
FOLLOW=true
POLLING_FREQUENCY=10000
TARGET_GRAPH=http://example.org/data
EOF

# Start service
docker compose up ldes-consumer
```

### Example 3: Filtering by Timestamp

```yaml
# Historical data import - only process data from 2024
url: http://example.com/ldes-historical
sparql_endpoint: http://graphdb:7200/repositories/kgap/statements
after: "2024-01-01T00:00:00.000Z"
before: "2024-12-31T23:59:59.999Z"
follow: false  # Don't follow, just process historical data
```
