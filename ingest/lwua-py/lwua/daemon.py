""" Deamon wrapper script
--> https://stackoverflow.com/questions/1603109/how-to-make-a-python-script-run-like-a-service-or-daemon-in-linux
--> https://web.archive.org/web/20160320091458/http://www.jejik.com/files/examples/daemon3x.py
"""

import sys
import os
import time
import atexit
import signal
from abc import ABC, abstractmethod
import logging


log = logging.getLogger(__name__)


class Daemon(ABC):
    """A generic daemon class.
    Usage: subclass the daemon class and override the run() method.
    """

    def __init__(self, pidfile):
        self.pidfile = str(pidfile)

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""

        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as err:
            log.exception(f"fork #1 failed: {err}")
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as err:
            log.exception(f"fork #2 failed: {err}")
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, "r")
        so = open(os.devnull, "a+")
        se = open(os.devnull, "a+")

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)

        pid = str(os.getpid())
        log.info(f"creating pidfile {self.pidfile} - containing {pid}")
        with open(self.pidfile, "w+") as f:
            f.write(pid + "\n")

    def delpid(self):
        log.info("atexit -- service run completed -- removing pidfile")
        os.remove(self.pidfile)

    def start(self):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile, "r") as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            message = f"pidfile {self.pidfile} already exist. Daemon already running?\n"
            sys.stderr.write(message)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pidfile, "r") as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            message = f"pidfile {self.pidfile} does not exist. Daemon not running?\n"
            sys.stderr.write(message)
            return  # not an error in a restart

        # Try killing the daemon process

        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print(str(err.args))
                sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    @abstractmethod
    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart().
        """

    CMDS = ["start", "stop", "restart", "run"]

    def _usage(self):
        print(
            f"run this daemon script with one argument == {'|'.join(Daemon.CMDS)}")

    def _cmd(self, argv):
        if len(argv) != 2:
            log.warning(f"daemon started with cmdline ==> {argv}")
            return self._usage()
        # else
        cmd = argv[1]
        if cmd not in Daemon.CMDS:
            return self._usage()
        # else
        self.__getattribute__(cmd)()
