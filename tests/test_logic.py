import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rhinoagent import logic  # noqa: E402


class LogicTests(unittest.TestCase):
    def test_unique_sorted(self):
        self.assertEqual(logic.unique_sorted([3, 1, 1.0000000001, 2]), [1, 2, 3])

    def test_chain_pairs(self):
        self.assertEqual(logic.chain_pairs([0, 10, 25]), [(0, 10), (10, 25)])
        self.assertEqual(logic.chain_pairs([5]), [])

    def test_nesting(self):
        boxes = [(0, 0, 100, 100), (10, 10, 20, 20), (12, 12, 15, 15), (200, 0, 300, 50)]
        self.assertEqual(logic.nest_by_containment(boxes), [None, 0, 1, None])

    def test_identical_boxes_no_cycle(self):
        b = (0, 0, 1, 1)
        self.assertEqual(logic.nest_by_containment([b, b]), [None, 0])

    def test_l_shape_needs_chains_not_per_segment_dims(self):
        pts = [(0, 0, 0), (100, 0, 0), (100, 40, 0), (40, 40, 0), (40, 100, 0),
               (0, 100, 0), (0, 0, 0)]
        plan = logic.plan_polyline_dims(pts)
        self.assertEqual(plan['xs'], [0, 40, 100])
        self.assertEqual(plan['ys'], [0, 40, 100])
        self.assertEqual(plan['slanted'], [])

    def test_slanted_deduplicated(self):
        pts = [(0, 0, 0), (10, 10, 0), (20, 0, 0), (30, 10, 0), (30, 20, 0)]
        plan = logic.plan_polyline_dims(pts)
        self.assertEqual(len(plan['slanted']), 1)  # three diagonals, two equal

    def test_hole_centres_join_chains(self):
        plan = logic.plan_polyline_dims([(0, 0, 0), (50, 0, 0), (50, 20, 0), (0, 20, 0), (0, 0, 0)],
                                        hole_centers=[(25, 10, 0)])
        self.assertEqual(plan['xs'], [0, 25, 50])


if __name__ == '__main__':
    unittest.main()
