"""Pure-Python geometry decisions (no Rhino imports, so testable anywhere).

Points are (x, y, z) tuples.  Boxes are (xmin, ymin, xmax, ymax).
"""


def unique_sorted(values, tol=1e-6):
    """Sorted values with near-duplicates (within tol) collapsed."""
    out = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def chain_pairs(values):
    """[a, b, c] -> [(a, b), (b, c)]: one chained dimension per gap."""
    return [(values[i], values[i + 1]) for i in range(len(values) - 1)]


def box_of(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def box_contains(outer, inner, tol=1e-6):
    return (outer[0] - tol <= inner[0] and outer[1] - tol <= inner[1] and
            outer[2] + tol >= inner[2] and outer[3] + tol >= inner[3])


def _area(b):
    return (b[2] - b[0]) * (b[3] - b[1])


def nest_by_containment(boxes, tol=1e-6):
    """For each box, index of the smallest *other* box containing it (or None).

    Used to find which closed curves are holes of which outline, so a part
    (outline + holes) can be grouped and dimensioned as one unit.
    """
    parents = []
    for i, b in enumerate(boxes):
        best = None
        for j, o in enumerate(boxes):
            if i == j or not box_contains(o, b, tol):
                continue
            # identical boxes: lower index wins as parent to avoid cycles
            if abs(_area(o) - _area(b)) <= tol and j > i:
                continue
            if best is None or _area(o) < _area(boxes[best]):
                best = j
        parents.append(best)
    return parents


def classify_segment(p, q, tol=1e-6):
    """'H' (parallel to X), 'V' (parallel to Y) or 'S' (slanted) in XY."""
    dx, dy = abs(q[0] - p[0]), abs(q[1] - p[1])
    if dy <= tol:
        return 'H'
    if dx <= tol:
        return 'V'
    return 'S'


def plan_polyline_dims(points, hole_centers=(), tol=1e-6):
    """Decide which dimensions a polyline outline needs.

    Instead of one dimension per segment (the "loose lines" look), return:
      xs / ys  - unique coordinates of vertices (+ hole centres) to chain
                 along the bottom / left edge
      slanted  - de-duplicated slanted segments needing aligned dimensions
    Horizontal/vertical segments are fully described by the chains.
    """
    pts = list(points)
    xs = [p[0] for p in pts] + [c[0] for c in hole_centers]
    ys = [p[1] for p in pts] + [c[1] for c in hole_centers]
    slanted, seen = [], set()
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if classify_segment(p, q, tol) != 'S':
            continue
        length = round(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5, 4)
        if length in seen:  # same length already dimensioned
            continue
        seen.add(length)
        slanted.append((p, q))
    return {'xs': unique_sorted(xs, tol), 'ys': unique_sorted(ys, tol),
            'slanted': slanted}
