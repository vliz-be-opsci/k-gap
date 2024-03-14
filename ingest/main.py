#!/usr/bin/env python
import os
from pathlib import Path
from pysyncfstriples.service import SyncFsTriples

sft = SyncFsTriples(
    fpath=os.getenv("INPUT_DATA_LOCATION"),
    read_uri=os.getenv("READ_URI"),
    write_uri=os.getenv("WRITE_URI"),
)

sft.process()
