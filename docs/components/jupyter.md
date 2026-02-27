---
title: Jupyter Component
parent: Components
nav_order: 2
---

# Jupyter Component

The Jupyter component provides an interactive notebook environment for exploring, analyzing, and visualizing knowledge graph data.

## Overview

The Jupyter component is built on the official Jupyter base notebook and includes pre-configured tools for working with RDF/SPARQL data and the K-GAP platform.

**Base Image**: `jupyter/base-notebook`  
**Exposed Port**: 8889 (maps to internal port 8888)  
**Container Name**: `test_kgap_jupyter` (in test setup)

## Features

- Interactive Python notebooks
- Pre-installed RDF and SPARQL libraries
- Direct connection to GraphDB repository
- Template notebooks for common tasks
- Shared data and notebook volumes
- No authentication required (configurable)

## Architecture

```
┌────────────────────────────────────────┐
│        Jupyter Container               │
├────────────────────────────────────────┤
│                                        │
│  entrypoint-wrap.sh                   │
│       │                                │
│       └─▶ Start Jupyter Notebook      │
│           - No token authentication    │
│           - Port 8888                  │
│                                        │
│  Pre-installed Tools:                  │
│  - pykg2tbl (SPARQL → DataFrame)      │
│  - kgap_tools.py helper functions      │
│  - pandas, numpy, etc.                 │
│                                        │
│  Volumes:                              │
│  - ./notebooks → /notebooks           │
│  - ./data → /data                     │
│                                        │
└────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GDB_BASE` | `http://graphdb:7200/` | GraphDB base URL |
| `GDB_REPO` | `kgap` | GraphDB repository name |
| `NOTEBOOK_ARGS` | `--NotebookApp.token=''` | Jupyter configuration arguments |
| `SRC_FOLDER` | `/kgap/notebooks` | Source folder for notebooks |

### Dependencies

The Jupyter image includes the following Python packages (defined in `jupyter/kgap/requirements.txt`):

```
pykg2tbl
```

Additional packages can be installed at runtime using `!pip install` in notebooks.

## File Structure

```
jupyter/
├── Dockerfile                        # Image definition
└── kgap/
    ├── entrypoint-wrap.sh           # Startup script
    ├── requirements.txt             # Python dependencies
    └── notebooks/
        ├── kgap_tools.py            # Helper functions
        └── kgap_template.ipynb      # Template notebook
```

### kgap_tools.py

This module provides convenience functions for working with GraphDB:

```python
from pykg2tbl import DefaultSparqlBuilder, KGSource, QueryResult
from pathlib import Path
from pandas import DataFrame
import os

# SPARQL EndPoint - configured from environment
GDB_BASE: str = os.getenv("GDB_BASE", "http://localhost:7200/")
GDB_REPO: str = os.getenv("GDB_REPO", "kgap")
GDB_ENDPOINT: str = f"{GDB_BASE}repositories/{GDB_REPO}"
GDB: KGSource = KGSource.build(GDB_ENDPOINT)

# Template-based SPARQL query builder
TEMPLATES_FOLDER = str(Path().absolute() / "queries")
GENERATOR = DefaultSparqlBuilder(templates_folder=TEMPLATES_FOLDER)

def generate_sparql(name: str, **vars) -> str:
    """Build SPARQL query from template with variables"""
    return GENERATOR.build_syntax(name, **vars)

def execute_to_df(name: str, **vars) -> DataFrame:
    """Execute template query and return results as DataFrame"""
    sparql = generate_sparql(name, **vars)
    result: QueryResult = GDB.query(sparql=sparql)
    return result.to_dataframe()

class ExternalEndPoint:
    """Helper for querying external SPARQL endpoints"""
    def __init__(self, src: KGSource):
        self.src = src
    
    def execute_to_df(self, name: str, **vars) -> DataFrame:
        return _execute_to_df(self.src, name, **vars)
```

