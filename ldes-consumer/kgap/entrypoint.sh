#!/bin/bash
set -e

# Environment variables
LDES_CONFIG_PATH="${LDES_CONFIG_PATH:-}"
LDES2SPARQL_IMAGE="${LDES2SPARQL_IMAGE:-ghcr.io/rdf-connect/ldes2sparql:latest}"
DOCKER_NETWORK="${DOCKER_NETWORK:-kgap_default}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kgap}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Array to track spawned containers
declare -A ACTIVE_CONTAINERS

# Logging functions
log_info() {
    if [[ "$LOG_LEVEL" =~ ^(DEBUG|INFO)$ ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ldes-consumer - INFO - $*"
    fi
}

log_debug() {
    if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ldes-consumer - DEBUG - $*"
    fi
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ldes-consumer - ERROR - $*" >&2
}

log_warning() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ldes-consumer - WARNING - $*"
}

# Function to parse YAML files using grep/sed (simple key-value extraction)
parse_yaml_value() {
    local yaml_file="$1"
    local key="$2"
    local default="$3"
    
    # Try to extract value from YAML file
    local value=$(grep "^${key}:" "$yaml_file" 2>/dev/null | sed "s/^${key}:[[:space:]]*//" | sed 's/^["'\'']//' | sed 's/["'\'']$//' | head -n 1)
    
    if [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# Function to validate YAML config
validate_yaml_config() {
    local yaml_file="$1"
    
    if [ ! -f "$yaml_file" ]; then
        log_error "YAML file not found: $yaml_file"
        return 1
    fi
    
    local url=$(parse_yaml_value "$yaml_file" "url" "")
    local sparql_endpoint=$(parse_yaml_value "$yaml_file" "sparql_endpoint" "")
    
    if [ -z "$url" ] || [ -z "$sparql_endpoint" ]; then
        log_error "YAML file $yaml_file missing required fields 'url' or 'sparql_endpoint'"
        return 1
    fi
    
    return 0
}

# Function to generate container name from filename
get_container_name() {
    local filename="$1"
    # Remove .yaml or .yml extension
    local name="${filename%.yaml}"
    name="${name%.yml}"
    # Sanitize name for docker
    name=$(echo "$name" | tr '_ ' '--' | tr '[:upper:]' '[:lower:]')
    echo "ldes-consumer-${name}"
}

# Function to spawn a container from YAML config
spawn_container() {
    local yaml_file="$1"
    local filename=$(basename "$yaml_file")
    
    # Validate config
    if ! validate_yaml_config "$yaml_file"; then
        return 1
    fi
    
    local container_name=$(get_container_name "$filename")
    
    # Check if container already exists
    if [ -n "${ACTIVE_CONTAINERS[$filename]:-}" ]; then
        log_warning "Container already exists for $filename"
        return 1
    fi
    
    # Parse configuration
    local url=$(parse_yaml_value "$yaml_file" "url" "")
    local sparql_endpoint=$(parse_yaml_value "$yaml_file" "sparql_endpoint" "")
    local shape=$(parse_yaml_value "$yaml_file" "shape" "")
    local target_graph=$(parse_yaml_value "$yaml_file" "target_graph" "")
    local follow=$(parse_yaml_value "$yaml_file" "follow" "true")
    local materialize=$(parse_yaml_value "$yaml_file" "materialize" "false")
    local order=$(parse_yaml_value "$yaml_file" "order" "none")
    local last_version_only=$(parse_yaml_value "$yaml_file" "last_version_only" "false")
    local failure_is_fatal=$(parse_yaml_value "$yaml_file" "failure_is_fatal" "false")
    local concurrent_fetches=$(parse_yaml_value "$yaml_file" "concurrent_fetches" "10")
    local for_virtuoso=$(parse_yaml_value "$yaml_file" "for_virtuoso" "false")
    local query_timeout=$(parse_yaml_value "$yaml_file" "query_timeout" "1800")
    local polling_interval=$(parse_yaml_value "$yaml_file" "polling_interval" "5")
    local before=$(parse_yaml_value "$yaml_file" "before" "")
    local after=$(parse_yaml_value "$yaml_file" "after" "")
    local access_token=$(parse_yaml_value "$yaml_file" "access_token" "")
    local perf_name=$(parse_yaml_value "$yaml_file" "perf_name" "")
    
    # Convert polling_interval (seconds) to POLLING_FREQUENCY (milliseconds)
    local polling_frequency=$((polling_interval * 1000))
    
    log_info "Starting LDES consumer from config file: $filename"
    log_info "  Container name: $container_name"
    log_info "  URL: $url"
    log_info "  SPARQL Endpoint: $sparql_endpoint"
    
    # Build docker run command
    local docker_cmd="docker run -d"
    docker_cmd="$docker_cmd --name $container_name"
    docker_cmd="$docker_cmd --network $DOCKER_NETWORK"
    docker_cmd="$docker_cmd --label com.docker.compose.project=$COMPOSE_PROJECT_NAME"
    docker_cmd="$docker_cmd --label com.docker.compose.service=ldes-consumer"
    docker_cmd="$docker_cmd --label ldes.config.file=$filename"
    docker_cmd="$docker_cmd -v /data/ldes-state-${container_name}:/state"
    docker_cmd="$docker_cmd -e LDES=$url"
    docker_cmd="$docker_cmd -e SPARQL_ENDPOINT=$sparql_endpoint"
    docker_cmd="$docker_cmd -e SHAPE=$shape"
    docker_cmd="$docker_cmd -e TARGET_GRAPH=$target_graph"
    docker_cmd="$docker_cmd -e FOLLOW=$follow"
    docker_cmd="$docker_cmd -e MATERIALIZE=$materialize"
    docker_cmd="$docker_cmd -e ORDER=$order"
    docker_cmd="$docker_cmd -e LAST_VERSION_ONLY=$last_version_only"
    docker_cmd="$docker_cmd -e FAILURE_IS_FATAL=$failure_is_fatal"
    docker_cmd="$docker_cmd -e POLLING_FREQUENCY=$polling_frequency"
    docker_cmd="$docker_cmd -e CONCURRENT_FETCHES=$concurrent_fetches"
    docker_cmd="$docker_cmd -e FOR_VIRTUOSO=$for_virtuoso"
    docker_cmd="$docker_cmd -e QUERY_TIMEOUT=$query_timeout"
    
    [ -n "$before" ] && docker_cmd="$docker_cmd -e BEFORE=$before"
    [ -n "$after" ] && docker_cmd="$docker_cmd -e AFTER=$after"
    [ -n "$access_token" ] && docker_cmd="$docker_cmd -e ACCESS_TOKEN=$access_token"
    [ -n "$perf_name" ] && docker_cmd="$docker_cmd -e PERF_NAME=$perf_name"
    
    docker_cmd="$docker_cmd $LDES2SPARQL_IMAGE"
    
    log_debug "Docker command: $docker_cmd"
    
    # Execute docker run
    if eval "$docker_cmd" >/dev/null 2>&1; then
        sleep 2
        
        # Verify container is running
        if docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null | grep -q "true"; then
            log_info "Successfully started container: $container_name"
            ACTIVE_CONTAINERS[$filename]="$container_name"
            return 0
        else
            log_error "Container $container_name failed to start properly"
            docker logs "$container_name" 2>&1 | head -20 | while read -r line; do
                log_error "  $line"
            done
            return 1
        fi
    else
        log_error "Failed to start container $container_name"
        return 1
    fi
}

# Function to stop a container
stop_container() {
    local filename="$1"
    local container_name="${ACTIVE_CONTAINERS[$filename]:-}"
    
    if [ -z "$container_name" ]; then
        log_warning "No active container found for $filename"
        return 1
    fi
    
    log_info "Stopping container: $container_name"
    
    if docker stop "$container_name" >/dev/null 2>&1; then
        docker rm "$container_name" >/dev/null 2>&1 || true
        unset ACTIVE_CONTAINERS[$filename]
        log_info "Successfully stopped and removed container: $container_name"
        return 0
    else
        log_error "Failed to stop container: $container_name"
        return 1
    fi
}

# Function to cleanup all containers on exit
cleanup_all_containers() {
    log_info "Shutting down all LDES consumers..."
    for filename in "${!ACTIVE_CONTAINERS[@]}"; do
        stop_container "$filename"
    done
}

# Trap signals for graceful shutdown
trap cleanup_all_containers EXIT SIGTERM SIGINT

# Function to spawn containers from legacy config file
spawn_from_legacy_file() {
    local config_file="$1"
    
    log_info "Parsing legacy configuration file..."
    
    # Extract feed definitions using simple grep/sed approach
    # This assumes feeds are in the format:
    # feeds:
    #   - name: feed1
    #     url: http://...
    #     sparql_endpoint: http://...
    
    local in_feeds=0
    local feed_count=0
    declare -A current_feed
    
    while IFS= read -r line; do
        # Check if we're in the feeds section
        if echo "$line" | grep -q "^feeds:"; then
            in_feeds=1
            continue
        fi
        
        if [ $in_feeds -eq 1 ]; then
            # New feed starts with "  - name:"
            if echo "$line" | grep -q "^  - name:"; then
                # Process previous feed if exists
                if [ ${#current_feed[@]} -gt 0 ]; then
                    spawn_legacy_feed
                    current_feed=()
                fi
                
                # Start new feed
                local name=$(echo "$line" | sed 's/^  - name:[[:space:]]*//' | sed 's/^["'\'']//' | sed 's/["'\'']$//')
                current_feed[name]="$name"
                ((feed_count++))
            # Other feed properties
            elif echo "$line" | grep -q "^    "; then
                local key=$(echo "$line" | sed 's/^[[:space:]]*//' | cut -d: -f1)
                local value=$(echo "$line" | sed "s/^[[:space:]]*${key}:[[:space:]]*//" | sed 's/^["'\'']//' | sed 's/["'\'']$//')
                current_feed[$key]="$value"
            fi
        fi
    done < "$config_file"
    
    # Process last feed
    if [ ${#current_feed[@]} -gt 0 ]; then
        spawn_legacy_feed
    fi
    
    if [ $feed_count -eq 0 ]; then
        log_error "No feeds defined in configuration file"
        exit 1
    fi
    
    log_info "Successfully started $feed_count LDES consumer(s)"
}

# Helper function to spawn a single feed from legacy config
spawn_legacy_feed() {
    local feed_name="${current_feed[name]:-unnamed}"
    local url="${current_feed[url]:-}"
    local sparql_endpoint="${current_feed[sparql_endpoint]:-}"
    
    if [ -z "$url" ] || [ -z "$sparql_endpoint" ]; then
        log_error "Feed '$feed_name' is missing required 'url' or 'sparql_endpoint'"
        return 1
    fi
    
    local container_name="ldes-consumer-${feed_name}"
    
    # Get optional fields with defaults
    local shape="${current_feed[shape]:-}"
    local target_graph="${current_feed[target_graph]:-}"
    local follow="${current_feed[follow]:-true}"
    local materialize="${current_feed[materialize]:-false}"
    local order="${current_feed[order]:-none}"
    local last_version_only="${current_feed[last_version_only]:-false}"
    local failure_is_fatal="${current_feed[failure_is_fatal]:-false}"
    local concurrent_fetches="${current_feed[concurrent_fetches]:-10}"
    local for_virtuoso="${current_feed[for_virtuoso]:-false}"
    local query_timeout="${current_feed[query_timeout]:-1800}"
    local polling_interval="${current_feed[polling_interval]:-60}"
    
    # Convert polling_interval to milliseconds
    local polling_frequency=$((polling_interval * 1000))
    
    log_info "Starting LDES consumer for feed: $feed_name"
    log_info "  URL: $url"
    log_info "  SPARQL Endpoint: $sparql_endpoint"
    
    # Build and execute docker run command
    local docker_cmd="docker run -d"
    docker_cmd="$docker_cmd --name $container_name"
    docker_cmd="$docker_cmd --network $DOCKER_NETWORK"
    docker_cmd="$docker_cmd --label com.docker.compose.project=$COMPOSE_PROJECT_NAME"
    docker_cmd="$docker_cmd --label com.docker.compose.service=ldes-consumer"
    docker_cmd="$docker_cmd -v /data/ldes-state-${feed_name}:/state"
    docker_cmd="$docker_cmd -e LDES=$url"
    docker_cmd="$docker_cmd -e SPARQL_ENDPOINT=$sparql_endpoint"
    docker_cmd="$docker_cmd -e SHAPE=$shape"
    docker_cmd="$docker_cmd -e TARGET_GRAPH=$target_graph"
    docker_cmd="$docker_cmd -e FOLLOW=$follow"
    docker_cmd="$docker_cmd -e MATERIALIZE=$materialize"
    docker_cmd="$docker_cmd -e ORDER=$order"
    docker_cmd="$docker_cmd -e LAST_VERSION_ONLY=$last_version_only"
    docker_cmd="$docker_cmd -e FAILURE_IS_FATAL=$failure_is_fatal"
    docker_cmd="$docker_cmd -e POLLING_FREQUENCY=$polling_frequency"
    docker_cmd="$docker_cmd -e CONCURRENT_FETCHES=$concurrent_fetches"
    docker_cmd="$docker_cmd -e FOR_VIRTUOSO=$for_virtuoso"
    docker_cmd="$docker_cmd -e QUERY_TIMEOUT=$query_timeout"
    docker_cmd="$docker_cmd $LDES2SPARQL_IMAGE"
    
    if eval "$docker_cmd" >/dev/null 2>&1; then
        sleep 2
        if docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null | grep -q "true"; then
            log_info "Successfully started container: $container_name"
            ACTIVE_CONTAINERS[$feed_name]="$container_name"
            return 0
        else
            log_error "Container $container_name failed to start"
            return 1
        fi
    else
        log_error "Failed to spawn container for feed: $feed_name"
        return 1
    fi
}

# Function to watch folder for changes
watch_folder() {
    local folder="$1"
    
    log_info "Scanning directory for YAML files: $folder"
    
    # Initial scan - start containers for existing files
    for yaml_file in "$folder"/*.yaml "$folder"/*.yml; do
        if [ -f "$yaml_file" ]; then
            spawn_container "$yaml_file"
        fi
    done
    
    log_info "File watcher started. Monitoring for changes..."
    log_info "Press Ctrl+C to stop"
    
    # Use inotifywait to watch for file changes
    inotifywait -m -e create,delete,modify,moved_to,moved_from "$folder" 2>/dev/null | \
    while read -r directory events filename; do
        # Only process YAML files
        if [[ "$filename" =~ \.(yaml|yml)$ ]]; then
            local full_path="$directory$filename"
            
            case "$events" in
                *CREATE* | *MOVED_TO*)
                    log_info "Detected new YAML file: $filename"
                    sleep 1  # Brief delay to ensure file is fully written
                    spawn_container "$full_path"
                    ;;
                *DELETE* | *MOVED_FROM*)
                    log_info "Detected deleted YAML file: $filename"
                    stop_container "$filename"
                    ;;
                *MODIFY*)
                    log_info "Detected modified YAML file: $filename"
                    # Stop existing container and restart with new config
                    if [ -n "${ACTIVE_CONTAINERS[$filename]:-}" ]; then
                        stop_container "$filename"
                    fi
                    sleep 1
                    spawn_container "$full_path"
                    ;;
            esac
        fi
    done &
    
    local watcher_pid=$!
    
    # Monitor container health
    while true; do
        sleep 30
        
        for filename in "${!ACTIVE_CONTAINERS[@]}"; do
            local container_name="${ACTIVE_CONTAINERS[$filename]}"
            
            if ! docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null | grep -q "true"; then
                log_warning "Container $container_name is not running, restarting..."
                unset ACTIVE_CONTAINERS[$filename]
                
                local yaml_path="$folder/$filename"
                if [ -f "$yaml_path" ]; then
                    spawn_container "$yaml_path"
                fi
            fi
        done
    done
}

# Main execution logic
if [ -z "$LDES_CONFIG_PATH" ]; then
    # Mode 1: Direct mode - no config path provided
    echo "=== Running in DIRECT mode ==="
    echo "No LDES_CONFIG_PATH provided, running as direct ldes2sparql container"
    echo "Using environment variables for configuration"
    
    # Check if required environment variables are set
    if [ -z "$LDES" ]; then
        echo "ERROR: LDES environment variable is required in direct mode"
        echo "Please set LDES to the URL of your LDES feed"
        exit 1
    fi
    
    if [ -z "$SPARQL_ENDPOINT" ]; then
        echo "ERROR: SPARQL_ENDPOINT environment variable is required in direct mode"
        echo "Please set SPARQL_ENDPOINT to your SPARQL endpoint URL"
        exit 1
    fi
    
    echo "LDES: $LDES"
    echo "SPARQL_ENDPOINT: $SPARQL_ENDPOINT"
    
    # Install Node.js and dependencies as in the ldes2sparql Dockerfile
    echo "Installing Node.js and ldes2sparql dependencies..."
    
    # Install Node.js LTS (pinned version for security)
    NODEJS_VERSION="20.x"
    curl -fsSL "https://deb.nodesource.com/setup_${NODEJS_VERSION}" | bash -
    apt-get install -y nodejs
    
    # Clone and setup ldes2sparql
    cd /tmp
    git clone https://github.com/rdf-connect/ldes2sparql.git
    cd ldes2sparql
    
    # Create state and performance directories
    mkdir -p /state
    mkdir -p /performance
    
    # Install dependencies
    npm ci
    
    # Make run.sh executable
    chmod +x run.sh
    
    # Set default environment variables if not provided
    export SHAPE="${SHAPE:-}"
    export TARGET_GRAPH="${TARGET_GRAPH:-}"
    export FAILURE_IS_FATAL="${FAILURE_IS_FATAL:-false}"
    export FOLLOW="${FOLLOW:-true}"
    export MATERIALIZE="${MATERIALIZE:-false}"
    export ORDER="${ORDER:-none}"
    export POLLING_FREQUENCY="${POLLING_FREQUENCY:-5000}"
    export CONCURRENT_FETCHES="${CONCURRENT_FETCHES:-10}"
    export FOR_VIRTUOSO="${FOR_VIRTUOSO:-false}"
    export QUERY_TIMEOUT="${QUERY_TIMEOUT:-1800}"
    export LAST_VERSION_ONLY="${LAST_VERSION_ONLY:-false}"
    
    # Execute the ldes2sparql run.sh script
    echo "Starting ldes2sparql..."
    exec ./run.sh

elif [ -d "$LDES_CONFIG_PATH" ]; then
    # Mode 2: Folder watcher mode
    echo "=== Running in FOLDER WATCHER mode ==="
    echo "Configuration directory: $LDES_CONFIG_PATH"
    echo "Using ldes2sparql image: $LDES2SPARQL_IMAGE"
    
    # Make sure that the ldes2sparql image is available
    echo "Pulling ldes2sparql image..."
    docker pull "$LDES2SPARQL_IMAGE"
    
    # Start folder watcher
    watch_folder "$LDES_CONFIG_PATH"

elif [ -f "$LDES_CONFIG_PATH" ]; then
    # Mode 3: Legacy single file mode
    echo "=== Running in LEGACY SINGLE FILE mode ==="
    echo "Configuration file: $LDES_CONFIG_PATH"
    echo "Using ldes2sparql image: $LDES2SPARQL_IMAGE"
    
    # Make sure that the ldes2sparql image is available
    echo "Pulling ldes2sparql image..."
    docker pull "$LDES2SPARQL_IMAGE"
    
    # Parse YAML and start ldes2sparql instances
    spawn_from_legacy_file "$LDES_CONFIG_PATH"
    
    # Monitor containers
    log_info "Containers running in detached mode"
    log_info "Monitoring containers... (Press Ctrl+C to stop)"
    
    while true; do
        sleep 30
        
        for filename in "${!ACTIVE_CONTAINERS[@]}"; do
            local container_name="${ACTIVE_CONTAINERS[$filename]}"
            
            if ! docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null | grep -q "true"; then
                log_warning "Container $container_name is not running. It may have stopped or been removed."
            fi
        done
    done

else
    echo "ERROR: LDES_CONFIG_PATH does not point to a valid file or directory: $LDES_CONFIG_PATH"
    echo ""
    echo "Usage modes:"
    echo "1. Direct mode: Do not set LDES_CONFIG_PATH, use LDES and SPARQL_ENDPOINT environment variables"
    echo "2. Folder mode: Set LDES_CONFIG_PATH to a directory containing YAML files"
    echo "3. Legacy mode: Set LDES_CONFIG_PATH to a single YAML file"
    exit 1
fi
