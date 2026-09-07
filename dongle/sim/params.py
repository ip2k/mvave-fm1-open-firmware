"""Read the dongle parameters from dongle/firmware/config.h so the simulator and
the firmware share one source of truth."""
import pathlib
import re

CONFIG_H = pathlib.Path(__file__).resolve().parents[1] / "firmware" / "config.h"


def load(path=CONFIG_H):
    text = path.read_text()
    values = {}
    for m in re.finditer(r"^#define\s+(\w+)\s+(.+?)(?://.*)?$", text, re.M):
        name, expr = m.group(1), m.group(2).strip()
        expr = re.sub(r"\b(\w+)\b", lambda k: str(values[k.group(1)]) if k.group(1) in values else k.group(1), expr)
        try:
            values[name] = int(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 - our own header
        except Exception:
            pass
    return values


PARAMS = load()
