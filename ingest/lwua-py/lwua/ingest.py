import logging
import time
from dotenv import load_dotenv
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
import os
from pathlib import Path
from .helpers import enable_logging, resolve_path
from .watcher import FolderChangeObserver, FolderChangeDetector
from .graphdb import (
    get_registry_of_lastmod,
    delete_graph,
    ingest_graph,
    update_registry_lastmod,
    read_graph,
    fname_2_context,
)


log = logging.getLogger(__name__)


# functions here to ingest and delete files


def delete_data_file(fname):
    context = fname_2_context(fname)
    log.info(f"deleting {fname} from {context}")
    delete_graph(context)
    update_registry_lastmod(context, None)


def ingest_data_file(fname: str, lastmod: datetime, replace: bool = True):
    """
    Ingest a data file.

    :param fname: The name of the file to ingest.
    :type fname: str
    :param replace: Whether to replace the existing data. Defaults to True.
    :type replace: bool
    :raises AssertionError: If the file does not exist.
    """
    file_path = data_path_from_config() / fname
    assert file_path.exists(), f"cannot ingest file at {file_path}"
    graph = read_graph(file_path)
    context = fname_2_context(fname)
    log.info(f"ingesting {file_path} into {context} | replace : {replace}")
    ingest_graph(graph, lastmod, context=context, replace=replace)


def data_path_from_config():
    local_default = str(resolve_path("./data", versus="dotenv"))
    folder_name = os.getenv("INGEST_DATA_FOLDER", local_default)
    return Path(folder_name).absolute()


class Ingester:
    def __init__(self):
        data_path = data_path_from_config()
        log.info(f"run_ingest on updated files in {data_path}")

        # get the last context graph modification dates
        # run while true loop with 5 second sleep
        self.detector = FolderChangeDetector(data_path)
        self.ingestor = IngestChangeObserver()

    def run_ingest(self):
        last_mod = {}
        try:
            last_mod = get_registry_of_lastmod()
            log.info(f"initial last mod == {last_mod}")
            log.info("reporting changes")
            self.detector.report_changes(self.ingestor, last_mod)
            log.info(f"last_mod == {last_mod}")
        except Exception as e:
            log.exception(e)


class IngestChangeObserver(FolderChangeObserver):
    def __init__(self):
        pass

    def removed(self, fname):
        # Implement the deletion of graph context and update of lastmod
        # registry
        log.info(f"File {fname} has been deleted")
        delete_data_file(fname)

    def added(self, fname, lastmod):
        # Implement the addition of graph in context
        log.info(f"File {fname} has been added")
        ingest_data_file(fname, lastmod)

    def changed(self, fname, lastmod):
        # Implement the replacement of graph in context and update the lastmod
        # registry
        log.info(f"File {fname} has been modified")
        ingest_data_file(fname, lastmod, True)


# Note: this main method allows to locally test outside docker
# directly connecting to a localhost graphdb endpoint (which might be
# inside docker itself)


def main():
    load_dotenv()
    enable_logging()


if __name__ == "__main__":
    main()
