---
title: Advanced Topics
nav_order: 5
---

# Advanced Topics

This section covers advanced K-GAP concepts and patterns.

## Table of Contents

- [Assertion Paths and Dereferencing](#assertion-paths-and-dereferencing)
- [Custom SPARQL Query Templates](#custom-sparql-query-templates)
- [Data Validation Patterns](#data-validation-patterns)
- [Performance Optimization](#performance-optimization)
- [Multi-Repository Setup](#multi-repository-setup)

## Assertion Paths and Dereferencing

**Note**: Assertion paths and dereferencing are concepts that may be implemented in the [py-sema](https://github.com/vliz-be-opsci/py-sema) library used by Sembench, rather than directly in K-GAP. This section provides context for these patterns.

### What Are Assertion Paths?

Assertion paths are patterns used in semantic data processing to:

1. **Define minimal requirements**: Specify the minimum properties required for valid data
2. **Enable dereferencing**: Automatically fetch related data beyond what's explicitly requested
3. **Validate data quality**: Assert that required properties exist
4. **Return more than requested**: Provide context by including related properties

### Dereferencing Pattern

Dereferencing in the context of linked data means following URIs to retrieve additional information about resources.

**Example scenario**:
```turtle
# You query for:
?observation a sosa:Observation .

# But you get back:
?observation a sosa:Observation ;
    sosa:madeBySensor ?sensor ;
    sosa:hasResult ?result .

?sensor rdfs:label "Temperature Sensor" ;
    sosa:isHostedBy ?platform .

?result qudt:numericValue 23.5 ;
    qudt:unit unit:DegreeCelsius .
```

The system automatically "dereferenced" the sensor and result URIs to include their properties.

### Configuration in Sembench/py-sema

If your sembench configuration uses dereferencing, it might look like:

```yaml
# Example sembench.yaml with dereferencing
workflows:
  - name: enrich-observations
    steps:
      - type: dereference
        source:
          endpoint: http://graphdb:7200/repositories/kgap
          query: |
            SELECT ?observation
            WHERE {
              ?observation a sosa:Observation .
            }
        
        # Assertion: Require these properties exist
        assertions:
          - path: sosa:madeBySensor
            required: true
          - path: sosa:hasResult
            required: true
        
        # Dereferencing: Also fetch these related properties
        dereference:
          - path: sosa:madeBySensor
            include:
              - rdfs:label
              - sosa:isHostedBy
          
          - path: sosa:hasResult
            include:
              - qudt:numericValue
              - qudt:unit
        
        # What happens:
        # 1. Query returns observations
        # 2. Assert each has required paths (fails if not)
        # 3. Dereference sensor and result URIs
        # 4. Return enriched data with all properties
```

### Assertion Patterns

Common assertion patterns validate data completeness:

#### Required Property Assertion

```yaml
assertions:
  - path: rdfs:label
    required: true
    message: "All entities must have labels"
```

#### Type Assertion

```yaml
assertions:
  - path: rdf:type
    values:
      - sosa:Observation
      - sosa:Sensor
    message: "Entity must be an Observation or Sensor"
```

#### Cardinality Assertion

```yaml
assertions:
  - path: sosa:observedProperty
    min: 1
    max: 1
    message: "Observation must have exactly one observed property"
```

#### Value Range Assertion

```yaml
assertions:
  - path: sosa:hasSimpleResult
    datatype: xsd:double
    min_value: 0
    max_value: 100
    message: "Result must be between 0 and 100"
```

### Using Assertions in SPARQL

You can also implement assertions directly in SPARQL queries:

```sparql
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# Query with assertion
SELECT ?observation ?sensor ?result
WHERE {
  ?observation a sosa:Observation .
  
  # Assert required properties exist
  ?observation sosa:madeBySensor ?sensor .
  ?observation sosa:hasResult ?result .
  
  # Dereference sensor
  ?sensor rdfs:label ?sensorLabel .
  
  # Dereference result
  ?result qudt:numericValue ?value .
  
  # Additional assertions
  FILTER(?value >= 0 && ?value <= 100)
}
```

### Implementing Custom Dereferencing

You can implement dereferencing in Jupyter notebooks:

```python
from kgap_tools import GDB
import pandas as pd

def dereference_uri(uri: str, properties: list) -> dict:
    """
    Dereference a URI to get specified properties.
    
    Args:
        uri: The URI to dereference
        properties: List of properties to retrieve
        
    Returns:
        Dictionary of property values
    """
    # Build property paths
    prop_patterns = []
    for i, prop in enumerate(properties):
        prop_patterns.append(f"OPTIONAL {{ <{uri}> <{prop}> ?prop{i} . }}")
    
    query = f"""
    SELECT *
    WHERE {{
        {' '.join(prop_patterns)}
    }}
    """
    
    result = GDB.query(query)
    df = result.to_dataframe()
    
    return {
        prop: df[f'prop{i}'][0] if len(df) > 0 else None
        for i, prop in enumerate(properties)
    }

# Usage
sensor_info = dereference_uri(
    'http://example.org/sensor/123',
    [
        'http://www.w3.org/2000/01/rdf-schema#label',
        'http://www.w3.org/ns/sosa/isHostedBy'
    ]
)
print(sensor_info)
```

### Recursive Dereferencing

For more complex scenarios, implement recursive dereferencing:

```python
def recursive_dereference(uri: str, depth: int = 2, visited: set = None) -> dict:
    """
    Recursively dereference a URI to a specified depth.
    
    Args:
        uri: The URI to dereference
        depth: How many levels deep to dereference
        visited: Set of already visited URIs (prevents cycles)
        
    Returns:
        Nested dictionary of dereferenced data
    """
    if visited is None:
        visited = set()
    
    if depth <= 0 or uri in visited:
        return {'@id': uri}
    
    visited.add(uri)
    
    # Get all properties of this URI
    query = f"""
    SELECT ?p ?o
    WHERE {{
        <{uri}> ?p ?o .
    }}
    """
    
    result = GDB.query(query)
    df = result.to_dataframe()
    
    data = {'@id': uri}
    
    for _, row in df.iterrows():
        prop = row['p']
        obj = row['o']
        
        # If object is a URI, recursively dereference
        if obj.startswith('http://') or obj.startswith('https://'):
            obj_data = recursive_dereference(obj, depth - 1, visited)
        else:
            obj_data = obj
        
        # Group multiple values for same property
        if prop in data:
            if not isinstance(data[prop], list):
                data[prop] = [data[prop]]
            data[prop].append(obj_data)
        else:
            data[prop] = obj_data
    
    return data

# Usage
observation_data = recursive_dereference(
    'http://example.org/observation/456',
    depth=2
)
print(observation_data)
```

## Custom SPARQL Query Templates

### Template Structure

Store reusable SPARQL queries as templates in `notebooks/queries/`:

**File: `notebooks/queries/get_observations.sparql`**
```sparql
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX qudt: <http://qudt.org/schema/qudt/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?observation ?sensor ?result ?time
WHERE {
  ?observation a sosa:Observation ;
               sosa:madeBySensor ?sensor ;
               sosa:hasResult ?result ;
               sosa:resultTime ?time .
  
  # Optional filters based on parameters
  ${filter_sensor}
  ${filter_timerange}
  ${filter_value}
}
ORDER BY DESC(?time)
LIMIT ${limit}
```

### Using Templates

```python
from kgap_tools import execute_to_df

# Basic usage
df = execute_to_df('get_observations', limit=100)

# With sensor filter
df = execute_to_df(
    'get_observations',
    filter_sensor='FILTER(?sensor = <http://example.org/sensor/123>)',
    filter_timerange='',
    filter_value='',
    limit=100
)

# With time range
df = execute_to_df(
    'get_observations',
    filter_sensor='',
    filter_timerange='FILTER(?time >= "2025-01-01T00:00:00"^^xsd:dateTime)',
    filter_value='',
    limit=100
)
```

## Data Validation Patterns

### Pattern 1: Completeness Checks

```sparql
# Find entities missing required properties
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>

SELECT ?observation ?missingProperty
WHERE {
  ?observation a sosa:Observation .
  
  # Check for missing label
  OPTIONAL { ?observation rdfs:label ?label . }
  BIND(IF(!BOUND(?label), "rdfs:label", "") AS ?missing1)
  
  # Check for missing sensor
  OPTIONAL { ?observation sosa:madeBySensor ?sensor . }
  BIND(IF(!BOUND(?sensor), "sosa:madeBySensor", "") AS ?missing2)
  
  # Check for missing result
  OPTIONAL { ?observation sosa:hasResult ?result . }
  BIND(IF(!BOUND(?result), "sosa:hasResult", "") AS ?missing3)
  
  # Combine missing properties
  BIND(CONCAT(?missing1, " ", ?missing2, " ", ?missing3) AS ?missingProperty)
  
  # Filter to only those with missing properties
  FILTER(?missingProperty != "  ")
}
```

### Pattern 2: Type Consistency

```sparql
# Find type inconsistencies
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>

SELECT ?entity ?types
WHERE {
  ?entity a sosa:Observation .
  
  # Get all types
  ?entity rdf:type ?type .
  
  # Check for conflicting types
  FILTER(?type != sosa:Observation)
}
GROUP BY ?entity
HAVING (COUNT(?type) > 1)
```

### Pattern 3: Value Range Validation

```sparql
# Find values outside expected range
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX qudt: <http://qudt.org/schema/qudt/>

SELECT ?observation ?value ?unit
WHERE {
  ?observation a sosa:Observation ;
               sosa:hasResult ?result .
  
  ?result qudt:numericValue ?value ;
          qudt:unit ?unit .
  
  # Define acceptable range
  FILTER(?value < 0 || ?value > 100)
}
```

## Performance Optimization

### Indexed Queries

Leverage GraphDB indexes for better performance:

```sparql
# Good: Uses predicate list
SELECT ?s ?o
WHERE {
  ?s <http://www.w3.org/2000/01/rdf-schema#label> ?o .
}

# Bad: Scans all predicates
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
  FILTER(?p = <http://www.w3.org/2000/01/rdf-schema#label>)
}
```

### Limit Early

```sparql
# Good: Limit before processing
SELECT ?observation (COUNT(?property) AS ?propCount)
WHERE {
  {
    SELECT ?observation
    WHERE {
      ?observation a sosa:Observation .
    }
    LIMIT 1000
  }
  ?observation ?property ?value .
}
GROUP BY ?observation

# Bad: Limit after processing
SELECT ?observation (COUNT(?property) AS ?propCount)
WHERE {
  ?observation a sosa:Observation .
  ?observation ?property ?value .
}
GROUP BY ?observation
LIMIT 1000
```

## Multi-Repository Setup

### Running Multiple GraphDB Repositories

Modify `docker-compose.yml` to run multiple repositories:

```yaml
services:
  graphdb-prod:
    build:
      context: ./graphdb
    environment:
      - GDB_REPO=production
      - REPOLABEL=Production Repository
    ports:
      - "7200:7200"
  
  graphdb-staging:
    build:
      context: ./graphdb
    environment:
      - GDB_REPO=staging
      - REPOLABEL=Staging Repository
    ports:
      - "7201:7200"
```

### Querying Multiple Repositories

```python
from kgap_tools import ExternalEndPoint
from pykg2tbl import KGSource

# Connect to different repositories
prod = KGSource.build("http://localhost:7200/repositories/production")
staging = KGSource.build("http://localhost:7201/repositories/staging")

# Query both
prod_results = prod.query("SELECT * WHERE { ?s ?p ?o } LIMIT 10")
staging_results = staging.query("SELECT * WHERE { ?s ?p ?o } LIMIT 10")
```

## Related Documentation

- [Main Documentation](./index.md)
- [Sembench Component](./components/sembench.md)
- [py-sema Documentation](https://github.com/vliz-be-opsci/py-sema)
