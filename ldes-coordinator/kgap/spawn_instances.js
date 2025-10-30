#!/usr/bin/env node
/**
 * LDES Coordinator Spawner
 * Manages spawning and monitoring of ldes2sparql consumer container instances
 */

const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// Configuration from environment (passed by entrypoint.sh)
const LDES_CONFIG_PATH = process.env.LDES_CONFIG_PATH || '';
const DOCKER_IMAGE = process.env.DOCKER_IMAGE;
const DOCKER_NETWORK = process.env.DOCKER_NETWORK;
const COMPOSE_PROJECT_NAME = process.env.COMPOSE_PROJECT_NAME;
const LOG_LEVEL = process.env.LOG_LEVEL || 'INFO';
const LOCK_FILE = path.join(LDES_CONFIG_PATH, '.spawn.lock');

// Track active containers
const activeContainers = new Map();

// Logging functions
function log(level, ...args) {
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const levels = { DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3 };
    const currentLevel = levels[LOG_LEVEL] || 1;
    
    if (levels[level] >= currentLevel) {
        console.log(`${timestamp} - ldes-coordinator - ${level} -`, ...args);
    }
}

// Acquire lock to prevent competing spawning instances
async function acquireLock() {
    const maxRetries = 10;
    const retryDelay = 1000;
    
    for (let i = 0; i < maxRetries; i++) {
        try {
            // Try to create lock file exclusively
            fs.writeFileSync(LOCK_FILE, process.pid.toString(), { flag: 'wx' });
            log('INFO', 'Lock acquired');
            return true;
        } catch (error) {
            if (error.code === 'EEXIST') {
                // Lock file exists, check if process is still running
                try {
                    const pid = parseInt(fs.readFileSync(LOCK_FILE, 'utf8'));
                    try {
                        process.kill(pid, 0); // Check if process exists
                        log('DEBUG', `Lock held by process ${pid}, waiting...`);
                        await new Promise(resolve => setTimeout(resolve, retryDelay));
                    } catch {
                        // Process doesn't exist, remove stale lock
                        log('WARNING', 'Removing stale lock file');
                        fs.unlinkSync(LOCK_FILE);
                    }
                } catch {
                    // Can't read lock file, remove it
                    try {
                        fs.unlinkSync(LOCK_FILE);
                    } catch {}
                }
            } else {
                throw error;
            }
        }
    }
    
    throw new Error('Failed to acquire lock after maximum retries');
}

// Release lock
function releaseLock() {
    try {
        if (fs.existsSync(LOCK_FILE)) {
            fs.unlinkSync(LOCK_FILE);
            log('INFO', 'Lock released');
        }
    } catch (error) {
        log('ERROR', 'Failed to release lock:', error.message);
    }
}