## Usage

### Accessing Jupyter

Navigate to http://localhost:8889 in your browser. No password/token is required by default.

### Basic Notebook Operations

#### 1. Querying GraphDB

```python
from kgap_tools import execute_to_df, GDB

# Method 1: Using template queries
df = execute_to_df('my_query_template', param1='value', param2=123)
display(df)

# Method 2: Direct SPARQL query
from pykg2tbl import KGSource

sparql = """
SELECT ?s ?p ?o
WHERE {
    ?s ?p ?o .
}
LIMIT 10
"""

result = GDB.query(sparql=sparql)
df = result.to_dataframe()
display(df)
```

#### 2. Working with Query Templates

Create query templates in `notebooks/queries/` directory:

**File: `notebooks/queries/count_triples.sparql`**
```sparql
SELECT (COUNT(*) as ?count)
WHERE {
    ?s ?p ?o .
}
```

**In notebook**:
```python
from kgap_tools import execute_to_df

df = execute_to_df('count_triples')
print(f"Total triples: {df['count'][0]}")
```

#### 3. Parameterized Queries

**File: `notebooks/queries/get_by_type.sparql`**
```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?subject ?label
WHERE {
    ?subject rdf:type <${type_uri}> .
    OPTIONAL { ?subject rdfs:label ?label . }
}
LIMIT ${limit}
```

**In notebook**:
```python
df = execute_to_df(
    'get_by_type',
    type_uri='http://example.org/Person',
    limit=100
)
display(df)
```

#### 4. Querying External Endpoints

```python
from kgap_tools import ExternalEndPoint
from pykg2tbl import KGSource

# Connect to external endpoint
external_ep = KGSource.build("https://dbpedia.org/sparql")
external = ExternalEndPoint(external_ep)

# Query external endpoint
sparql = """
SELECT ?label ?abstract
WHERE {
    <http://dbpedia.org/resource/Python_(programming_language)> 
        rdfs:label ?label ;
        dbo:abstract ?abstract .
    FILTER(LANG(?label) = 'en')
    FILTER(LANG(?abstract) = 'en')
}
"""
result = external_ep.query(sparql=sparql)
df = result.to_dataframe()
display(df)
```

#### 5. Data Visualization

```python
import matplotlib.pyplot as plt
import pandas as pd

# Query data
df = execute_to_df('count_by_type')

# Visualize
df.plot(kind='bar', x='type', y='count', figsize=(12, 6))
plt.title('Entity Count by Type')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
```

#### 6. Working with Data Files

```python
import pandas as pd
from pathlib import Path

# Data directory is mounted at /data
data_dir = Path('/data')

# Read CSV file
df = pd.read_csv(data_dir / 'input.csv')

# Process data
# ...

# Write results
df.to_csv(data_dir / 'output.csv', index=False)
```

### Installing Additional Packages

Within a notebook:

```python
# Install packages for current session
!pip install rdflib
!pip install networkx matplotlib
```

For permanent installation, update `jupyter/kgap/requirements.txt` and rebuild the image.

### Saving and Sharing Notebooks

Notebooks are automatically saved to the `./notebooks` directory on the host machine, which is mounted into the container. This means:

- Notebooks persist across container restarts
- You can edit notebooks using local tools
- Notebooks can be version controlled with git

## Template Notebook

The included template (`kgap_template.ipynb`) demonstrates:

- Connecting to GraphDB
- Running basic SPARQL queries
- Converting results to DataFrames
- Basic data visualization

To use it:

1. Open http://localhost:8889
2. Open `kgap_template.ipynb`
3. Run cells to see examples
4. Duplicate and modify for your needs

## Common Patterns

### Pattern 1: Exploratory Data Analysis

