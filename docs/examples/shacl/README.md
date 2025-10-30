# Example SHACL Shapes for Data Validation

This directory contains example SHACL shapes files that can be used to validate RDF data in GraphDB.

## What is SHACL?

SHACL (Shapes Constraint Language) is a W3C standard for validating RDF graphs against a set of conditions. SHACL shapes define constraints that RDF data should conform to.

## Using SHACL with K-GAP

### 1. Define Your Shapes

Create a SHACL shapes file (e.g., `shapes.ttl`) that defines the constraints for your data model.

### 2. Import Shapes into GraphDB

Import your SHACL shapes file into GraphDB using one of these methods:

**Via Web Interface:**
1. Navigate to http://localhost:7200
2. Select your repository
3. Go to "Import" → "RDF"
4. Upload your shapes file

**Via REST API:**
```bash
curl -X POST \
  http://localhost:7200/repositories/kgap/statements \
  -H 'Content-Type: text/turtle' \
  --data-binary '@shapes.ttl'
```

**Via mounted volume:**
Place your shapes file in `./data/` and import from there.

### 3. Run Validation

Execute SHACL validation using the provided scripts:

```bash
# From the host
./validate-shacl-host.sh

# Or using docker exec
docker exec test_kgap_graphdb /kgap/validate-shacl.sh
```

## Example Shape Files

See the example files in this directory:
- `person-shape.ttl` - Example shape for validating Person entities
- `organization-shape.ttl` - Example shape for validating Organization entities

## Learn More

- [SHACL Specification](https://www.w3.org/TR/shacl/)
- [GraphDB SHACL Documentation](https://graphdb.ontotext.com/documentation/latest/shacl-validation.html)
- [SHACL Playground](https://shacl.org/playground/)
