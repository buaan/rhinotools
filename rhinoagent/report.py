"""Measure / extract scene information as JSON so an agent can read it back."""
from __future__ import division

import json
import rhinoscriptsyntax as rs

from . import logic


def _r(v, n=4):
    return round(v, n)


def describe(obj):
    d = {"id": str(obj), "layer": rs.ObjectLayer(obj), "type": rs.ObjectType(obj),
         "name": rs.ObjectName(obj), "groups": rs.ObjectGroups(obj) or []}
    bb = rs.BoundingBox(obj)
    if bb:
        lo, hi = logic.xyz(bb[0]), logic.xyz(bb[6])
        d["bbox_min"] = [_r(c) for c in lo]
        d["bbox_max"] = [_r(c) for c in hi]
        d["size"] = [_r(hi[i] - lo[i]) for i in range(3)]
    if rs.IsCurve(obj):
        d["length"] = _r(rs.CurveLength(obj))
        d["closed"] = bool(rs.IsCurveClosed(obj))
        d["planar"] = bool(rs.IsCurvePlanar(obj))
        if d["closed"] and d["planar"]:
            a = rs.CurveArea(obj)
            d["area"] = _r(a[0]) if a else None
        if rs.IsCircle(obj):
            d["radius"] = _r(rs.CircleRadius(obj))
            d["center"] = [_r(c) for c in logic.xyz(rs.CircleCenterPoint(obj))]
        if rs.IsPolyline(obj):
            d["vertices"] = len(rs.PolylineVertices(obj) or [])
    elif rs.IsSurface(obj) or rs.IsPolysurface(obj):
        d["closed_solid"] = bool(rs.IsPolysurfaceClosed(obj)) if rs.IsPolysurface(obj) else False
        a = rs.SurfaceArea(obj)
        d["area"] = _r(a[0]) if a else None
        if d["closed_solid"]:
            v = rs.SurfaceVolume(obj)
            d["volume"] = _r(v[0]) if v else None
    return d


def scene_report(ids=None, details=True):
    ids = ids or rs.AllObjects() or []
    counts, layers = {}, {}
    for i in ids:
        counts[rs.ObjectType(i)] = counts.get(rs.ObjectType(i), 0) + 1
        layers[rs.ObjectLayer(i)] = layers.get(rs.ObjectLayer(i), 0) + 1
    rep = {"units": rs.UnitSystemName(abbreviate=True),
           "tolerance": rs.UnitAbsoluteTolerance(),
           "object_count": len(ids), "by_type_code": counts, "by_layer": layers}
    bb = rs.BoundingBox(ids) if ids else None
    if bb:
        rep["bbox_min"] = [_r(c) for c in logic.xyz(bb[0])]
        rep["bbox_max"] = [_r(c) for c in logic.xyz(bb[6])]
    if details:
        rep["objects"] = [describe(i) for i in ids]
    return rep


def print_report(ids=None, details=True):
    print(json.dumps(scene_report(ids, details), indent=1))