```python
from kgap_tools import GDB

# Count total triples
total = GDB.query("SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }")
print(f"Total triples: {total.to_dataframe()['count'][0]}")

# Get all predicate types
predicates = GDB.query("""
    SELECT DISTINCT ?p (COUNT(?s) as ?usage)
    WHERE { ?s ?p ?o }
    GROUP BY ?p
    ORDER BY DESC(?usage)
""")
print("Most used predicates:")
display(predicates.to_dataframe().head(20))

# Get all RDF types
types = GDB.query("""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?type (COUNT(?s) as ?count)
    WHERE { ?s rdf:type ?type }
    GROUP BY ?type
    ORDER BY DESC(?count)
""")
print("Entity types:")
display(types.to_dataframe())
```

### Pattern 2: Data Quality Checks

```python
# Check for missing labels
missing_labels = GDB.query("""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?entity ?type
    WHERE {
        ?entity rdf:type ?type .
        FILTER NOT EXISTS { ?entity rdfs:label ?label }
    }
    LIMIT 100
""")
df = missing_labels.to_dataframe()
print(f"Entities without labels: {len(df)}")
display(df)
```

### Pattern 3: Exporting Results

```python
import pandas as pd

# Query data
df = execute_to_df('my_export_query')

# Export to various formats
df.to_csv('/data/export.csv', index=False)
df.to_json('/data/export.json', orient='records')
df.to_excel('/data/export.xlsx', index=False)

print(f"Exported {len(df)} rows")
```

## Troubleshooting

### Cannot Connect to GraphDB

**Check GraphDB is running**:
```python
from kgap_tools import GDB
try:
    result = GDB.query("ASK { ?s ?p ?o }")
    print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
```

**Verify endpoint**:
```python
import os
print(f"GraphDB endpoint: {os.getenv('GDB_BASE')}repositories/{os.getenv('GDB_REPO')}")
```

### Memory Errors

For large query results, use pagination:

```python
def paginated_query(sparql_template, page_size=1000):
    offset = 0
    all_results = []
    
    while True:
        query = f"{sparql_template} LIMIT {page_size} OFFSET {offset}"
        result = GDB.query(query)
        df = result.to_dataframe()
        
        if len(df) == 0:
            break
            
        all_results.append(df)
        offset += page_size
    
    return pd.concat(all_results, ignore_index=True)
```

### Package Import Errors

Install missing packages:
```python
!pip install package-name
```

For permanent installation, rebuild the image with updated requirements.

## Advanced Configuration

### Custom Startup Arguments

Modify `NOTEBOOK_ARGS` in `.env` or `docker-compose.yml`:

```yaml
environment:
  NOTEBOOK_ARGS: "--NotebookApp.token='my-secret-token'"
```

### Persistent Package Installation

Create a startup script in `notebooks/`:

**File: `notebooks/.jupyter_startup.py`**
```python
import subprocess
import sys

packages = ['rdflib', 'networkx', 'plotly']
for package in packages:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
```

## Best Practices

1. **Use Query Templates**: Store reusable queries as templates
2. **Limit Results**: Always use LIMIT in exploratory queries
3. **Version Control Notebooks**: Commit notebooks to git (use `.ipynb_checkpoints/` in `.gitignore`)
4. **Document Queries**: Add markdown cells explaining complex queries
5. **Modular Code**: Extract reusable functions to separate `.py` files
6. **Error Handling**: Wrap queries in try-except blocks for production code

## Performance Tips

- Use `SELECT` instead of `CONSTRUCT` when possible
- Add `LIMIT` clauses to prevent large result sets
- Filter early in the query (move `FILTER` clauses up)
- Use `DISTINCT` sparingly (it can be expensive)
- Consider materialized views for frequently-run complex queries

## Related Documentation

- [Main Documentation](../index.md)
- [GraphDB Component](./graphdb.md) - SPARQL endpoint
- [Sembench Component](./sembench.md) - Automated processing
- [pykg2tbl Documentation](https://github.com/vliz-be-opsci/pykg2tbl) - SPARQL query library
