# LDES Consumer Service

This service is a wrapper around the [ldes2sparql](https://github.com/maregraph-eu/ldes2sparql) tool that enables harvesting multiple LDES (Linked Data Event Streams) feeds.

## Overview

The LDES consumer service reads a YAML configuration file containing a list of LDES feeds and spawns a separate `ldes2sparql` Docker container instance for each feed. All spawned containers are attached to the same Docker Compose network.

## Configuration

### Environment Variables

The following environment variables can be configured in your `.env` file:

- `LDES_CONFIG_FILE`: Path to the YAML configuration file (default: `/data/ldes-feeds.yaml`)
- `LDES2SPARQL_IMAGE`: Docker image to use for ldes2sparql (default: `ghcr.io/maregraph-eu/ldes2sparql:latest`)
- `LOG_LEVEL`: Logging level for the LDES consumer service (default: `INFO`). Available levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### LDES Feeds Configuration File

Create a YAML file (e.g., `data/ldes-feeds.yaml`) with the following structure:

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

#### Required fields:
- `name`: Unique identifier for the feed (used in container naming)
- `url`: URL of the LDES feed
- `sparql_endpoint`: SPARQL endpoint where the data should be ingested

#### Optional fields:
- `polling_interval`: How often to poll the feed in seconds (default: 60). Note: This is converted to milliseconds and passed as `POLLING_FREQUENCY` to the ldes2sparql container.
- `environment`: Additional environment variables to pass to the ldes2sparql container

## Usage

1. Ensure the ldes2sparql Docker image is available:
   ```bash
   docker pull ghcr.io/maregraph-eu/ldes2sparql:latest
   ```
   Or build it locally if needed.

2. Copy the example configuration file:
   ```bash
   cp ldes-consumer/ldes-feeds.yaml.example data/ldes-feeds.yaml
   ```

3. Edit `data/ldes-feeds.yaml` with your LDES feeds

4. Start the service using Docker Compose:
   ```bash
   docker compose up ldes-consumer
   ```

## How it Works

1. The service reads the YAML configuration file on startup
2. For each feed in the configuration, it spawns a new Docker container running `ldes2sparql`
3. Each container is named `ldes-consumer-{feed-name}` and attached to the Docker Compose network
4. Containers are labeled with the Docker Compose project name for integration with the stack
5. The service monitors the spawned containers and automatically restarts them if they fail
6. **NEW:** The service watches the configuration file for changes and dynamically:
   - Spawns new containers when feeds are added
   - Stops and removes containers when feeds are removed
   - Restarts containers when feed configurations are modified
7. All containers are gracefully stopped when the service is terminated

## Dynamic Feed Management

The LDES consumer service now supports **dynamic addition, removal, and modification of feeds at runtime** without requiring a container restart.

### How Dynamic Feed Management Works

The service uses the Python `watchdog` library to monitor the configuration file (`/data/ldes-feeds.yaml`) for changes. When a modification is detected:

1. The file content hash is checked to avoid false positives (e.g., from file system events that don't change content)
2. The new configuration is loaded and validated
3. The service compares the new feed list with currently running feeds
4. Appropriate actions are taken:
   - **Added feeds**: New containers are spawned automatically
   - **Removed feeds**: Existing containers are gracefully stopped and removed
   - **Modified feeds**: Containers are restarted with the new configuration

### Dynamic Usage Example

To add a new feed at runtime:

1. Edit the configuration file while the service is running:
   ```bash
   # Edit data/ldes-feeds.yaml and add a new feed
   vim data/ldes-feeds.yaml
   ```

2. Save the file - the new feed container will be spawned automatically within a few seconds

3. Check the logs to see the feed being added:
   ```bash
   docker compose logs -f ldes-consumer
   ```

You should see log messages like:
```
ldes-consumer - INFO - Config file modification detected: /data/ldes-feeds.yaml
ldes-consumer - INFO - Synchronizing feeds with configuration file...
ldes-consumer - INFO - New feed 'my-new-feed' detected, spawning container...
ldes-consumer - INFO - Starting LDES consumer for feed: my-new-feed
```

### Use Cases for Dynamic Feed Management

This feature is particularly useful for:

- **On-demand harvesting**: A backend service or manager can add new LDES feeds to the YAML file programmatically, triggering automatic harvesting
- **Configuration updates**: Modify feed parameters (polling interval, target graph, etc.) without downtime
- **Feed lifecycle management**: Temporarily disable feeds by removing them, then re-enable later
- **Integration with self-hosted platforms**: Perfect for platforms like [mtt-self-host-platform](https://github.com/marine-term-translations/mtt-self-host-platform) where users can request new data streams

### Technical Details

- File changes are debounced (2-second delay) to handle rapid successive modifications
- Invalid YAML or configuration errors preserve the current running state
- The configuration file is the single source of truth - no state is persisted elsewhere
- Minimal overhead - watchdog is a lightweight library with no additional dependencies

## Container Naming

Spawned containers follow the naming convention: `ldes-consumer-{feed-name}`

For example, a feed named `marine-observations` will create a container named `ldes-consumer-marine-observations`.

## Network Integration

All spawned ldes2sparql containers are attached to the same Docker network as the main stack (typically `kgap_default`), allowing them to communicate with other services like GraphDB.

## Logging

The LDES consumer service uses structured logging with configurable log levels. 

### Log Levels

Set the `LOG_LEVEL` environment variable to control the verbosity of logs:
- `DEBUG`: Detailed information for debugging (includes Docker commands)
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that prevent operation

### Viewing Logs

Logs from the spawner service can be viewed using:
```bash
docker compose logs ldes-consumer
```

Logs from individual ldes2sparql containers can be viewed using:
```bash
docker logs ldes-consumer-{feed-name}
```

### Log Format

Logs are formatted with timestamp, logger name, level, and message:
```
2025-10-28 14:20:00 - ldes-consumer - INFO - Starting LDES consumer for feed: example-feed-1
```
