"""Geometry hygiene: join loose lines into polylines, group parts, audit."""
import rhinoscriptsyntax as rs

from . import logic


def join_loose_curves(ids, tol=None):
    """Join lines/arcs/polylines end-to-end into the fewest curves.

    Returns the new curve ids (closed loops come back closed).  Native
    JoinCurves is used on purpose: it is exact and keeps layers/colours.
    """
    tol = tol or rs.UnitAbsoluteTolerance()
    ids = [i for i in ids if rs.IsCurve(i)]
    if len(ids) < 2:
        return ids
    return rs.JoinCurves(ids, delete_input=True, tolerance=tol) or ids


def group_parts(curve_ids, name_prefix="part"):
    """Group each outline with the closed curves inside it (its holes).

    Returns {group_name: [ids]}.  Only planar-in-XY nesting is considered.
    """
    closed = [c for c in curve_ids if rs.IsCurveClosed(c)]
    boxes = []
    for c in closed:
        bb = rs.BoundingBox(c)
        boxes.append(logic.box_of(bb))
    parents = logic.nest_by_containment(boxes)

    def root(i):
        while parents[i] is not None:
            i = parents[i]
        return i

    parts = {}
    for i, c in enumerate(closed):
        parts.setdefault(root(i), []).append(c)
    result = {}
    for n, key in enumerate(sorted(parts)):
        name = "%s_%02d" % (name_prefix, n + 1)
        rs.AddGroup(name)
        rs.AddObjectsToGroup(parts[key], name)
        result[name] = parts[key]
    return result


def audit(ids=None, short=None):
    """Return a list of human-readable problems worth fixing before dimensioning."""
    ids = ids or rs.AllObjects() or []
    tol = rs.UnitAbsoluteTolerance()
    short = short or tol * 10
    issues = []
    lines = [i for i in ids if rs.IsLine(i)]
    if len(lines) > 1:
        issues.append("%d loose lines: join them (tidy.join_loose_curves)" % len(lines))
    ungrouped = [i for i in ids if not rs.ObjectGroups(i)]
    if len(ungrouped) > 1:
        issues.append("%d objects not in any group" % len(ungrouped))
    on_default = [i for i in ids if rs.ObjectLayer(i) == "Default"]
    if on_default:
        issues.append("%d objects on layer 'Default'" % len(on_default))
    tiny = [i for i in ids if rs.IsCurve(i) and rs.CurveLength(i) < short]
    if tiny:
        issues.append("%d curves shorter than %g (likely junk)" % (len(tiny), short))
    seen, dups = set(), 0
    for i in ids:
        if rs.IsCurve(i):
            bb = rs.BoundingBox(i)
            key = (round(rs.CurveLength(i), 4),) + tuple(round(c, 3) for c in bb[0] + bb[6])
            dups += key in seen
            seen.add(key)
    if dups:
        issues.append("%d duplicate curves (rs.SelDup)" % dups)
    bad = [i for i in ids if rs.IsObjectValid(i) is False]
    if bad:
        issues.append("%d invalid objects (rs.Command('_Check'))" % len(bad))
    return issues
