import yaml
import logging
import logging.config
import os
from pathlib import Path
from dotenv import find_dotenv


log = logging.getLogger(__name__)


def yaml_load_file(file):
    if file is None:
        log.debug("can not load unspecified yaml file")
        return None
    # else
    try:
        with open(file, "r") as yml_file:
            return yaml.load(yml_file, Loader=yaml.SafeLoader)
    except Exception as e:
        log.exception(e)
        return dict()


def find_logconf(logconf):
    if logconf is None or logconf == "":
        return None
    for vs in ["dotenv", "module", "work"]:  # try in this order
        logconf_path = resolve_path(logconf, versus=vs)
        print(f"trying vs {vs} --> {logconf_path} ?")
        if logconf_path.exists():
            return logconf_path
    # else
    raise Exception(
        f"config error logconf file {logconf} not found relative to dotenv, module or pwd"
    )


def enable_logging(logconf: str = None):
    """Configures logging based on logconf specified through .env ${LOGCONF}"""
    logconf = os.getenv("LOGCONF") if logconf is None else logconf
    logconf_path = find_logconf(logconf)
    if logconf_path is None:
        log.info("No logging config found.")
        return
    # else
    logconf = str(logconf_path)
    logging.config.dictConfig(yaml_load_file(logconf))
    log.info(f"Logging enabled according to config in {logconf}")


def singleton(class_):
    """Decorator for singleton classes"""
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


LOCATIONS: dict[str, Path] = dict(
    work=Path().cwd(),
    helpers=Path(__file__).parent.absolute(),
    module=Path(__file__).parent.parent.absolute(),
    dotenv=Path(find_dotenv()).parent,
)


def resolve_path(location: str, versus: str = "module"):
    location = location if location else ""
    assert versus in LOCATIONS, f"no base path available for coded versus = '{versus}'"
    base: Path = LOCATIONS[versus]
    log.debug(f"resolve path base='{base}' + rel='{location}'")
    return Path(base, location).absolute()
