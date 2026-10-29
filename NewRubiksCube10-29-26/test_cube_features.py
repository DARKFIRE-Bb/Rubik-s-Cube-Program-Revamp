import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from RubiksCube import (
    Cube,
    calculate_averages,
    describe_move,
    edit_solve_record,
    inspection_penalty,
    load_cube_state,
    load_solve_records,
    main,
    run_speed_timer,
    run_stats_menu,
    save_cube_state,
    save_solve_record,
    timed_key_moves,
    timed_key_from_scan_code,
)


class CubeHistoryTests(unittest.TestCase):
    def test_move_sequences_can_be_undone_and_redone(self):
        cube = Cube()
        solved_faces = {
            face: [row[:] for row in grid] for face, grid in cube.faces.items()
        }

        cube.apply_moves(["R", "U", "F"])
        self.assertTrue(cube.undo())
        self.assertEqual(cube.faces, solved_faces)
        self.assertTrue(cube.redo())
        self.assertNotEqual(cube.faces, solved_faces)

    def test_new_moves_clear_redo_history(self):
        cube = Cube()
        cube.apply_moves(["R"])
        cube.undo()
        cube.apply_moves(["U"])

        self.assertFalse(cube.redo())

    def test_invalid_move_sequence_rolls_back_without_history_entry(self):
        cube = Cube()
        solved_faces = {
            face: [row[:] for row in grid] for face, grid in cube.faces.items()
        }

        with self.assertRaises(ValueError):
            cube.apply_moves(["R", "not-a-move"])

        self.assertEqual(cube.faces, solved_faces)
        self.assertFalse(cube.undo())


