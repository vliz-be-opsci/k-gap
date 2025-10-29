#!/usr/bin/env node
/**
 * LDES Consumer Spawner
 * Manages spawning and monitoring of ldes2sparql container instances
 */

const fs = require('fs');
const path = require('path');
const { exec, spawn } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// Configuration
const LDES_CONFIG_PATH = process.env.LDES_CONFIG_PATH || '';
const DOCKER_NETWORK = process.env.DOCKER_NETWORK || 'kgap_default';
const COMPOSE_PROJECT_NAME = process.env.COMPOSE_PROJECT_NAME || 'kgap';
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
        console.log(`${timestamp} - ldes-spawner - ${level} -`, ...args);
    }
}

// Get own container info from hostname
async function getOwnContainerInfo() {
    try {
        const hostname = require('os').hostname();
        const { stdout } = await execAsync(`docker inspect ${hostname}`);
        const info = JSON.parse(stdout)[0];
        return {
            id: info.Id,
            name: info.Name.replace('/', ''),
            image: info.Config.Image
        };
    } catch (error) {
        log('ERROR', 'Failed to get own container info:', error.message);
        throw error;
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
async function spawnContainer(yamlPath, ownImage) {
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
    
    // Use own image
    dockerArgs.push(ownImage);
    
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
async function watchFolder(folder, ownImage) {
    log('INFO', `Scanning directory for YAML files: ${folder}`);
    
    // Initial scan - start containers for existing files
    const files = fs.readdirSync(folder)
        .filter(f => f.endsWith('.yaml') || f.endsWith('.yml'))
        .filter(f => f !== '.spawn.lock');
    
    for (const file of files) {
        await spawnContainer(path.join(folder, file), ownImage);
    }
    
    log('INFO', 'File watcher started. Monitoring for changes...');
    
    // Watch for file changes
    const watcher = fs.watch(folder, async (eventType, filename) => {
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
                await spawnContainer(filePath, ownImage);
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
                await spawnContainer(filePath, ownImage);
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
                        await spawnContainer(yamlPath, ownImage);
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

// Parse legacy config file
async function parseLegacyFile(configFile, ownImage) {
    log('INFO', 'Parsing legacy configuration file...');
    
    const content = fs.readFileSync(configFile, 'utf8');
    const lines = content.split('\n');
    
    const feeds = [];
    let currentFeed = null;
    let inFeeds = false;
    
    for (const line of lines) {
        if (line.match(/^feeds:/)) {
            inFeeds = true;
            continue;
        }
        
        if (inFeeds) {
            if (line.match(/^  - name:/)) {
                if (currentFeed) {
                    feeds.push(currentFeed);
                }
                currentFeed = { name: line.replace(/^  - name:\s*/, '').trim() };
            } else if (line.match(/^    \w+:/)) {
                const [key, ...valueParts] = line.trim().split(':');
                const value = valueParts.join(':').trim().replace(/^["']|["']$/g, '');
                currentFeed[key] = value;
            }
        }
    }
    
    if (currentFeed) {
        feeds.push(currentFeed);
    }
    
    if (feeds.length === 0) {
        log('ERROR', 'No feeds defined in configuration file');
        process.exit(1);
    }
    
    log('INFO', `Found ${feeds.length} feed(s) to process`);
    
    // Spawn containers for each feed
    for (const feed of feeds) {
        await spawnLegacyFeed(feed, ownImage);
    }
    
    log('INFO', `Successfully started ${feeds.length} LDES consumer(s)`);
}

// Spawn container from legacy feed config
async function spawnLegacyFeed(feed, ownImage) {
    const feedName = feed.name || 'unnamed';
    const url = feed.url;
    const sparqlEndpoint = feed.sparql_endpoint;
    
    if (!url || !sparqlEndpoint) {
        log('ERROR', `Feed '${feedName}' is missing required 'url' or 'sparql_endpoint'`);
        return false;
    }
    
    const containerName = `ldes-consumer-${feedName}`;
    const pollingInterval = parseInt(feed.polling_interval || '60');
    const pollingFrequency = pollingInterval * 1000;
    
    log('INFO', `Starting LDES consumer for feed: ${feedName}`);
    log('INFO', `  URL: ${url}`);
    log('INFO', `  SPARQL Endpoint: ${sparqlEndpoint}`);
    
    const dockerArgs = [
        'run', '-d',
        '--name', containerName,
        '--network', DOCKER_NETWORK,
        '--label', `com.docker.compose.project=${COMPOSE_PROJECT_NAME}`,
        '--label', 'com.docker.compose.service=ldes-consumer',
        '-v', `/data/ldes-state-${feedName}:/state`,
        '-e', `LDES=${url}`,
        '-e', `SPARQL_ENDPOINT=${sparqlEndpoint}`,
        '-e', `SHAPE=${feed.shape || ''}`,
        '-e', `TARGET_GRAPH=${feed.target_graph || ''}`,
        '-e', `FOLLOW=${feed.follow || 'true'}`,
        '-e', `MATERIALIZE=${feed.materialize || 'false'}`,
        '-e', `ORDER=${feed.order || 'none'}`,
        '-e', `LAST_VERSION_ONLY=${feed.last_version_only || 'false'}`,
        '-e', `FAILURE_IS_FATAL=${feed.failure_is_fatal || 'false'}`,
        '-e', `POLLING_FREQUENCY=${pollingFrequency}`,
        '-e', `CONCURRENT_FETCHES=${feed.concurrent_fetches || '10'}`,
        '-e', `FOR_VIRTUOSO=${feed.for_virtuoso || 'false'}`,
        '-e', `QUERY_TIMEOUT=${feed.query_timeout || '1800'}`,
        ownImage
    ];
    
    try {
        await execAsync(`docker ${dockerArgs.join(' ')}`);
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const { stdout } = await execAsync(`docker inspect -f '{{.State.Running}}' ${containerName}`);
        if (stdout.trim() === 'true') {
            log('INFO', `Successfully started container: ${containerName}`);
            activeContainers.set(feedName, containerName);
            return true;
        } else {
            log('ERROR', `Container ${containerName} failed to start`);
            return false;
        }
    } catch (error) {
        log('ERROR', `Failed to spawn container for feed '${feedName}':`, error.message);
        return false;
    }
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
        // Acquire lock
        await acquireLock();
        
        // Get own container info
        const ownInfo = await getOwnContainerInfo();
        log('INFO', `Running in container: ${ownInfo.name}`);
        log('INFO', `Using image: ${ownInfo.image}`);
        
        // Determine mode based on LDES_CONFIG_PATH
        if (fs.statSync(LDES_CONFIG_PATH).isDirectory()) {
            // Folder mode
            log('INFO', `Folder mode: watching ${LDES_CONFIG_PATH}`);
            await watchFolder(LDES_CONFIG_PATH, ownInfo.image);
        } else if (fs.statSync(LDES_CONFIG_PATH).isFile()) {
            // Legacy file mode
            log('INFO', `Legacy mode: reading ${LDES_CONFIG_PATH}`);
            await parseLegacyFile(LDES_CONFIG_PATH, ownInfo.image);
            
            // Monitor containers
            log('INFO', 'Monitoring containers... (Press Ctrl+C to stop)');
            setInterval(async () => {
                for (const [feedName, containerName] of activeContainers.entries()) {
                    try {
                        const { stdout } = await execAsync(`docker inspect -f '{{.State.Running}}' ${containerName}`);
                        if (stdout.trim() !== 'true') {
                            log('WARNING', `Container ${containerName} is not running`);
                        }
                    } catch (error) {
                        log('ERROR', `Error checking container ${containerName}:`, error.message);
                    }
                }
            }, 30000);
            
            // Keep process alive
            process.stdin.resume();
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
