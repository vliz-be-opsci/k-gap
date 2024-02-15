import pytest
from datetime import datetime
from pathlib import Path
from lwua.graphdb import (
    context_2_fname,
    suffix_2_format,
    read_graph,
    convert_results_registry_of_lastmod,
)
from lwua.ingest import data_path_from_config
import os

results = {
    "head": {"vars": ["graph", "lastmod"]},
    "results": {
        "bindings": [
            {
                "graph": {"value": "urn:lwua:INGEST:test_file.txt"},
                "lastmod": {"value": "2022-01-01T00:00:00"},
            }
        ]
    },
}


def test_context_2_fname():
    # Act
    converted = context_2_fname("urn:lwua:INGEST:test_file.txt")

    # Assert
    assert isinstance(converted, Path)


def get_registry_of_lastmod(results):
    # Act
    converted = convert_results_registry_of_lastmod(results)
    test_path = Path("test_file.txt")
    test_date = datetime.fromisoformat("2022-01-01T00:00:00")

    # Assert
    assert isinstance(converted, dict)
    assert len(converted) == 1
    assert converted[test_path] == test_date


def test_suffix_2_format():
    # Arrange
    suffixes = ["ttl", "turtle", "jsonld", "json", "other"]

    # Act
    results = [suffix_2_format(suffix) for suffix in suffixes]

    # Assert
    assert results == ["turtle", "turtle", "json-ld", "json-ld", None]


def test_read_graph():
    # Arrange
    test_file_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "test.ttl"
    )

    fpath = os.path.join(
        os.path.dirname(
            os.path.realpath(__file__)),
        "test.ttl")
    format = "turtle"

    # Act
    graph = read_graph(fpath, format)

    # Assert
    assert graph is not None
    # Add more assertions based on what the read_graph function is supposed to
    # do
