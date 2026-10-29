import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from RubiksCube import (
    ALGORITHM_SHORTCUTS,
    Cube,
    FACE_SCREEN_OFFSETS,
    _project,
    _project_face,
    apply_algorithm,
    main,
)


class CubeSizeTests(unittest.TestCase):
    def test_cube_size_can_be_selected(self):
        cube = Cube(size=2)

        self.assertEqual(cube.size, 2)
        self.assertTrue(all(len(face) == 2 for face in cube.faces.values()))
        self.assertTrue(
            all(
                len(row) == 2
                for face in cube.faces.values()
                for row in face
            )
        )

    def test_two_by_two_face_turn_and_inverse_restore_cube(self):
        for face in "UDLRFB":
            with self.subTest(face=face):
                cube = Cube(size=2)
                solved_faces = {
                    name: [row[:] for row in grid]
                    for name, grid in cube.faces.items()
                }
                cube.apply_moves([face, face + "'"])
                self.assertEqual(cube.faces, solved_faces)

    def test_two_by_two_whole_cube_rotations_and_wide_turns(self):
        for rotation, wide_move in (("x", "Rw"), ("y", "Uw"), ("z", "Fw")):
            with self.subTest(rotation=rotation):
                rotated = Cube(size=2)
                wide = Cube(size=2)
                rotated.apply_moves([rotation])
                wide.apply_moves([wide_move])
                self.assertEqual(rotated.faces, wide.faces)

    def test_two_by_two_slice_moves_and_inverses_restore_cube(self):
        for move in "MES":
            with self.subTest(move=move):
                cube = Cube(size=2)
                cube.apply_moves([move, move + "'"])
                self.assertTrue(cube.is_solved())

    def test_all_algorithm_shortcuts_work_on_a_two_by_two(self):
        for name in ALGORITHM_SHORTCUTS:
            with self.subTest(name=name):
                cube = Cube(size=2)
                apply_algorithm(cube, name)
                self.assertEqual(cube.size, 2)

    def test_two_by_two_net_and_perspective_rendering(self):
        cube = Cube(size=2)

        self.assertIn("W", cube.render(color=False, view="net"))
        self.assertIn("3D view: U top | F front | R right", cube.render())

    def test_two_by_two_perspective_insets_faces_and_lowers_top(self):
        point = (0, 0, 0)
        base_x, base_y = _project(point)

        self.assertEqual(_project_face(point, "U", size=2), (base_x + 4, base_y))
        self.assertEqual(_project_face(point, "F", size=2), (base_x + 4, base_y))
        self.assertEqual(_project_face(point, "R", size=2), (base_x + 4, base_y))

    def test_two_by_two_offsets_do_not_change_three_by_three_projection(self):
        point = (0, 0, 0)

        for face, (offset_x, offset_y) in FACE_SCREEN_OFFSETS.items():
            with self.subTest(face=face):
                base_x, base_y = _project(point)
                self.assertEqual(
                    _project_face(point, face, size=3),
                    (base_x + offset_x, base_y + offset_y),
                )

    def test_invalid_cube_size_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "size must be 2 or 3"):
            Cube(size=4)

    def test_main_switches_cube_sizes(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["2x2", "R", "3x3", "quit"]):
            with redirect_stdout(output):
                main()

        text = output.getvalue()
        self.assertIn("Switched to a solved 2x2 cube.", text)
        self.assertIn("Switched to a solved 3x3 cube.", text)


if __name__ == "__main__":
    unittest.main()
