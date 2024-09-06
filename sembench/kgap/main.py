#!/usr/bin/env python
import os
from pathlib import Path
from sema.bench import Sembench
from sema.bench.core import locations_from_environ

sb = Sembench(
    locations=locations_from_environ(),
    sembench_config_path=os.getenv("SEMBENCH_CONFIG_PATH"),
    scheduler_interval_seconds=os.getenv("SCHEDULER_INTERVAL_SECONDS"),
)

sb.process()
