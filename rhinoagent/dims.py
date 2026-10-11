"""Native Rhino dimensions - never lines + text.

Rules baked in:
  * real dimension objects (linear / aligned / radial) with one shared style
  * chained dimensions over unique coordinates, not one-per-segment
  * horizontal/vertical segments covered by chains; only slanted ones get
    aligned dims, de-duplicated by length
  * holes: one diameter/radius dim per unique size + centre positions in chain
  * everything of a part lands on layer 'Cotas' inside ONE group

Written for CPlane-parallel (XY) geometry.  For other planes, orient the
part to the World XY plane first (rs.OrientObject) or project to it.
"""
from __future__ import division

import rhinoscriptsyntax as rs

from . import logic

LAYER = "Cotas"
STYLE = "Agent"


def ensure_style(text_height, precision=2):
    """Create/refresh the shared dimension style and make it current."""
    if STYLE not in (rs.DimStyleNames() or []):
        rs.AddDimStyle(STYLE)
    rs.CurrentDimStyle(STYLE)
    for fn, val in (("DimStyleTextHeight", text_height),
                    ("DimStyleArrowSize", text_height),
                    ("DimStyleExtension", text_height * 0.5),
                    ("DimStyleOffset", text_height * 0.5),
                    ("DimStyleLengthResolution", precision)):
        try:
            getattr(rs, fn)(STYLE, val)
        except Exception:  # older Rhino: setter missing, keep default
            pass
    if not rs.IsLayer(LAYER):
        rs.AddLayer(LAYER, (0, 120, 200))


def _plane_h():
    return rs.WorldXYPlane()


def _plane_v():
    return rs.PlaneFromFrame((0, 0, 0), (0, 1, 0), (-1, 0, 0))


def _add(ids, new):
    if new:
        ids.append(new)


def _chain_h(xs, y, off, z, ids):
    """Chained horizontal dims along y-off, plus overall if >1 gap."""
    for a, b in logic.chain_pairs(xs):
        _add(ids, rs.AddLinearDimension(_plane_h(), (a, y, z), (b, y, z), ((a + b) / 2, y - off, z)))
    if len(xs) > 2:
        a, b = xs[0], xs[-1]
        _add(ids, rs.AddLinearDimension(_plane_h(), (a, y, z), (b, y, z), ((a + b) / 2, y - 2 * off, z)))


def _chain_v(ys, x, off, z, ids):
    for a, b in logic.chain_pairs(ys):
        _add(ids, rs.AddLinearDimension(_plane_v(), (x, a, z), (x, b, z), (x - off, (a + b) / 2, z)))
    if len(ys) > 2:
        a, b = ys[0], ys[-1]
        _add(ids, rs.AddLinearDimension(_plane_v(), (x, a, z), (x, b, z), (x - 2 * off, (a + b) / 2, z)))


def _radial(circle_id, ids, off):
    """Diameter dimension for a circle; falls back to a leader with text."""
    c = logic.xyz(rs.CircleCenterPoint(circle_id))
    r = rs.CircleRadius(circle_id)
    try:
        import Rhino
        import scriptcontext
        pt = Rhino.Geometry.Point3d(c[0] + r * 0.7071, c[1] + r * 0.7071, c[2])
        plane = rs.WorldXYPlane()
        dim = Rhino.Geometry.RadialDimension(Rhino.Geometry.Point3d(*c), pt, plane.XAxis, plane.Normal, off)
        dim.AnnotationType = Rhino.Geometry.AnnotationType.Diameter
        gid = scriptcontext.doc.Objects.AddRadialDimension(dim)
        if gid and str(gid) != '00000000-0000-0000-0000-000000000000':
            ids.append(gid)
            return
    except Exception:
        pass
    _add(ids, rs.AddLeader([(c[0] + r * 0.7071, c[1] + r * 0.7071, c[2]),
                            (c[0] + r + off, c[1] + r + off, c[2])],
                           text=u"Ø%.*f" % (2, 2 * r)))


def dimension_part(outline, holes=(), name=None, text_height=None):
    """Dimension one part (closed outline curve + inner curves).

    Returns the list of created dimension ids (also grouped as `name`).
    """
    bb = rs.BoundingBox(outline)
    x0, y0, z = logic.xyz(bb[0])
    x1, y1 = logic.xyz(bb[6])[:2]
    th = text_height or max(x1 - x0, y1 - y0) * 0.03
    off = th * 3
    ensure_style(th)
    prev_layer = rs.CurrentLayer()
    rs.CurrentLayer(LAYER)
    rs.EnableRedraw(False)
    ids = []
    try:
        pts = [logic.xyz(p) for p in (rs.PolylineVertices(outline) or [])] \
            if rs.IsPolyline(outline) else [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]

        circles = [h for h in holes if rs.IsCircle(h)]
        others = [h for h in holes if not rs.IsCircle(h)]
        centres = [logic.xyz(rs.CircleCenterPoint(c)) for c in circles]
        for h in others:
            hb = rs.BoundingBox(h)
            centres.append(((hb[0][0] + hb[6][0]) / 2, (hb[0][1] + hb[6][1]) / 2, z))

        plan = logic.plan_polyline_dims(pts, centres)
        _chain_h(plan['xs'], y0, off, z, ids)
        _chain_v(plan['ys'], x0, off, z, ids)

        for p, q in plan['slanted']:
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            nx, ny = -(q[1] - p[1]), (q[0] - p[0])      # push away from centre
            if nx * (mx - cx) + ny * (my - cy) < 0:
                nx, ny = -nx, -ny
            n = (nx * nx + ny * ny) ** 0.5
            _add(ids, rs.AddAlignedDimension(p, q, (mx + nx / n * off, my + ny / n * off, z)))

        seen = set()                                    # one dim per unique diameter
        for c in circles:
            key = round(rs.CircleRadius(c), 4)
            if key not in seen:
                seen.add(key)
                _radial(c, ids, off)
        if ids:
            rs.AddObjectsToGroup(ids, rs.AddGroup(name))
    finally:
        rs.CurrentLayer(prev_layer)
        rs.EnableRedraw(True)
    return ids


def dimension_all(curve_ids, name_prefix="cotas"):
    """Dimension every part found among curve_ids (outline + nested holes)."""
    closed = [c for c in curve_ids if rs.IsCurveClosed(c)]
    boxes = [logic.box_of(rs.BoundingBox(c)) for c in closed]
    parents = logic.nest_by_containment(boxes)
    out = {}
    n = 0
    for i, c in enumerate(closed):
        if parents[i] is not None:
            continue
        n += 1
        holes = [closed[j] for j in range(len(closed)) if parents[j] == i]
        name = "%s_%02d" % (name_prefix, n)
        out[name] = dimension_part(c, holes, name)
    return out
