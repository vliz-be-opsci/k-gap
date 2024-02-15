# test file for the ingest.py file in the lwua-py folder
import pytest
import os
from lwua.ingest import fname_2_context, data_path_from_config


def test_fname_2_context():
    # Arrange
    fname = "test_file.txt"  # replace with a test file name

    # Act
    # Call the function with the test parameters
    result = fname_2_context(fname)

    # Assert
    # Check the results
    # This depends on what the function does
    # For example, if the function returns a string based on the file name,
    # you can check if the string is correct
    assert (
        result == "urn:lwua:INGEST:test_file.txt"
    ), f"Expected 'expected_result', but got '{result}'"