class CubePersistenceTests(unittest.TestCase):
    def test_saved_cube_preserves_size_and_stickers(self):
        cube = Cube(size=2)
        cube.apply_moves(["R", "U2", "F'"])

        with tempfile.TemporaryDirectory() as directory:
            save_cube_state(cube, "practice_1", directory)
            loaded = load_cube_state("practice_1", directory)

        self.assertEqual(loaded.size, 2)
        self.assertEqual(loaded.faces, cube.faces)
        self.assertFalse(loaded.undo())

    def test_state_names_cannot_escape_the_save_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_cube_state(Cube(), "..\\outside", directory)

    def test_invalid_saved_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "broken.json"
            state_path.write_text(
                json.dumps({"size": 3, "faces": Cube().faces}), encoding="utf-8"
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["faces"]["U"][0][0] = "X"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sticker colors or counts"):
                load_cube_state("broken", directory)


class SolveStatisticsTests(unittest.TestCase):
    def test_timed_keypress_resolves_moves_and_bindings_and_ignores_other_keys(self):
        keybinds = {"a": ["R'", "U2"]}

        self.assertEqual(timed_key_moves("R", keybinds), ["R"])
        self.assertEqual(timed_key_moves("a", keybinds), ["R'", "U2"])
        self.assertEqual(timed_key_moves("?", keybinds), [])
        self.assertEqual(timed_key_moves("2", keybinds), [])
        self.assertEqual(timed_key_from_scan_code("H"), "8")
        self.assertEqual(timed_key_from_scan_code("G"), "7")
        self.assertIsNone(timed_key_from_scan_code("Z"))

    def test_records_preserve_legacy_format_and_penalties(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            path.write_text(
                json.dumps([{"time": 20.0, "scramble": "R U"}]), encoding="utf-8"
            )
            record = save_solve_record(["F", "R2"], 30.0, path, "+2")

            self.assertEqual(record["penalty"], "+2")
            records = load_solve_records(path)

        self.assertEqual(records[0]["scramble"], "R U")
        from RubiksCube import format_averages

        self.assertIn("  3x3 timed solves:", format_averages(records)[1:])
        self.assertEqual(records[1]["time"], 30.0)
        self.assertEqual(records[1]["penalty"], "+2")
        self.assertEqual(records[1]["size"], 3)

    def test_stats_separate_cube_sizes_and_solve_modes(self):
        from RubiksCube import format_averages

        records = [
            {"time": 10.0, "scramble": "R", "mode": "virtual", "size": 3},
            {"time": 20.0, "scramble": "R", "mode": "manual", "size": 3},
            {"time": 30.0, "scramble": "R", "mode": "virtual", "size": 2},
            {"time": 40.0, "scramble": "R", "mode": "manual", "size": 2},
        ]

        lines = format_averages(records)

        self.assertIn("  3x3 timed solves:", lines)
        self.assertIn("  3x3 manual solves:", lines)
        self.assertIn("  2x2 timed solves:", lines)
        self.assertIn("  2x2 manual solves:", lines)
        self.assertEqual(
            lines[lines.index("  3x3 timed solves:") + 5],
            "    All-time average: 0:10.00",
        )
        self.assertEqual(
            lines[lines.index("  3x3 manual solves:") + 5],
            "    All-time average: 0:20.00",
        )
        self.assertEqual(
            lines[lines.index("  2x2 timed solves:") + 5],
            "    All-time average: 0:30.00",
        )
        self.assertEqual(
            lines[lines.index("  2x2 manual solves:") + 5],
            "    All-time average: 0:40.00",
        )
        self.assertIn("      1. 0:10.00 (none)  R", lines)
        self.assertIn("      2. 0:20.00 (none)  Manual solve", lines)
        self.assertIn("      3. 0:30.00 (none)  R", lines)
        self.assertIn("      4. 0:40.00 (none)  Manual solve", lines)

    def test_stats_menu_edits_and_deletes_numbered_records(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            save_solve_record(["R", "U"], 20.0, path)
            save_solve_record(["F", "L"], 30.0, path)
            output = StringIO()
            with patch(
                "builtins.input",
                side_effect=[
                    "edit 2 time 1:02.34",
                    "edit 1 scramble R U R'",
                    "delete 2",
                    "yes",
                    "back",
                ],
            ):
                with redirect_stdout(output):
                    run_stats_menu(path)

            records = load_solve_records(path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["scramble"], "R U R'")
        self.assertEqual(records[0]["time"], 20.0)
        self.assertIn("2. 0:30.00 (none)  F L", output.getvalue())
        self.assertIn("Updated solve 2.", output.getvalue())
        self.assertIn("Deleted solve 2.", output.getvalue())

    def test_stats_menu_clear_removes_all_solves_after_confirmation(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            save_solve_record(["R", "U"], 20.0, path)
            save_solve_record(["F", "L"], 30.0, path)
            session_records = load_solve_records(path)[-1:]
            output = StringIO()
            with patch("builtins.input", side_effect=["clear", "yes", "back"]):
                with redirect_stdout(output):
                    run_stats_menu(path, session_records)

            records = load_solve_records(path)

        self.assertEqual(records, [])
        self.assertEqual(session_records, [])
        self.assertIn("All solve records cleared.", output.getvalue())
        self.assertIn("No solves recorded yet.", output.getvalue())

    def test_stats_menu_clear_can_be_canceled(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            save_solve_record(["R"], 20.0, path)
            output = StringIO()
            with patch("builtins.input", side_effect=["clear", "no", "back"]):
                with redirect_stdout(output):
                    run_stats_menu(path)

            records = load_solve_records(path)

        self.assertEqual(len(records), 1)
        self.assertIn("Clear canceled.", output.getvalue())

    def test_solve_record_edits_validate_fields_and_numbers(self):
        records = [{"time": 10.0, "scramble": "R", "penalty": "none"}]

        edit_solve_record(records, 1, "penalty", "dnf")

        self.assertEqual(records[0]["penalty"], "DNF")
        with self.assertRaises(ValueError):
            edit_solve_record(records, 2, "time", "20")
        with self.assertRaises(ValueError):
            edit_solve_record(records, 1, "scramble", "R X")

    def test_averages_apply_penalties_and_ignore_single_dnf_in_trimmed_average(self):
        records = [
            {"time": 10.0, "scramble": "R"},
            {"time": 11.0, "scramble": "R", "penalty": "+2"},
            {"time": 12.0, "scramble": "R"},
            {"time": 13.0, "scramble": "R"},
            {"time": 1.0, "scramble": "R", "penalty": "DNF"},
        ]

        averages = calculate_averages(records)

        self.assertEqual(averages["best"], 10.0)
        self.assertAlmostEqual(averages["ao5"], 12.6666667)
        self.assertEqual(averages["all_time"], 12.0)

    def test_multiple_dnfs_make_a_trimmed_average_dnf(self):
        records = [
            {"time": 10.0, "scramble": "R"},
            {"time": 11.0, "scramble": "R"},
            {"time": 12.0, "scramble": "R"},
            {"time": 13.0, "scramble": "R", "penalty": "DNF"},
            {"time": 14.0, "scramble": "R", "penalty": "DNF"},
        ]

        self.assertTrue(math.isinf(calculate_averages(records)["ao5"]))

    def test_inspection_penalty_boundaries(self):
        self.assertEqual(inspection_penalty(14.99), "none")
        self.assertEqual(inspection_penalty(15), "+2")
        self.assertEqual(inspection_penalty(17), "DNF")

    def test_spacebar_timer_starts_and_stops_on_space(self):
        from contextlib import redirect_stdout
        from io import StringIO

        key_states = iter((False, True, True))
        fake_msvcrt = SimpleNamespace(
            kbhit=lambda: next(key_states), getwch=lambda: " "
        )
        with patch.dict(sys.modules, {"msvcrt": fake_msvcrt}):
            with patch(
                "RubiksCube.time.perf_counter", side_effect=(0, 1, 1, 1, 3)
            ):
                with patch("RubiksCube.time.sleep"):
                    with redirect_stdout(StringIO()):
                        elapsed, penalty = run_speed_timer()

        self.assertEqual(elapsed, 2)
        self.assertEqual(penalty, "none")

    def test_timed_command_stops_and_records_when_virtual_cube_is_solved(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            records_path = Path(directory) / "solves.json"
            output = StringIO()

            def fixed_scramble(cube):
                cube.apply_moves(["R"])
                return ["R"]

            with patch("RubiksCube.SOLVE_RECORDS_PATH", records_path):
                with patch("RubiksCube.scramble", side_effect=fixed_scramble):
                    with patch("msvcrt.getwch", side_effect=["?", "a"]):
                        with patch(
                            "builtins.input",
                            side_effect=[
                                "bind a R'",
                                "timed",
                                "stats",
                                "back",
                                "quit",
                            ],
                        ):
                            with redirect_stdout(output):
                                main()

            record = load_solve_records(records_path)[0]

        self.assertEqual(record["penalty"], "none")
        self.assertEqual(record["scramble"], "R")
        self.assertEqual(record["mode"], "virtual")
        self.assertGreaterEqual(record["time"], 0)
        self.assertIn("Virtual timer started.", output.getvalue())
        self.assertIn("Timed solve: press move/bind keys", output.getvalue())
        self.assertIn("Virtual timed solve:", output.getvalue())
        self.assertNotIn("Invalid move", output.getvalue())
        self.assertIn("1. ", output.getvalue())
        self.assertIn("Moves: U D L R F B", output.getvalue())

    def test_timed_command_displays_cube_and_returns_to_move_prompt(self):
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()

        def fixed_scramble(cube):
            cube.apply_moves(["R"])
            return ["R"]

        with patch("RubiksCube.scramble", side_effect=fixed_scramble):
            with patch("RubiksCube.run_speed_timer", side_effect=AssertionError):
                with patch("msvcrt.getwch", side_effect=["\x1b"]):
                    with patch("builtins.input", side_effect=["timed", "quit"]):
                        with redirect_stdout(output):
                            main()

        scrambled_cube = Cube()
        scrambled_cube.apply_moves(["R"])
        rendered_scramble = scrambled_cube.render(
            color=False, view="cube", show_help=True
        )
        self.assertIn(rendered_scramble, output.getvalue())
        self.assertIn("Virtual timed solve canceled", output.getvalue())

    def test_timed_solve_applies_preset_keys_and_confirms_them(self):
        from contextlib import redirect_stdout
        from io import StringIO

        cube = Cube()
        output = StringIO()

        def fixed_scramble(target_cube):
            target_cube.apply_moves(["R"])
            return ["R"]

        with patch("RubiksCube.Cube", return_value=cube):
            with patch("RubiksCube.scramble", side_effect=fixed_scramble):
                with patch("msvcrt.getwch", side_effect=["c", "\x1b"]):
                    with patch(
                        "builtins.input",
                        side_effect=["bind preset home", "timed", "quit"],
                    ):
                        with redirect_stdout(output):
                            main()

        expected = Cube()
        expected.apply_moves(["R2"])
        self.assertEqual(cube.faces, expected.faces)
        self.assertIn("c -> R", output.getvalue())
        self.assertIn(
            expected.render(color=False, view="cube", show_help=True),
            output.getvalue(),
        )

    def test_manual_mode_runs_timer_without_scrambling_virtual_cube(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            records_path = Path(directory) / "solves.json"
            output = StringIO()
            with patch("RubiksCube.SOLVE_RECORDS_PATH", records_path):
                with patch("RubiksCube.scramble", side_effect=AssertionError):
                    with patch(
                        "RubiksCube.run_speed_timer", return_value=(12.34, "none")
                    ):
                        with patch(
                            "builtins.input", side_effect=["manual", "+2", "quit"]
                        ):
                            with redirect_stdout(output):
                                main()
            record = load_solve_records(records_path)[0]

        self.assertEqual(record["mode"], "manual")
        self.assertEqual(record["scramble"], "")
        self.assertEqual(record["penalty"], "+2")
        self.assertEqual(record["time"], 12.34)
        self.assertIn("Manual solve time:", output.getvalue())


class GuidedMoveTests(unittest.TestCase):
    def test_help_colors_section_headers_and_alternates_command_colors(self):
        from io import StringIO
        from unittest.mock import patch
        from RubiksCube import print_help

        class TTYStringIO(StringIO):
            def isatty(self):
                return True

        output = TTYStringIO()
        with patch("RubiksCube.sys.stdout", output):
            print_help()

        help_text = output.getvalue()
        self.assertIn("\033[1m\033[96mSOLVING\033[0m", help_text)
        self.assertIn("\033[93mscramble\033[0m", help_text)
        self.assertIn("\033[96mtimed\033[0m", help_text)
        self.assertIn("\033[93mmanual\033[0m", help_text)

    def test_startup_shows_compact_help_panel_instead_of_full_help_page(self):
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()
        with patch("builtins.input", side_effect=["quit"]):
            with redirect_stdout(output):
                main()

        text = output.getvalue()
        self.assertIn("QUICK HELP", text)
        self.assertNotIn("COMMANDS", text)
        self.assertIn("help = full guide", text)

    def test_quit_command_clears_an_interactive_terminal(self):
        from io import StringIO
        from unittest.mock import patch

        class TTYStringIO(StringIO):
            def isatty(self):
                return True

        output = TTYStringIO()
        with patch("builtins.input", side_effect=["q"]):
            with patch("RubiksCube.sys.stdout", output):
                with patch("RubiksCube.os.system") as system:
                    main()

        system.assert_called_once_with("cls" if sys.platform == "win32" else "clear")
        self.assertIn("Goodbye!", output.getvalue())

    def test_timed_solve_q_clears_an_interactive_terminal(self):
        from io import StringIO
        from types import SimpleNamespace
        from unittest.mock import patch

        class TTYStringIO(StringIO):
            def isatty(self):
                return True

        output = TTYStringIO()
        with patch("builtins.input", side_effect=["timed"]):
            with patch("RubiksCube.sys.stdout", output):
                with patch.dict("sys.modules", {"msvcrt": SimpleNamespace(getwch=lambda: "q")}):
                    with patch("RubiksCube.os.system") as system:
                        main()

        system.assert_called_once_with("cls" if sys.platform == "win32" else "clear")
        self.assertIn("Goodbye!", output.getvalue())

    def test_move_instructions_explain_turn_direction_and_target(self):
        self.assertIn("clockwise", describe_move("R"))
        self.assertIn("counterclockwise", describe_move("U'"))
        self.assertIn("half-turn", describe_move("F2"))
        self.assertIn("whole cube", describe_move("x"))
        self.assertIn("adjacent layer", describe_move("Rw"))

    def test_help_panel_renders_to_the_right_of_both_cube_views(self):
        cube = Cube()

        for view in ("cube", "net"):
            with self.subTest(view=view):
                rendered = cube.render(color=False, view=view, show_help=True)
                lines = rendered.splitlines()
                first_panel_line = next(
                    line for line in lines if "QUICK HELP" in line
                )
                self.assertIn("|  QUICK HELP", first_panel_line)
                self.assertTrue(any("solve = solve cube" in line for line in lines))
                self.assertTrue(any("help = full guide" in line for line in lines))

    def test_quick_help_colors_commands_differently_from_descriptions(self):
        rendered = Cube().render(color=True, show_help=True)

        self.assertIn("\033[93msolve\033[0m", rendered)
        self.assertIn("\033[96m = solve cube | \033[0m", rendered)

    def test_graphics_themes_recolor_net_and_perspective_cubes(self):
        from RubiksCube import THEMES, _solved_banner

        self.assertEqual(set(THEMES), {
            "default", "christmas", "halloween", "grayscale", "colorblind",
            "deuteranopia", "protanopia", "tritanopia", "warm", "cold", "rubiks",
            "dev",
        })
        for theme in THEMES:
            with self.subTest(theme=theme):
                net = Cube().render(view="net", theme=theme)
                perspective = Cube().render(theme=theme)
                banner = _solved_banner(True, theme)

                net_color = (
                    "\033[102m"
                    if theme in ("default", "rubiks")
                    else f"\033[48;5;{THEMES[theme]['stickers']['G']}m"
                )
                self.assertIn(net_color, net)
                self.assertIn(
                    f"\033[38;5;{THEMES[theme]['stickers']['G']}m",
                    perspective,
                )
                self.assertIn(f"\033[38;5;{THEMES[theme]['banner'][0]}m", banner)

        self.assertIn("\033[102m", Cube().render(view="net", theme="default"))
        themed_panel = Cube().render(theme="christmas", show_help=True)
        self.assertIn("\033[38;5;196msolve\033[0m", themed_panel)
        self.assertIn("\033[38;5;46m = solve cube | \033[0m", themed_panel)

    def test_rubiks_theme_preserves_original_cube_colors_but_themes_text(self):
        default_cube = Cube()

        self.assertEqual(
            default_cube.render(view="net", theme="rubiks"),
            default_cube.render(view="net", theme="default"),
        )
        self.assertEqual(
            default_cube.render(theme="rubiks"),
            default_cube.render(theme="default"),
        )
        themed = default_cube.render(theme="rubiks", show_help=True)
        self.assertIn("\033[38;5;15msolve\033[0m", themed)
        self.assertIn("\033[38;5;208m = solve cube | \033[0m", themed)

    def test_rubiks_theme_text_uses_all_original_cube_colors(self):
        from RubiksCube import COLOR_256, _append_help_panel

        panel = _append_help_panel("", color=True, theme="rubiks")
        for color in COLOR_256.values():
            with self.subTest(color=color):
                self.assertIn(f"\033[38;5;{color}m", panel)

    def test_theme_command_changes_active_theme_and_lists_choices(self):
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()
        with patch(
            "builtins.input",
            side_effect=["theme christmas", "themes", "quit"],
        ):
            with redirect_stdout(output):
                main()

        self.assertIn("Graphics theme set to Christmas.", output.getvalue())
        self.assertIn("christmas", output.getvalue())
        self.assertIn("deuteranopia", output.getvalue())

    def test_theme_aliases_resolve_to_named_palettes(self):
        from RubiksCube import _get_theme

        self.assertEqual(_get_theme("color-blind")["name"], "Color-blind friendly")
        self.assertEqual(_get_theme("rubiks-exclusive")["name"], "Rubik's exclusive")

    def test_dev_theme_uses_purple_and_grayscale_palette(self):
        from RubiksCube import THEMES, _solved_banner

        theme = THEMES["dev"]
        self.assertEqual(
            set(theme["stickers"].values()),
            {255, 250, 246, 238, 141, 98},
        )
        self.assertEqual(theme["edge"], 232)
        self.assertIn("\033[38;5;141m", _solved_banner(True, "dev"))
        rendered = Cube().render(theme="dev", show_help=True)
        self.assertIn("\033[38;5;141msolve\033[0m", rendered)

    def test_all_boxed_menus_use_the_selected_theme(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from RubiksCube import (
            print_algorithms,
            print_bind_presets,
            print_binds,
            print_help,
            print_themes,
        )

        class TTYStringIO(StringIO):
            def isatty(self):
                return True

        output = TTYStringIO()
        with patch.dict("os.environ", {}, clear=True):
            with redirect_stdout(output):
                print_binds({}, "dev")
                print_bind_presets("dev")
                print_algorithms("dev")
                print_help("dev")
                print_themes("dev", "dev")

        rendered = output.getvalue()
        self.assertGreaterEqual(rendered.count("\033[38;5;141m+"), 5)
        self.assertIn("\033[38;5;177mCustom keybinds", rendered)
        import re

        plain_text = re.sub(r"\033\[[0-9;]*m", "", rendered)
        self.assertIn("Dev (purple grayscale) (current)", plain_text)

    def test_theme_descriptions_preview_each_themes_sticker_colors(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import re
        from RubiksCube import THEMES, print_themes

        class TTYStringIO(StringIO):
            def isatty(self):
                return True

        output = TTYStringIO()
        with patch.dict("os.environ", {}, clear=True):
            with redirect_stdout(output):
                print_themes()

        rendered = output.getvalue()
        rendered_lines = rendered.splitlines()
        plain_lines = [
            re.sub(r"\033\[[0-9;]*m", "", line)
            for line in rendered_lines
        ]
        for theme_name, palette in THEMES.items():
            with self.subTest(theme=theme_name):
                line_index = next(
                    index for index, line in enumerate(plain_lines)
                    if theme_name in line
                )
                theme_line = rendered_lines[line_index]
                self.assertIn(
                    palette["name"],
                    plain_lines[line_index],
                )
                self.assertTrue(
                    plain_lines[line_index].startswith(f"|   {theme_name:<18} ")
                )
                preview_colors = re.findall(
                    r"\033\[38;5;(\d+)m", theme_line
                )
                expected_colors = {
                    str(color)
                    for sticker, color in palette["stickers"].items()
                    if sticker != "W"
                }
                self.assertEqual(set(preview_colors), expected_colors)

    def test_stats_sheet_uses_the_selected_theme(self):
        from contextlib import redirect_stdout
        from io import StringIO

        class TTYStringIO(StringIO):
            def isatty(self):
                return True

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solves.json"
            output = TTYStringIO()
            with patch.dict("os.environ", {}, clear=True):
                with patch("builtins.input", side_effect=["back"]):
                    with redirect_stdout(output):
                        run_stats_menu(path, theme="dev")

        rendered = output.getvalue()
        self.assertIn("\033[38;5;141m+", rendered)
        self.assertIn("\033[38;5;177mNo solves recorded yet.", rendered)

    def test_net_face_labels_are_centered_over_each_face(self):
        for size in (2, 3):
            with self.subTest(size=size):
                net = Cube(size=size).render(color=False, view="net")
                lines = net.splitlines()
                header = lines[size + 1]
                face_width = size * 4 - 1

                for face_index, face in enumerate(("L", "F", "R", "B")):
                    face_start = 3 + face_index * (face_width + 3)
                    label_position = header.index(face, face_start)
                    self.assertEqual(
                        label_position - face_start,
                        (face_width - 1) // 2,
                    )

    def test_main_keeps_help_panel_visible_during_animated_solving(self):
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()
        with patch("RubiksCube.Cube.solve", return_value=["R"]):
            with patch("builtins.input", side_effect=["R", "solve", "quit"]):
                with patch("RubiksCube.time.sleep"):
                    with redirect_stdout(output):
                        main()

        self.assertIn("QUICK HELP", output.getvalue())
        self.assertIn("Solving... 1/1: R", output.getvalue())

    def test_guided_solve_explains_moves_and_can_be_stopped(self):
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()
        with patch("RubiksCube.Cube.solve", return_value=["R", "U'"]):
            with patch("builtins.input", side_effect=["R", "guide", "", "q", "quit"]):
                with redirect_stdout(output):
                    main()

        self.assertIn("Step 1/2: R - Turn the right face: clockwise turn.", output.getvalue())
        self.assertIn("Guided solve stopped.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
