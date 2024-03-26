#!/usr/bin/env python
import os
from pathlib import Path
from pysembench.core import Sembench

sb = Sembench(
    input_data_location=os.getenv("INPUT_DATA_LOCATION"),
    output_data_location=os.getenv("OUTPUT_DATA_LOCATION"),
    sembench_data_location=os.getenv("SEMBENCH_DATA_LOCATION"),
    sembench_config_path=os.getenv("SEMBENCH_CONFIG_PATH"),
    force=True,
    scheduler_interval_seconds=os.getenv("SCHEDULER_INTERVAL_SECONDS"),
)

sb.process()
