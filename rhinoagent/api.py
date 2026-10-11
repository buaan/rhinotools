"""One-line entry points for MCP `execute_code`.

Every function returns a JSON *string* so the call can be written as
    result = api.dimension()
(rhino-mcp only returns the `result` variable; `print` inside imported
modules is not captured).  Functions act on the current selection unless
told otherwise.
"""
import json
import sys

import rhinoscriptsyntax as rs

from . import dims, report, tidy


def _ids(ids=None):
    return list(ids or rs.SelectedObjects() or [])


def _out(data):
    return json.dumps(data)


def scene(details=False):
    """Units, tolerance, layers, counts, bbox of the whole document."""
    return _out(report.scene_report(details=details))


def measure(ids=None):
    """Per-object measurements (length, area, volume, bbox, radius...) of the selection."""
    return _out(report.scene_report(_ids(ids), details=True))


def audit(ids=None):
    """Problems worth fixing before dimensioning (loose lines, duplicates...)."""
    return _out(tidy.audit(_ids(ids) or None))


def join(ids=None):
    """Join selected loose lines/arcs/polylines into the fewest curves."""
    ids = _ids(ids)
    new = tidy.join_loose_curves(ids)
    return _out({"input": len(ids), "output": len(new), "ids": [str(i) for i in new]})


def group_parts(ids=None):
    """Group each closed outline with the closed curves inside it."""
    parts = tidy.group_parts(_ids(ids))
    return _out({k: len(v) for k, v in parts.items()})


def dimension(ids=None, join_first=True):
    """Join loose curves, then add native chained dimensions per part."""
    ids = [i for i in _ids(ids) if rs.IsCurve(i)]
    if join_first:
        ids = tidy.join_loose_curves(ids)
    made = dims.dimension_all(ids)
    return _out({k: len(v) for k, v in made.items()})


def forget():
    """Drop cached rhinoagent modules; re-import after editing the library."""
    for name in [m for m in sys.modules if m == "rhinoagent" or m.startswith("rhinoagent.")]:
        del sys.modules[name]
    return _out("rhinoagent unloaded; import it again")
