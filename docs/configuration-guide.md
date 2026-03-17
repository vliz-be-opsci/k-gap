---
title: Configuration Guide
nav_order: 3
---

# K-GAP Configuration Guide

Complete reference for configuring all K-GAP components through environment variables and configuration files.

## Quick Navigation

- [Environment Variables Overview](#environment-variables-overview)
- [GraphDB Configuration](#graphdb-configuration)
- [Jupyter Configuration](#jupyter-configuration)
- [Sembench Configuration](#sembench-configuration)
- [LDES Consumer Configuration](#ldes-consumer-configuration)
- [Complete `.env` Example](#complete-env-example)

## Environment Variables Overview

K-GAP uses environment variables (stored in `.env` file) to configure all components. Copy the template and customize:

```bash
cp dotenv-example .env
```

### Variable Naming Convention

- **COMPOSE_**: Docker Compose settings
- **GDB_**: GraphDB settings
- **JUPYTER_**: Jupyter settings (optional)
- **SEMBENCH_**: Sembench settings
- **LDES_**: LDES Consumer settings
- **LOG_**: Logging settings

## GraphDB Configuration

### Core Variables

| Variable | Default | Purpose | Example |
|----------|---------|---------|---------|
| `GDB_REPO` | `kgap` | Repository identifier | `kgap`,`my-repo` |
| `REPOLABEL` | `label_repo_here` | Human-readable name | `My Knowledge Graph` |
| `GDB_HOME_FOLDER` | `/opt/graphdb/home` | Data directory | `/data/graphdb` |
| `GDB_MAX_HEADER` | `65536` | Max HTTP header size | `65536` (dev), `131072` (prod) |
| `GDB_JAVA_OPTS` | `-Xms8g -Xmx16g ...` | Java runtime options | See below |

### Memory Configuration

GraphDB Java options control memory allocation. Adjust `GDB_JAVA_OPTS` based on your system:

```bash
# Development (4GB)
GDB_JAVA_OPTS="-Xms2g -Xmx4g"

# Standard (16GB)
GDB_JAVA_OPTS="-Xms8g -Xmx16g -Dcom.ontotext.graphdb.monitoring.jmx=true"

# Large-scale (64GB with monitoring)
GDB_JAVA_OPTS="-Xms32g -Xmx64g -Dcom.ontotext.graphdb.monitoring.jmx=true -XX:+UseG1GC"

# Kubernetes/Container (automatic tuning)
GDB_JAVA_OPTS="-Xms4g -Xmx8g -XX:+PerfDisableSharedMem"
```

### Data Persistence

To persist GraphDB data across container restarts:

```bash
# 1. Create directory
mkdir -p ./data/graphdb

# 2. Add to .env
GDB_HOME_FOLDER=/data/graphdb

# 3. Verify docker-compose.yml has volume:
# volumes:
#   - ./data/graphdb:/opt/graphdb/home
```

## Jupyter Configuration

### Core Variables

| Variable | Default | Purpose | Example |
|----------|---------|---------|---------|
| `GDB_BASE` | `http://graphdb:7200/` | GraphDB service URL | See below |
| `GDB_REPO` | `kgap` | GraphDB repository name | Same as `GDB_REPO` above |
| `NOTEBOOK_ARGS` | `--NotebookApp.token=''` | Jupyter settings | Typically unchanged |
| `SRC_FOLDER` | `/kgap/notebooks` | Notebook location | Typically unchanged |

### Connecting to Remote GraphDB

For external GraphDB (not in Docker Compose):

```bash
# Within Docker Compose network
GDB_BASE=http://graphdb-server:7200/

# Remote server (DNS)
GDB_BASE=http://graphdb.example.org:7200/

# Remote server (IP)
GDB_BASE=http://192.168.1.100:7200/
```

### Adding Python Packages

Permanently add dependencies:

```bash
# 1. Edit requirements file
echo "rdflib==6.1" >> jupyter/kgap/requirements.txt
echo "networkx==3.0" >> jupyter/kgap/requirements.txt

# 2. Rebuild and restart
docker compose build jupyter
docker compose up -d jupyter
```

Alternatively, install in notebook:

```python
!pip install rdflib networkx
```

## Sembench Configuration

### Core Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEMBENCH_INPUT_PATH` | `/data` | Input data directory |
| `SEMBENCH_OUTPUT_PATH` | `/data` | Output data directory |
| `SEMBENCH_HOME_PATH` | `/data` | Runtime files directory |
| `SEMBENCH_CONFIG_PATH` | `/data/sembench.yaml` | Configuration file path |
| `SCHEDULER_INTERVAL_SECONDS` | `86400` | Task check interval (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Setting Execution Schedule

The `SCHEDULER_INTERVAL_SECONDS` controls how often Sembench checks for scheduled tasks:

```bash
# Check every hour (useful for hourly/daily tasks)
SCHEDULER_INTERVAL_SECONDS=3600

# Check every 10 minutes (for frequently scheduled tasks)
SCHEDULER_INTERVAL_SECONDS=600

# Check once per day at startup (set and forget)
SCHEDULER_INTERVAL_SECONDS=86400

# Check every 30 seconds (aggressive, for testing)
SCHEDULER_INTERVAL_SECONDS=30
```

### Minimal Configuration

If not using Sembench yet:

```bash
# Create empty config
echo "workflows: []" > ./data/sembench.yaml
```

## LDES Consumer Configuration

### Core Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LDES_CONFIG_FILE` | `/data/ldes-feeds.yaml` | Feed configuration path |
| `LDES2SPARQL_IMAGE` | `ghcr.io/maregraph-eu/ldes2sparql:latest` | Container image |
| `LDES_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_LEVEL` | `INFO` | General logging level |
| `COMPOSE_PROJECT_NAME` | `kgap` | Docker Compose project name |
| `DEFAULT_SPARQL_ENDPOINT` | `http://graphdb:7200/...` | Default ingest endpoint |
| `REMOVE_ORPHANS` | `false` | Remove unlisted feeds |

### Feed Configuration

Create `data/ldes-feeds.yaml` with feed definitions:

```yaml
feeds:
  feed-name-1:
    url: https://example.org/ldes/feed1
    environment:
      POLLING_FREQUENCY: 300000     # 5 minutes in milliseconds
      MATERIALIZE: "false"
      RESTART: "unless-stopped"
  
  feed-name-2:
    url: https://example.org/ldes/feed2
    sparql_endpoint: http://graphdb:7200/repositories/custom/statements
    environment:
      POLLING_FREQUENCY: 600000     # 10 minutes
      MATERIALIZE: "true"
```

### Polling Frequency Reference

Common polling frequencies (in milliseconds):

| Frequency | Milliseconds | Use Case |
|-----------|-----------|----------|
| Every 1 minute | `60000` | High-frequency data feeds |
| Every 5 minutes | `300000` | Active data feeds |
| Every 10 minutes | `600000` | Standard feeds (recommended) |
| Every 30 minutes | `1800000` | Lower priority feeds |
| Every hour | `3600000` | Bulk data feeds |
| Every 6 hours | `21600000` | Slow-changing data |
| Every 24 hours | `86400000` | Daily snapshot data |

### Restart Policies

Control feed container restart behavior:

```yaml
# Restart unless explicitly stopped (production default)
RESTART: "unless-stopped"

# Always restart on exit (high availability)
RESTART: "always"

# Restart only on non-zero exit (with backoff)
RESTART: "on-failure"

# Don't restart (experimental/testing)
RESTART: "no"
```

## Complete `.env` Example

```bash
# ============================================================================
# Docker Compose Configuration
# ============================================================================
COMPOSE_PROJECT_NAME=kgap
BUILD_TAG=latest
LOG_LEVEL=INFO

# ============================================================================
# GraphDB Configuration
# ============================================================================

# Repository identity
GDB_REPO=kgap
REPOLABEL=K-GAP Knowledge Graph Repository

# Storage (optional - comment out to keep data in container)
# GDB_HOME_FOLDER=/data/graphdb

# Performance tuning
GDB_MAX_HEADER=65536
GDB_JAVA_OPTS="-Xms8g -Xmx16g -Dcom.ontotext.graphdb.monitoring.jmx=true"

# ============================================================================
# Jupyter Configuration
# ============================================================================

# Connect to GraphDB
GDB_BASE=http://graphdb:7200/

# Notebook startup options (token authentication disabled)
NOTEBOOK_ARGS="--NotebookApp.token=''"
SRC_FOLDER=/kgap/notebooks

# ============================================================================
# Sembench Configuration
# ============================================================================

SEMBENCH_INPUT_PATH=/data
SEMBENCH_OUTPUT_PATH=/data
SEMBENCH_HOME_PATH=/data
SEMBENCH_CONFIG_PATH=/data/sembench.yaml

# How often to check for scheduled tasks (seconds)
# 86400 = once per day, 3600 = once per hour
SCHEDULER_INTERVAL_SECONDS=86400

# ============================================================================
# LDES Consumer Configuration
# ============================================================================

# Feed configuration file
LDES_CONFIG_FILE=/data/ldes-feeds.yaml

# (Optional) Custom ldes2sparql image
# LDES2SPARQL_IMAGE=ghcr.io/maregraph-eu/ldes2sparql:latest

# Logging for LDES containers
LDES_LOG_LEVEL=INFO

# Docker network (auto-detected, usually no change needed)
# DOCKER_NETWORK=kgap_default

# Whether to remove containers not in configuration
# REMOVE_ORPHANS=false
```

## Configuration by Deployment Profile

### Development Environment

Minimal resources, debug logging:

```bash
COMPOSE_PROJECT_NAME=kgap-dev
LOG_LEVEL=DEBUG
GDB_JAVA_OPTS="-Xms2g -Xmx4g"
LDES_LOG_LEVEL=DEBUG
SCHEDULER_INTERVAL_SECONDS=3600
```

### Testing Environment

Medium resources, INFO logging:

```bash
COMPOSE_PROJECT_NAME=kgap-test
LOG_LEVEL=INFO
GDB_JAVA_OPTS="-Xms4g -Xmx8g"
GDB_HOME_FOLDER=/data/graphdb
SCHEDULER_INTERVAL_SECONDS=1800  # Check every 30 min
```

### Production Environment

Full resources, WARNING logging, persistence:

```bash
COMPOSE_PROJECT_NAME=kgap-prod
LOG_LEVEL=WARNING
GDB_JAVA_OPTS="-Xms32g -Xmx64g -Dcom.ontotext.graphdb.monitoring.jmx=true -XX:+UseG1GC"
GDB_HOME_FOLDER=/data/graphdb
LDES_LOG_LEVEL=INFO
SCHEDULER_INTERVAL_SECONDS=86400
LDES_CLEAR_STATE=0
```

## Validation Checklist

After creating `.env`, verify configuration:

```bash
# 1. Check .env exists and is readable
test -f .env && echo "✓ .env exists"

# 2. Verify required variables
grep "GDB_REPO" .env && echo "✓ GDB_REPO set"
grep "LDES_CONFIG_FILE" .env && echo "✓ LDES_CONFIG_FILE set"

# 3. Check configuration files exist
test -f ./data/ldes-feeds.yaml && echo "✓ ldes-feeds.yaml exists"
test -f ./data/sembench.yaml && echo "✓ sembench.yaml exists"

# 4. Validate YAML syntax
python -m yaml ./data/ldes-feeds.yaml && echo "✓ ldes-feeds.yaml valid"
python -m yaml ./data/sembench.yaml && echo "✓ sembench.yaml valid"

# 5. Start services and check logs
docker compose up -d
sleep 5
docker compose logs --grep "ERROR" && echo "⚠ Check errors above"
```

## Changing Configuration

### Applying Changes

After modifying `.env`:

```bash
# Option 1: Restart affected service
docker compose restart graphdb
docker compose restart jupyter
docker compose restart sembench

# Option 2: Restart all services
docker compose down
docker compose up -d

# Option 3: Rebuild and restart (for image changes)
docker compose build
docker compose up -d
```

### Reverting to Defaults

```bash
# Restore original template
cp dotenv-example .env

# Or selectively
grep "^GDB_REPO" dotenv-example >> .env
```

## Troubleshooting Configuration

### Variables Not Taking Effect

```bash
# 1. Verify .env is being read
docker compose config | grep "GDB_REPO"

# 2. Check container environment
docker compose exec graphdb env | grep GDB

# 3. Restart service
docker compose down
docker compose up -d
```

### Invalid YAML in Configuration Files

```bash
# Check LDES configuration
python -c "import yaml; yaml.safe_load(open('./data/ldes-feeds.yaml'))"

# Check Sembench configuration
python -c "import yaml; yaml.safe_load(open('./data/sembench.yaml'))"
```

### Memory-Related Issues

```bash
# Check available system memory
free -h

# Review actual Java allocation
docker compose exec graphdb jps -e | grep graphdb

# Adjust GDB_JAVA_OPTS in .env and restart
```

## See Also

- [GraphDB Component](./components/graphdb.md)
- [Jupyter Component](./components/jupyter.md)
- [Sembench Component](./components/sembench.md)
- [LDES Consumer Component](./components/ldes-consumer.md)
- [Quick Reference](./quick-reference.md)