// Parse YAML file (simple key-value extraction)
function parseYamlValue(content, key, defaultValue = '') {
    const regex = new RegExp(`^${key}:\\s*(.*)$`, 'm');
    const match = content.match(regex);
    if (!match) return defaultValue;
    
    let value = match[1].trim();
    // Remove quotes if present
    value = value.replace(/^["']|["']$/g, '');
    return value;
}

// Load and validate YAML config
function loadYamlConfig(filePath) {
    try {
        const content = fs.readFileSync(filePath, 'utf8');
        const url = parseYamlValue(content, 'url');
        const sparqlEndpoint = parseYamlValue(content, 'sparql_endpoint');
        
        if (!url || !sparqlEndpoint) {
            log('ERROR', `YAML file ${filePath} missing required fields 'url' or 'sparql_endpoint'`);
            return null;
        }
        
        return {
            url,
            sparql_endpoint: sparqlEndpoint,
            shape: parseYamlValue(content, 'shape', ''),
            target_graph: parseYamlValue(content, 'target_graph', ''),
            follow: parseYamlValue(content, 'follow', 'true'),
            materialize: parseYamlValue(content, 'materialize', 'false'),
            order: parseYamlValue(content, 'order', 'none'),
            last_version_only: parseYamlValue(content, 'last_version_only', 'false'),
            failure_is_fatal: parseYamlValue(content, 'failure_is_fatal', 'false'),
            polling_interval: parseInt(parseYamlValue(content, 'polling_interval', '5')),
            concurrent_fetches: parseInt(parseYamlValue(content, 'concurrent_fetches', '10')),
            for_virtuoso: parseYamlValue(content, 'for_virtuoso', 'false'),
            query_timeout: parseInt(parseYamlValue(content, 'query_timeout', '1800')),
            before: parseYamlValue(content, 'before', ''),
            after: parseYamlValue(content, 'after', ''),
            access_token: parseYamlValue(content, 'access_token', ''),
            perf_name: parseYamlValue(content, 'perf_name', '')
        };
    } catch (error) {
        log('ERROR', `Failed to load YAML file ${filePath}:`, error.message);
        return null;
    }
}

// Generate container name from filename
function getContainerName(filename) {
    let name = filename.replace(/\.(yaml|yml)$/, '');
    name = name.replace(/[_ ]/g, '-').toLowerCase();
    return `ldes-consumer-${name}`;
}

// Spawn a container from YAML config
async function spawnContainer(yamlPath) {
    const filename = path.basename(yamlPath);
    
    if (activeContainers.has(filename)) {
        log('WARNING', `Container already exists for ${filename}`);
        return false;
    }
    
    const config = loadYamlConfig(yamlPath);
    if (!config) return false;
    
    const containerName = getContainerName(filename);
    const pollingFrequency = config.polling_interval * 1000;
    
    log('INFO', `Starting LDES consumer from config file: ${filename}`);
    log('INFO', `  Container name: ${containerName}`);
    log('INFO', `  URL: ${config.url}`);
    log('INFO', `  SPARQL Endpoint: ${config.sparql_endpoint}`);
    
    // Build docker run command
    const dockerArgs = [
        'run', '-d',
        '--name', containerName,
        '--network', DOCKER_NETWORK,
        '--label', `com.docker.compose.project=${COMPOSE_PROJECT_NAME}`,
        '--label', 'com.docker.compose.service=ldes-consumer',
        '--label', `ldes.config.file=${filename}`,
        '-v', `/data/ldes-state-${containerName}:/state`,
        '-e', `LDES=${config.url}`,
        '-e', `SPARQL_ENDPOINT=${config.sparql_endpoint}`,
        '-e', `SHAPE=${config.shape}`,
        '-e', `TARGET_GRAPH=${config.target_graph}`,
        '-e', `FOLLOW=${config.follow}`,
        '-e', `MATERIALIZE=${config.materialize}`,
        '-e', `ORDER=${config.order}`,
        '-e', `LAST_VERSION_ONLY=${config.last_version_only}`,
        '-e', `FAILURE_IS_FATAL=${config.failure_is_fatal}`,
        '-e', `POLLING_FREQUENCY=${pollingFrequency}`,
        '-e', `CONCURRENT_FETCHES=${config.concurrent_fetches}`,
        '-e', `FOR_VIRTUOSO=${config.for_virtuoso}`,
        '-e', `QUERY_TIMEOUT=${config.query_timeout}`
    ];
    
    // Add optional environment variables
    if (config.before) dockerArgs.push('-e', `BEFORE=${config.before}`);
    if (config.after) dockerArgs.push('-e', `AFTER=${config.after}`);
    if (config.access_token) dockerArgs.push('-e', `ACCESS_TOKEN=${config.access_token}`);
    if (config.perf_name) dockerArgs.push('-e', `PERF_NAME=${config.perf_name}`);
    
    // Use the image passed from entrypoint
    dockerArgs.push(DOCKER_IMAGE);
    
    log('DEBUG', 'Docker command:', 'docker', dockerArgs.join(' '));
    
    try {
        await execAsync(`docker ${dockerArgs.join(' ')}`);
        
        // Wait for container to start
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Verify container is running
        const { stdout } = await execAsync(`docker inspect -f '{{.State.Running}}' ${containerName}`);
        if (stdout.trim() === 'true') {
            log('INFO', `Successfully started container: ${containerName}`);
            activeContainers.set(filename, containerName);
            return true;
        } else {
            log('ERROR', `Container ${containerName} failed to start properly`);
            const { stdout: logs } = await execAsync(`docker logs ${containerName}`);
            log('ERROR', 'Container logs:', logs.substring(0, 500));
            return false;
        }
    } catch (error) {
        log('ERROR', `Failed to start container ${containerName}:`, error.message);
        return false;
    }
}

// Stop a container
async function stopContainer(filename) {
    const containerName = activeContainers.get(filename);
    
    if (!containerName) {
        log('WARNING', `No active container found for ${filename}`);
        return false;
    }
    
    log('INFO', `Stopping container: ${containerName}`);
    
    try {
        await execAsync(`docker stop ${containerName}`);
        await execAsync(`docker rm ${containerName}`).catch(() => {});
        activeContainers.delete(filename);
        log('INFO', `Successfully stopped and removed container: ${containerName}`);
        return true;
    } catch (error) {
        log('ERROR', `Failed to stop container ${containerName}:`, error.message);
        return false;
    }
}

// Watch folder for changes
async function watchFolder(folder) {
    log('INFO', `Scanning directory for YAML files: ${folder}`);
    
    // Initial scan - start containers for existing files
    const files = fs.readdirSync(folder)
        .filter(f => f.endsWith('.yaml') || f.endsWith('.yml'))
        .filter(f => f !== '.spawn.lock');
    
    for (const file of files) {
        await spawnContainer(path.join(folder, file));
    }
    
    log('INFO', 'File watcher started. Monitoring for changes...');
    
    // Watch for file changes
    fs.watch(folder, async (eventType, filename) => {
        if (!filename || (!filename.endsWith('.yaml') && !filename.endsWith('.yml'))) {
            return;
        }
        
        if (filename === '.spawn.lock') return;
        
        const filePath = path.join(folder, filename);
        
        // Wait a bit for file operations to complete
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        if (eventType === 'rename') {
            // File created or deleted
            if (fs.existsSync(filePath)) {
                log('INFO', `Detected new YAML file: ${filename}`);
                await spawnContainer(filePath);
            } else {
                log('INFO', `Detected deleted YAML file: ${filename}`);
                await stopContainer(filename);
            }
        } else if (eventType === 'change') {
            log('INFO', `Detected modified YAML file: ${filename}`);
            // Stop existing container and restart with new config
            if (activeContainers.has(filename)) {
                await stopContainer(filename);
            }
            if (fs.existsSync(filePath)) {
                await spawnContainer(filePath);
            }
        }
    });
    
    // Monitor container health
    setInterval(async () => {
        for (const [filename, containerName] of activeContainers.entries()) {
            try {
                const { stdout } = await execAsync(`docker inspect -f '{{.State.Running}}' ${containerName}`);
                if (stdout.trim() !== 'true') {
                    log('WARNING', `Container ${containerName} is not running, restarting...`);
                    activeContainers.delete(filename);
                    
                    const yamlPath = path.join(folder, filename);
                    if (fs.existsSync(yamlPath)) {
                        await spawnContainer(yamlPath);
                    }
                }
            } catch (error) {
                log('ERROR', `Error checking container ${containerName}:`, error.message);
            }
        }
    }, 30000);
    
    // Keep process alive
    process.stdin.resume();
}

// Cleanup on exit
async function cleanup() {
    log('INFO', 'Shutting down all LDES consumers...');
    
    for (const filename of activeContainers.keys()) {
        await stopContainer(filename);
    }
    
    releaseLock();
    process.exit(0);
}

// Main function
async function main() {
    try {
        log('INFO', 'LDES Coordinator starting...');
        log('INFO', `Using image: ${DOCKER_IMAGE}`);
        log('INFO', `Using network: ${DOCKER_NETWORK}`);
        log('INFO', `Using project: ${COMPOSE_PROJECT_NAME}`);
        
        // Acquire lock
        await acquireLock();
        
        // Determine mode based on LDES_CONFIG_PATH
        if (!fs.existsSync(LDES_CONFIG_PATH)) {
            log('ERROR', `LDES_CONFIG_PATH does not exist: ${LDES_CONFIG_PATH}`);
            process.exit(1);
        }
        
        const stats = fs.statSync(LDES_CONFIG_PATH);
        
        if (stats.isDirectory()) {
            // Folder mode
            log('INFO', `Folder mode: watching ${LDES_CONFIG_PATH}`);
            await watchFolder(LDES_CONFIG_PATH);
        } else if (stats.isFile()) {
            log('ERROR', 'Single file mode is no longer supported');
            log('ERROR', 'Please use folder mode with individual YAML files');
            log('ERROR', 'See /kgap/feed-config.yaml.example for template');
            process.exit(1);
        } else {
            log('ERROR', `LDES_CONFIG_PATH is neither a file nor directory: ${LDES_CONFIG_PATH}`);
            process.exit(1);
        }
        
    } catch (error) {
        log('ERROR', 'Fatal error:', error.message);
        releaseLock();
        process.exit(1);
    }
}

// Handle signals
process.on('SIGTERM', cleanup);
process.on('SIGINT', cleanup);

// Run main
main().catch(error => {
    log('ERROR', 'Unhandled error:', error);
    releaseLock();
    process.exit(1);
});
