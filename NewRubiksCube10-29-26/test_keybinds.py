import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from RubiksCube import (
    BIND_PRESETS,
    Cube,
    apply_bind_preset,
    main,
    parse_bound_moves,
    print_binds,
    set_keybind,
)


class KeybindTests(unittest.TestCase):
    def test_main_switches_cube_sizes(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["2x2", "R", "3x3", "quit"]):
            with redirect_stdout(output):
                main()

        text = output.getvalue()
        self.assertIn("Switched to a solved 2x2 cube.", text)
        self.assertIn("Switched to a solved 3x3 cube.", text)

    def test_keybind_expands_to_a_move_sequence(self):
        keybinds = {}
        set_keybind(keybinds, "v", "R U R' U'")

        self.assertEqual(
            parse_bound_moves("v F", keybinds),
            ["R", "U", "R'", "U'", "F"],
        )

    def test_binding_an_existing_key_replaces_its_sequence(self):
        keybinds = {}
        set_keybind(keybinds, "v", "R")
        set_keybind(keybinds, "v", "U2 F")

        self.assertEqual(parse_bound_moves("v", keybinds), ["U2", "F"])

    def test_original_move_notation_remains_available(self):
        keybinds = {}
        set_keybind(keybinds, "v", "R")

        self.assertEqual(parse_bound_moves("U2 v F'", keybinds), ["U2", "R", "F'"])

    def test_binding_rejects_reserved_command_keys(self):
        for key in ("q", "h", "?", "ab"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    set_keybind({}, key, "R")

    def test_binding_can_override_a_default_move_key(self):
        keybinds = {}

        set_keybind(keybinds, "d", "F")

        self.assertEqual(parse_bound_moves("d", keybinds), ["F"])

    def test_numeric_two_can_be_used_as_a_bind_key(self):
        keybinds = {}

        set_keybind(keybinds, "2", "D'")

        self.assertEqual(parse_bound_moves("2", keybinds), ["D'"])

    def test_binding_rejects_invalid_move_sequences(self):
        with self.assertRaises(ValueError):
            set_keybind({}, "v", "R X")

    def test_bind_list_and_reset_commands(self):
        output = StringIO()
        with patch(
            "builtins.input",
            side_effect=["bind v R U R'", "binds", "reset binds", "binds", "quit"],
        ):
            with redirect_stdout(output):
                main()

        text = output.getvalue()
        self.assertIn("Bound v to R U R'.", text)
        self.assertIn("v -> R U R'", text)
        self.assertIn("Custom keybinds reset.", text)
        self.assertIn("Custom keybinds (these last for this run):", text)
        self.assertIn("|   None", text)

    def test_clear_binds_command_removes_custom_bindings(self):
        output = StringIO()
        with patch(
            "builtins.input",
            side_effect=["bind d F", "clear binds", "binds", "quit"],
        ):
            with redirect_stdout(output):
                main()

        text = output.getvalue()
        self.assertIn("Bound d to F.", text)
        self.assertIn("Custom keybinds reset.", text)
        self.assertIn("|   None", text)

    def test_main_applies_moves_from_a_custom_key(self):
        cube = Cube()
        output = StringIO()
        with patch("RubiksCube.Cube", return_value=cube):
            with patch("builtins.input", side_effect=["bind d F", "d", "quit"]):
                with redirect_stdout(output):
                    main()

        expected = Cube()
        expected.apply_moves(["F"])
        self.assertEqual(cube.faces, expected.faces)

    def test_print_binds_lists_empty_and_populated_bindings(self):
        output = StringIO()
        with redirect_stdout(output):
            print_binds({"v": ["R", "U2"]})

        self.assertIn("v -> R U2", output.getvalue())
        self.assertIn("numpad:", output.getvalue())
        self.assertIn("* -> x", output.getvalue())
        self.assertIn("5 -> F'", output.getvalue())
        self.assertIn("+", output.getvalue().splitlines()[0])
        self.assertEqual(
            output.getvalue().splitlines()[0],
            output.getvalue().splitlines()[-1],
        )

    def test_help_and_algorithm_menus_are_boxed(self):
        from RubiksCube import print_help, print_algorithms

        for printer in (print_help, print_algorithms):
            with self.subTest(printer=printer.__name__):
                output = StringIO()
                with redirect_stdout(output):
                    printer()
                lines = output.getvalue().splitlines()
                self.assertEqual(lines[0], lines[-1])
                self.assertTrue(all(line.startswith("| ") for line in lines[1:-1]))

    def test_numpad_preset_covers_every_face_turn_and_cube_rotation(self):
        keybinds = {}

        apply_bind_preset(keybinds, "numpad")

        self.assertEqual(
            keybinds,
            {
                "*": ["x"],
                "+": ["y"],
                "/": ["z"],
                "1": ["U'"],
                "2": ["D'"],
                "3": ["L'"],
                "4": ["R'"],
                "5": ["F'"],
                "6": ["B'"],
                "7": ["U2"],
                "8": ["D2"],
                "9": ["L2"],
                "0": ["R2"],
                ".": ["F2"],
                "-": ["B2"],
            },
        )
        self.assertEqual(
            parse_bound_moves("1 2 3 4 5 6 7 8 9 0 . - * + /", keybinds),
            [
                "U'", "D'", "L'", "R'", "F'", "B'",
                "U2", "D2", "L2", "R2", "F2", "B2",
                "x", "y", "z",
            ],
        )

    def test_presets_are_valid_and_merge_without_removing_other_binds(self):
        for name, preset in BIND_PRESETS.items():
            with self.subTest(preset=name):
                keybinds = {"!": ["R"]}
                applied = apply_bind_preset(keybinds, name)

                self.assertEqual(len(applied), len(preset))
                self.assertEqual(keybinds["!"], ["R"])

    def test_dev_preset_matches_requested_bindings(self):
        keybinds = {}

        apply_bind_preset(keybinds, "dev")

        self.assertEqual(
            keybinds,
            {
                ".": ["y"],
                "0": ["x"],
                "1": ["L"],
                "3": ["R'"],
                "4": ["L'"],
                "5": ["Rw'"],
                "6": ["R"],
                "7": ["U"],
                "8": ["Rw"],
                "9": ["U'"],
                "a": ["F'"],
                "d": ["F"],
                "e": ["Fw'"],
                "f": ["Fw"],
                "s": ["M"],
                "w": ["M'"],
                "x": ["S"],
            },
        )

    def test_bind_preset_command_applies_numpad_mapping(self):
        cube = Cube()
        with patch("RubiksCube.Cube", return_value=cube):
            with patch(
                "builtins.input",
                side_effect=["bind preset numpad", "1 7", "quit"],
            ):
                with redirect_stdout(StringIO()):
                    main()

        expected = Cube()
        expected.apply_moves(["U'", "U2"])
        self.assertEqual(cube.faces, expected.faces)


if __name__ == "__main__":
    unittest.main()
