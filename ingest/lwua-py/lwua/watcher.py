import time
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from abc import ABC, abstractmethod
import logging
from lwua.helpers import enable_logging, resolve_path

log = logging.getLogger(__name__)


class FolderChangeObserver(ABC):
    @abstractmethod
    def added(self, fname: str, lastmod: datetime = None):
        pass

    @abstractmethod
    def removed(self, fname: str):
        pass

    @abstractmethod
    def changed(self, fname: str, lastmod: datetime = None):
        pass


class FolderChangeDetector:
    def __init__(self, folder_to_inspect):
        self.root = Path(folder_to_inspect)
        while not self.root.exists():
            log.info(f"Waiting for {self.root} to exist")
            time.sleep(1)
        log.info(f"Watching {self.root}")

    def report_changes(self, observer, known_lastmod_by_fname: dict = {}):
        current_lastmod_by_fname = {
            str(p): datetime.utcfromtimestamp(p.stat().st_mtime)
            for p in self.root.glob("**/*")
            if p.is_file() and p.suffix in [".ttl", ".jsonld"]
        }
        log.info(f"current_lastmod_by_fname: {current_lastmod_by_fname}")
        for fname in known_lastmod_by_fname:
            if fname not in current_lastmod_by_fname:
                observer.removed(fname)
        for fname, lastmod in current_lastmod_by_fname.items():
            if fname not in known_lastmod_by_fname:
                log.info(f"new file {fname} with lastmod {lastmod}")
                observer.added(fname, lastmod)
            elif lastmod > known_lastmod_by_fname[fname]:
                observer.changed(fname, lastmod)

        return current_lastmod_by_fname


# test the watcher on local file system - not in docker
if __name__ == "__main__":
    load_dotenv()
    enable_logging()
    path_to_watch = resolve_path(
        os.getenv("GDB_DATA_FOLDER", "/root/graphdb-import/data"), "dotenv"
    ).absolute()
    log.info(f"env pointing to { path_to_watch }")
    w = Watcher(path_to_watch)
    w.run()
