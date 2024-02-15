# test file to test the JRDF builder and all the templates

from pyrdfj2 import J2RDFSyntaxBuilder
from lwua.helpers import resolve_path
import os
from .graphdb import URN_BASE


def get_j2rdf_builder():
    template_folder = os.path.join(
        os.path.dirname(__file__),
        "../lwua/templates")
    # init J2RDFSyntaxBuilder
    context = f"{URN_BASE}:ADMIN"
    j2rdf = J2RDFSyntaxBuilder(
        templates_folder=template_folder,
        extra_functions={"registry_of_lastmod_context": context},
    )
    return j2rdf


J2RDF = get_j2rdf_builder()


def test_template_insert_graph():
    # Arrange
    template = "insert_graph.sparql"
    vars = {
        "context": "urn:lwua:INGEST:test_file.txt",
        "raw_triples": "<http://example.com/subject> <http://example.com/predicate> <http://example.com/object> .",
    }

    # Act
    query = J2RDF.build_syntax(template, **vars)

    # clean up the query by removing the newlines
    query = query.replace("\n", "")

    print(query)
    to_expect = "INSERT DATA { GRAPH <urn:lwua:INGEST:test_file.txt> { <http://example.com/subject> <http://example.com/predicate> <http://example.com/object> . } }"
    # Assert
    assert query == to_expect, f"Expected '{to_expect}', but got '{query}'"


def test_template_delete_graph():
    # Arrange
    template = "delete_graph.sparql"
    vars = {
        "context": "urn:lwua:INGEST:test_file.txt",
    }

    # Act
    query = J2RDF.build_syntax(template, **vars)

    # clean up the query by removing the newlines
    query = query.replace("\n", "")

    print(query)
    to_expect = "DELETE WHERE { GRAPH <urn:lwua:INGEST:test_file.txt> { ?s ?p ?o }}"
    # Assert
    assert query == to_expect, f"Expected '{to_expect}', but got '{query}'"


def test_template_update_context_lastmod():
    # Arrange
    template = "update_context_lastmod.sparql"
    vars = {
        "context": "urn:lwua:INGEST:test_file.txt",
        "lastmod": "2022-01-01T00:00:00",
    }

    # Act
    query = J2RDF.build_syntax(template, **vars)

    # clean up the query by removing the newlines
    query = query.replace("\n", "")
    # replace all spaces with nothing
    query = query.replace(" ", "")

    to_expect = 'PREFIX schema: <https://schema.org/>DELETE {    GRAPH <urn:lwua:INGEST:ADMIN> {    <urn:lwua:INGEST:test_file.txt> schema:dateModified ?date .    }}INSERT {        GRAPH <urn:lwua:INGEST:ADMIN> {        <urn:lwua:INGEST:test_file.txt> schema:dateModified "2022-01-01T00:00:00"^^xsd:dateTime .    }    }WHERE {    OPTIONAL {    GRAPH <urn:lwua:INGEST:ADMIN> {        <urn:lwua:INGEST:test_file.txt> schema:dateModified ?date .    }    }}'
    # replace all spaces with nothing
    to_expect = to_expect.replace(" ", "")
    # Assert
    assert query == to_expect, f"Expected '{to_expect}', but got '{query}'"


def test_template_lastmod_info():
    # Arrange
    template = "lastmod_info.sparql"
    vars = {
        "context": "urn:lwua:INGEST:test_file.txt",
    }

    # Act
    query = J2RDF.build_syntax(template, **vars)

    # clean up the query by removing the newlines
    query = query.replace("\n", "")
    # replace all spaces with nothing
    query = query.replace(" ", "")

    to_expect = "SELECT ?graph ?lastmod WHERE {    GRAPH <urn:lwua:INGEST:ADMIN> { ?graph <https://schema.org/dateModified> ?lastmod }}"
    # replace all spaces with nothing
    to_expect = to_expect.replace(" ", "")
    # Assert
    assert query == to_expect, f"Expected '{to_expect}', but got '{query}'"
