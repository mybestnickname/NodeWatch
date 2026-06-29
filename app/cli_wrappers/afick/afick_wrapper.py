import enum
import logging
import re
import struct
import time
from datetime import datetime
from typing import Any

from app.utils import run_cmd

logger = logging.getLogger("afick")

INT_TYPES = {"inode", "links", "acl", "gid", "filesize", "blocs"}


class Result(enum.IntEnum):
    afick_success = 0
    service_started = 1
    afick_error = 2
    service_error = 3
    no_cache_dir = 4
    save_cache_error = 5
    access_save_cache_error = 6
    no_cache_file = 7
    access_load_cache_error = 8
    another_error = 9

    def __str__(self):
        return self.name


class ReqType(str, enum.Enum):
    get = "-g"
    next = "-n"
    set = "-s"
    test = "-t"


class AfickWrapper:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def get_datetime(self, datetime_str="") -> int:
        dt = datetime.strptime(datetime_str, "%c") if datetime_str else datetime.now()
        return int(dt.timestamp())

    def dateandtime(self, datetime_str="") -> str:
        dt = datetime.strptime(datetime_str, "%c") if datetime_str else datetime.now()
        offset = time.timezone if time.localtime().tm_isdst == 0 else time.altzone
        tz = -offset // 3600
        sign_tz = b'-' if tz < 0 else b'+'
        tz_h, tz_m = divmod(abs(tz), 1)
        deci_sec = dt.microsecond // 100000
        data = struct.pack(
            '>HBBBBBBcBB',
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
            deci_sec, sign_tz,
            int(tz_h), int(tz_m * 10)
        )
        return " ".join(f"{x:02X}" for x in data)

    def parse_info(self, info: str) -> dict[str, list[str | int]]:
        field, param = info.split(":", 1)
        field = field.strip()
        values = [p.strip() for p in param.split("\t")]
        parsed: list[str | int] = []

        for p in values:
            value: str | int = p
            if "time" in field or "date" in field:
                value = self.get_datetime(p)
            elif field in INT_TYPES or "number" in field:
                value = int(p)
            parsed.append(value)

        return {field: parsed}

    def parse_afick_output(self, afick_output: str) -> dict[str, Any]:
        snmp_data: dict[str, Any] = {
            "status": int(Result.afick_success),
            "time": "",
            "status_str": str(Result.afick_success),
            "count": 0,
        }
        detailed_pos = afick_output.find("# detailed changes")
        if detailed_pos == -1:
            logger.warning("No detailed changes section found in afick output.")
            return snmp_data

        detailed = afick_output[detailed_pos:]
        lines = detailed.splitlines()
        changes_regex = re.compile(r'^(\w+)\s+(\w+)\s+:\s+(.*)$')

        idx = 0
        for i, line in enumerate(lines):
            match = changes_regex.match(line)
            if not match:
                continue

            status, ftype, path = match.groups()
            changes = []

            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if not next_line.startswith((' ', '\t')):
                    break
                changes.append(self.parse_info(next_line))

            idx += 1
            entry = {path: {"type": ftype, "changes": changes}}
            snmp_data.setdefault(status, []).append(entry)

        snmp_data["count"] = idx
        return snmp_data

    def compare(self) -> dict[str, Any]:
        code, out, err = run_cmd(["sudo", "afick", "--compare"], self.timeout)
        if code != 0:
            logger.error(f"afick exited with code {code}: {err}")
        return self.parse_afick_output(out)
