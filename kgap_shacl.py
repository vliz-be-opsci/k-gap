#!/usr/bin/env python3
"""
SHACL Validation Module for K-GAP

This module provides a Python interface to GraphDB's SHACL validation API,
making it easy to trigger validation and process validation reports from
Python code (e.g., Jupyter notebooks, Sembench scripts).

Example usage:
    from kgap_shacl import validate_repository, ValidationReport
    
    # Validate entire repository
    report = validate_repository()
    
    # Validate specific named graph
    report = validate_repository(named_graph="http://example.org/my-graph")
    
    # Check if validation passed
    if report.conforms:
        print("Data is valid!")
    else:
        print(f"Found {len(report.violations)} violations")
        for violation in report.violations:
            print(f"  - {violation}")
"""

import os
import sys
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
import requests


class ValidationViolation:
    """Represents a single SHACL validation violation."""
    
    def __init__(self, violation_data: Dict[str, Any]):
        self.data = violation_data
        self.focus_node = violation_data.get('focusNode', 'Unknown')
        self.result_path = violation_data.get('resultPath', 'Unknown')
        self.message = violation_data.get('message', 'No message')
        self.severity = violation_data.get('severity', 'Violation')
    
    def __str__(self):
        return f"{self.severity} at {self.focus_node}: {self.message}"
    
    def __repr__(self):
        return f"ValidationViolation(focus={self.focus_node}, path={self.result_path})"


class ValidationReport:
    """Represents a SHACL validation report."""
    
    def __init__(self, report_text: str, conforms: bool, format: str = "turtle"):
        self.report_text = report_text
        self.conforms = conforms
        self.format = format
        self.violations: List[ValidationViolation] = []
        
        # Parse violations from report (basic parsing for turtle format)
        if not conforms and "sh:ValidationResult" in report_text:
            # Simple heuristic: count ValidationResult occurrences
            # For more sophisticated parsing, consider using rdflib
            self.violations = self._parse_violations()
    
    def _parse_violations(self) -> List[ValidationViolation]:
        """Basic parsing of violations from Turtle format."""
        # This is a simplified parser - for production use, consider rdflib
        violations = []
        # Count occurrences of sh:ValidationResult as a simple metric
        count = self.report_text.count("sh:ValidationResult")
        for i in range(count):
            violations.append(ValidationViolation({
                'focusNode': 'See report',
                'resultPath': 'See report',
                'message': f'Violation #{i+1} - see full report for details',
                'severity': 'Violation'
            }))
        return violations
    
    def __str__(self):
        status = "VALID" if self.conforms else "INVALID"
        return f"ValidationReport(status={status}, violations={len(self.violations)})"
    
    def __repr__(self):
        return self.__str__()
    
    def print_report(self):
        """Print the full validation report."""
        print("=" * 60)
        print("SHACL Validation Report")
        print("=" * 60)
        if self.conforms:
            print("✓ Validation PASSED - No constraint violations found")
        else:
            print(f"✗ Validation FAILED - {len(self.violations)} violations found")
        print("=" * 60)
        print(self.report_text)
        print("=" * 60)


def validate_repository(
    repository: Optional[str] = None,
    named_graph: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    accept_format: str = "text/turtle"
) -> ValidationReport:
    """
    Trigger SHACL validation on a GraphDB repository.
    
    Args:
        repository: GraphDB repository name (default: from GDB_REPO env or 'kgap')
        named_graph: Optional named graph IRI to validate (default: validates all graphs)
        host: GraphDB host (default: from GDB_HOST env or 'localhost')
        port: GraphDB port (default: from GDB_PORT env or 7200)
        accept_format: RDF format for validation report (default: 'text/turtle')
                      Options: 'text/turtle', 'application/rdf+xml', 'application/ld+json'
    
    Returns:
        ValidationReport object containing validation results
    
    Raises:
        requests.RequestException: If the API request fails
        ValueError: If the repository doesn't exist
    
    Examples:
        >>> report = validate_repository()
        >>> if report.conforms:
        ...     print("Data is valid!")
        
        >>> report = validate_repository(named_graph="http://example.org/graph1")
        >>> report.print_report()
    """
    # Get configuration from environment or use defaults
    repository = repository or os.getenv('GDB_REPO', 'kgap')
    host = host or os.getenv('GDB_HOST', 'localhost')
    port = port or int(os.getenv('GDB_PORT', '7200'))
    
    # Build the validation endpoint URL
    base_url = f"http://{host}:{port}"
    validation_url = f"{base_url}/repositories/{repository}/shacl/validate"
    
    # Prepare request headers
    headers = {
        'Accept': accept_format
    }
    
    # Prepare request body if validating specific named graph
    data = None
    if named_graph:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        data = urlencode({'context': named_graph})
    
    try:
        # Make the validation request
        response = requests.post(
            validation_url,
            headers=headers,
            data=data,
            timeout=30
        )
        
        # Handle error responses
        if response.status_code == 404:
            raise ValueError(
                f"Repository '{repository}' not found. "
                f"Available repositories: {_get_repositories(base_url)}"
            )
        
        response.raise_for_status()
        
        # Parse the validation report
        report_text = response.text
        
        # Determine if validation passed
        # In SHACL, a report with sh:conforms true means validation passed
        # If there are sh:ValidationResult entries, validation failed
        conforms = "sh:ValidationResult" not in report_text
        
        return ValidationReport(report_text, conforms, accept_format)
        
    except requests.RequestException as e:
        raise requests.RequestException(
            f"Failed to validate repository '{repository}': {e}"
        ) from e


def _get_repositories(base_url: str) -> List[str]:
    """Get list of available repositories."""
    try:
        response = requests.get(f"{base_url}/rest/repositories", timeout=10)
        response.raise_for_status()
        # Parse repository IDs from response (simplified)
        repos = []
        for line in response.text.split('\n'):
            if '"id":' in line:
                repo_id = line.split('"id":"')[1].split('"')[0]
                repos.append(repo_id)
        return repos
    except Exception:
        return []


def main():
    """Command-line interface for SHACL validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Trigger SHACL validation on a GraphDB repository"
    )
    parser.add_argument(
        'repository',
        nargs='?',
        help='Repository name (default: from GDB_REPO env or "kgap")'
    )
    parser.add_argument(
        'named_graph',
        nargs='?',
        help='Named graph IRI to validate (default: all graphs)'
    )
    parser.add_argument(
        '--host',
        help='GraphDB host (default: from GDB_HOST env or "localhost")'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='GraphDB port (default: from GDB_PORT env or 7200)'
    )
    parser.add_argument(
        '--format',
        choices=['turtle', 'rdfxml', 'jsonld'],
        default='turtle',
        help='Output format for validation report (default: turtle)'
    )
    
    args = parser.parse_args()
    
    # Map format names to MIME types
    format_map = {
        'turtle': 'text/turtle',
        'rdfxml': 'application/rdf+xml',
        'jsonld': 'application/ld+json'
    }
    
    try:
        report = validate_repository(
            repository=args.repository,
            named_graph=args.named_graph,
            host=args.host,
            port=args.port,
            accept_format=format_map[args.format]
        )
        
        report.print_report()
        
        # Exit with appropriate code
        sys.exit(0 if report.conforms else 1)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
