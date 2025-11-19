"""
kiln_errors.py

Shared helper to follow systemd journal for the kiln-controller service
and call a callback for relevant error/warn lines.

This module is UI-agnostic: the callback can send Telegram messages,
update an LCD icon, write to a file, etc.
"""

import logging
import re
import subprocess
import time
from typing import Callable

import sidecar_config as cfg


log = logging.getLogger(__name__)


def watch_kiln_errors(callback: Callable[[str], None]):
    """
    Follow journalctl for the configured kiln systemd unit and call `callback(line)`
    for each line that matches the kiln log regex and contains WARN/ERROR.

    This function is blocking; run it in a separate thread in your sidecar.
    """
    filter_re = re.compile(cfg.KILN_JOURNAL_FILTER_REGEX)

    args = [
        "journalctl",
        "-u",
        cfg.JOURNAL_UNIT,
        "-f",         # follow (like tail -f)
        "-n", "0",    # do not show old lines
        "-o", "short" # compact output
    ]

    while True:
        try:
            log.info("kiln_errors: starting journalctl for unit %s", cfg.JOURNAL_UNIT)
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )

            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue

                # First filter: only lines that match the kiln log pattern
                if not filter_re.search(line):
                    continue

                # Second filter: only WARN/ERROR; INFO is handled via /status
                if "ERROR" in line or "WARN" in line:
                    try:
                        callback(line)
                    except Exception as cb_err:
                        log.error("kiln_errors: error in callback: %s", cb_err)

            ret = proc.wait()
            log.warning(
                "kiln_errors: journalctl exited with code %s; restarting in 5s.", ret
            )
            time.sleep(5.0)

        except FileNotFoundError:
            log.error("kiln_errors: journalctl not found. Error watching disabled.")
            return
        except Exception as e:
            log.error("kiln_errors: error in watch_kiln_errors: %s", e)
            time.sleep(5.0)
