import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def run_cmd(cmd_line: list[str], timeout: int = 0, report_err: bool = True) -> tuple[int, str, str]:
    try:
        proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    except OSError as exc:
        logger.error(exc)
        return os.EX_SOFTWARE, "", ""

    try:
        out_bytes, err_bytes = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out_bytes, err_bytes = proc.communicate()

    code = proc.returncode if proc.returncode is not None else os.EX_SOFTWARE
    output = out_bytes.decode(errors="surrogateescape").strip()
    error = err_bytes.decode(errors="surrogateescape").strip()

    if code == os.EX_OK or not report_err:
        if output:
            logger.debug("stdout: %s", output)
        if error:
            logger.debug("stderr: %s", error)
    else:
        logger.error("command: %s , exit_code: %s", cmd_line, code)
        if output:
            logger.error("stdout: %s", output)
        if error:
            logger.error("stderr: %s", error)

    return code, output, error
