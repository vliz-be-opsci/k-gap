# SHACL Validation Quick Reference

This guide provides quick reference for using SHACL validation in K-GAP.

## What is SHACL?

SHACL (Shapes Constraint Language) is a W3C standard for validating RDF graphs. It allows you to:
- Define the expected structure of your RDF data
- Validate data against constraints
- Generate validation reports showing violations

## Quick Start

### 1. Add SHACL Shapes to Your Repository

First, create SHACL shapes that define constraints for your data:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix ex: <http://example.org/> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass foaf:Person ;
    sh:property [
        sh:path foaf:name ;
        sh:minCount 1 ;
    ] .
```

Import shapes into GraphDB via:
- Web interface: http://localhost:7200 → Import → RDF
- REST API: `curl -X POST http://localhost:7200/repositories/kgap/statements -H 'Content-Type: text/turtle' --data-binary '@shapes.ttl'`

### 2. Run Validation

#### Option A: Bash Script (Recommended for CLI)

```bash
# From host machine
./validate-shacl-host.sh

# From within container
docker exec test_kgap_graphdb /kgap/validate-shacl.sh
```

#### Option B: Python Module (Recommended for Jupyter/Scripts)

```python
from kgap_shacl import validate_repository

report = validate_repository()
if report.conforms:
    print("✓ Data is valid!")
else:
    print(f"✗ Found {len(report.violations)} violations")
```

#### Option C: REST API (Recommended for Automation)

```bash
curl -X POST \
  http://localhost:7200/repositories/kgap/shacl/validate \
  -H 'Accept: text/turtle'
```

## Common Use Cases

### Validate Specific Named Graph

**Bash:**
```bash
./validate-shacl-host.sh kgap http://example.org/my-graph
```

**Python:**
```python
report = validate_repository(named_graph="http://example.org/my-graph")
```

**REST API:**
```bash
curl -X POST \
  http://localhost:7200/repositories/kgap/shacl/validate \
  -H 'Accept: text/turtle' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'context=http://example.org/my-graph'
```

### Get Different Report Formats

**JSON-LD:**
```bash
curl -X POST \
  http://localhost:7200/repositories/kgap/shacl/validate \
  -H 'Accept: application/ld+json'
```

**Python:**
```python
report = validate_repository(accept_format='application/ld+json')
```

### Automated Validation in CI/CD

Add to your CI/CD pipeline:

```bash
#!/bin/bash
# Run SHACL validation and fail if violations found
./validate-shacl-host.sh || exit 1
```

### Scheduled Validation via Sembench

Add to your sembench configuration:

```python
from kgap_shacl import validate_repository
import logging

def validate_data():
    """Run SHACL validation as part of sembench processing."""
    logger = logging.getLogger(__name__)
    
    try:
        report = validate_repository()
        if not report.conforms:
            logger.warning(f"SHACL validation failed: {len(report.violations)} violations")
            # Log violations or send alert
        else:
            logger.info("SHACL validation passed")
    except Exception as e:
        logger.error(f"SHACL validation error: {e}")
```

## Understanding Validation Reports

### Report Structure

A SHACL validation report contains:

```turtle
[]
    a sh:ValidationReport ;
    sh:conforms false ;  # true if valid, false if violations found
    sh:result [
        a sh:ValidationResult ;
        sh:focusNode <http://example.org/person1> ;
        sh:resultPath <http://xmlns.com/foaf/0.1/name> ;
        sh:resultSeverity sh:Violation ;
        sh:resultMessage "MinCount constraint violation" ;
    ] .
```

### Severity Levels

- **sh:Violation** - Critical constraint violation
- **sh:Warning** - Non-critical issue
- **sh:Info** - Informational message

## Examples

K-GAP includes complete examples:

- **Example Shapes:** `docs/examples/shacl/person-shape.ttl`, `organization-shape.ttl`
- **Jupyter Notebook:** `docs/examples/shacl/shacl-validation-example.ipynb`
- **Documentation:** `docs/components/graphdb.md` (SHACL Validation section)

## Common SHACL Constraints

### Required Property
```turtle
sh:property [
    sh:path ex:name ;
    sh:minCount 1 ;
] .
```

### Datatype Constraint
```turtle
sh:property [
    sh:path ex:age ;
    sh:datatype xsd:integer ;
] .
```

### Value Range
```turtle
sh:property [
    sh:path ex:age ;
    sh:minInclusive 0 ;
    sh:maxInclusive 150 ;
] .
```

### Pattern Matching
```turtle
sh:property [
    sh:path ex:email ;
    sh:pattern "^.+@.+\\.+$" ;
] .
```

### Class Constraint
```turtle
sh:property [
    sh:path ex:knows ;
    sh:class foaf:Person ;
] .
```

## Troubleshooting

### Validation Endpoint Not Found (404)

Check that:
1. GraphDB is running: `docker ps | grep graphdb`
2. Repository exists: `curl http://localhost:7200/rest/repositories`
3. Repository name is correct in command/code

### No Violations Reported Despite Invalid Data

Ensure:
1. SHACL shapes are loaded in the repository
2. Shape targets match your data (check `sh:targetClass`, `sh:targetNode`, etc.)
3. Shapes are in the same repository as the data

### Python Module Import Error

From Jupyter notebook:
```python
import sys
sys.path.append('/workspace')
from kgap_shacl import validate_repository
```

### Container Not Found

Update container name in `validate-shacl-host.sh`:
```bash
# Check actual container name
docker ps --format '{{.Names}}' | grep graphdb

# Update CONTAINER_NAME variable if needed
```

## Resources

- [SHACL Specification](https://www.w3.org/TR/shacl/)
- [GraphDB SHACL Documentation](https://graphdb.ontotext.com/documentation/latest/shacl-validation.html)
- [SHACL Playground](https://shacl.org/playground/) - Test shapes online
- [K-GAP GraphDB Documentation](../components/graphdb.md)

## Integration with K-GAP Components

SHACL validation integrates seamlessly with all K-GAP components:

- **CI/CD Pipelines** - Use bash scripts with exit codes for automated quality gates
- **Sembench** - Schedule periodic validation using the Python module
- **Jupyter Notebooks** - Interactive data quality exploration and analysis
- **Custom Scripts** - Build automated monitoring and alerting workflows
- **GraphDB Workbench** - Manual validation and debugging via web interface

See the [Common Use Cases](#common-use-cases) section above for detailed examples.
