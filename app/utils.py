import logging
import os
import subprocess
from typing import Tuple

logger = logging.getLogger(__name__)


def run_cmd(cmd_line: list, timeout: int = 0, report_err=True) -> Tuple[int, str, str]:
    try:
        proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    except OSError as exc:
        logger.error(exc)
        return os.EX_SOFTWARE, '', ''
    try:
        output, error = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, error = proc.communicate()
    code = proc.returncode
    output = output.decode(errors='surrogateescape').strip()
    error = error.decode(errors='surrogateescape').strip()
    if code == os.EX_OK or not report_err:
        if output:
            logger.debug(f"stdout: {output}")
        if error:
            logger.debug(f"stderr: {error}")
    else:
        logger.error(f"command: {cmd_line} , exit_code: {code}")
        if output:
            logger.error(f"stdout: {output}")
        if error:
            logger.error(f"stderr: {error}")
    return code, output, error
