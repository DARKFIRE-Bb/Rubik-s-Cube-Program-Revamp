import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from RubiksCube import Cube, main


class IndependentSolverTests(unittest.TestCase):
    def test_two_by_two_solver_handles_current_sticker_state(self):
        cube = Cube(size=2)
        cube.apply_moves(["R", "U2", "F'", "L", "D"])

        solution = cube.solve()
        cube.apply_moves(solution)

        self.assertTrue(cube.is_solved())

    def test_two_by_two_solver_handles_odd_corner_permutation(self):
        cube = Cube(size=2)
        cube.apply_moves(["R", "U", "F", "L2", "D'", "B"])

        cube.apply_moves(cube.solve())

        self.assertTrue(cube.is_solved())

    def test_two_by_two_solver_rejects_wrong_sticker_counts(self):
        cube = Cube(size=2)
        cube.faces["U"][0][0] = "X"

        with self.assertRaisesRegex(ValueError, "four stickers"):
            cube.solve()

    def test_solved_cube_returns_no_moves(self):
        self.assertEqual(Cube().solve(), [])

    def test_solver_solves_from_current_stickers_not_move_history(self):
        cube = Cube()
        cube.apply_moves(["R", "U2", "F'", "L", "D"])
        cube.apply_moves(cube.solve())
        self.assertTrue(cube.is_solved())

    def test_solver_handles_a_scramble_after_a_previous_solve(self):
        cube = Cube()
        cube.apply_moves(["R", "U", "F'"])
        cube.apply_moves(cube.solve())
        self.assertTrue(cube.is_solved())

        cube.apply_moves(["L2", "D'", "B", "U2"])
        solution = cube.solve()
        cube.apply_moves(solution)

        self.assertTrue(cube.is_solved())

    def test_solver_handles_whole_cube_rotations(self):
        cube = Cube()
        cube.apply_moves(["x", "R", "U'", "z2", "F2"])

        cube.apply_moves(cube.solve())

        self.assertTrue(cube.is_solved())

    def test_solver_reports_invalid_sticker_colors(self):
        cube = Cube()
        cube.faces["U"][0][0] = "X"

        with self.assertRaisesRegex(ValueError, "nine stickers"):
            cube.solve()

    def test_solve_command_uses_the_generated_solution(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["R U F'", "solve", "quit"]):
            with patch("RubiksCube.time.sleep"):
                with redirect_stdout(output):
                    main()

        self.assertIn("Solving...", output.getvalue())
        self.assertIn("THE CUBE IS SOLVED!", output.getvalue())


if __name__ == "__main__":
    unittest.main()
