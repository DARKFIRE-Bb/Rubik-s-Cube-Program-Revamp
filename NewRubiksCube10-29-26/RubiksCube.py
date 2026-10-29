"""Play with a virtual Rubik's Cube in the terminal."""

import os
import json
import math
import random
import re
import sys
import time
from pathlib import Path


# Each face is described from the viewpoint of someone looking directly at it.
# The right/up vectors also define how its rows and columns appear in the net.
FACE_GEOMETRY = {
    "U": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    "D": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "F": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "B": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
    "R": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "L": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
}
FACE_COLORS = {
    "U": "W",
    "D": "Y",
    "F": "G",
    "B": "B",
    "R": "R",
    "L": "O",
}
FACE_ORDER = ("U", "D", "L", "R", "F", "B")
FACE_MOVE_PATTERN = re.compile(r"([UDLRFB])([2']?)", re.IGNORECASE)
WIDE_MOVE_PATTERN = re.compile(r"([UDLRFB])[wW]([2']?)", re.IGNORECASE)
SLICE_MOVE_PATTERN = re.compile(r"([MES])([2']?)", re.IGNORECASE)
COLOR_CODES = {
    "W": "\033[107m",
    "Y": "\033[103m",
    "G": "\033[102m",
    "B": "\033[104m",
    "R": "\033[101m",
    "O": "\033[48;5;208m",
}
COLOR_256 = {
    "W": 15,
    "Y": 226,
    "G": 46,
    "B": 21,
    "R": 196,
    "O": 208,
}
THEMES = {
    "default": {
        "name": "Default",
        "stickers": COLOR_256,
        "edge": 0,
        "accent": "\033[93m",
        "secondary": "\033[96m",
        "tertiary": "\033[96m",
        "banner": (208, 226, 46),
    },
    "christmas": {
        "name": "Christmas",
        "stickers": {"W": 255, "Y": 220, "G": 34, "B": 27, "R": 160, "O": 208},
        "edge": 22,
        "accent": 196,
        "secondary": 46,
        "tertiary": 226,
        "banner": (196, 46, 226),
    },
    "halloween": {
        "name": "Halloween",
        "stickers": {"W": 255, "Y": 226, "G": 46, "B": 129, "R": 202, "O": 208},
        "edge": 53,
        "accent": 202,
        "secondary": 226,
        "tertiary": 129,
        "banner": (202, 226, 129),
    },
    "grayscale": {
        "name": "Grayscale",
        "stickers": {"W": 255, "Y": 250, "G": 245, "B": 240, "R": 235, "O": 230},
        "edge": 235,
        "accent": 255,
        "secondary": 250,
        "tertiary": 245,
        "banner": (255, 250, 245),
    },
    "colorblind": {
        "name": "Color-blind friendly",
        "stickers": {"W": 255, "Y": 226, "G": 43, "B": 39, "R": 196, "O": 208},
        "edge": 17,
        "accent": 226,
        "secondary": 39,
        "tertiary": 43,
        "banner": (226, 39, 43),
    },
    "deuteranopia": {
        "name": "Deuteranopia",
        "stickers": {"W": 255, "Y": 226, "G": 39, "B": 27, "R": 201, "O": 208},
        "edge": 17,
        "accent": 226,
        "secondary": 39,
        "tertiary": 201,
        "banner": (226, 39, 201),
    },
    "protanopia": {
        "name": "Protanopia",
        "stickers": {"W": 255, "Y": 226, "G": 43, "B": 39, "R": 201, "O": 208},
        "edge": 17,
        "accent": 226,
        "secondary": 39,
        "tertiary": 43,
        "banner": (226, 39, 43),
    },
    "tritanopia": {
        "name": "Tritanopia",
        "stickers": {"W": 255, "Y": 220, "G": 34, "B": 201, "R": 196, "O": 208},
        "edge": 52,
        "accent": 220,
        "secondary": 196,
        "tertiary": 34,
        "banner": (220, 196, 34),
    },
    "warm": {
        "name": "Warm colors",
        "stickers": {"W": 255, "Y": 226, "G": 208, "B": 202, "R": 196, "O": 160},
        "edge": 52,
        "accent": 208,
        "secondary": 202,
        "tertiary": 226,
        "banner": (208, 202, 226),
    },
    "cold": {
        "name": "Cold colors",
        "stickers": {"W": 255, "Y": 159, "G": 51, "B": 27, "R": 93, "O": 69},
        "edge": 17,
        "accent": 51,
        "secondary": 39,
        "tertiary": 159,
        "banner": (51, 39, 159),
    },
    "rubiks": {
        "name": "Rubik's exclusive",
        "stickers": COLOR_256,
        "edge": 0,
        "accent": 196,
        "secondary": 208,
        "tertiary": 226,
        "command_colors": tuple(COLOR_256.values()),
        "banner": (196, 46, 226),
    },
    "dev": {
        "name": "Dev (purple grayscale)",
        "stickers": {"W": 255, "Y": 250, "G": 246, "B": 238, "R": 141, "O": 98},
        "edge": 232,
        "accent": 141,
        "secondary": 250,
        "tertiary": 177,
        "banner": (141, 250, 177),
    },
}
THEME_ALIASES = {
    "color-blind": "colorblind",
    "rubiks-exclusive": "rubiks",
}
COLOR_RESET = "\033[0m"
RENDER_SIZE = 55
SOLVE_STEP_DELAY = 0.25
SOLVE_RECORDS_PATH = Path.home() / ".rubikscube" / "solve_records.json"
CUBE_STATES_PATH = Path.home() / ".rubikscube" / "states"
INSPECTION_SECONDS = 15
DNF_INSPECTION_SECONDS = 17
FACE_SCREEN_OFFSETS = {
    "U": (4, -6),
    "F": (0, 0),
    "R": (8, 0),
}
TWO_BY_TWO_SCREEN_OFFSETS = {
    "U": (4, 0),
    "F": (4, 0),
    "R": (4, 0),
}
ROTATION_AXES = {
    "x": FACE_GEOMETRY["R"][0],
    "y": FACE_GEOMETRY["U"][0],
    "z": FACE_GEOMETRY["F"][0],
}
SLICE_AXES = {
    "M": FACE_GEOMETRY["L"][0],
    "E": FACE_GEOMETRY["D"][0],
    "S": FACE_GEOMETRY["F"][0],
}
ALGORITHM_SHORTCUTS = {
    "insert": (
        "Right F2L insert",
        ("R", "U", "R'", "U'"),
    ),
    "sune": (
        "Sune",
        ("R", "U", "R'", "U", "R", "U2", "R'"),
    ),
    "t-perm": (
        "T permutation",
        ("R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'", "U'", "R", "U", "R'", "F'"),
    ),
    "y-perm": (
        "Y permutation",
        ("F", "R", "U'", "R'", "U'", "R", "U", "R'", "F'", "R", "U", "R'", "U'", "R'", "F", "R", "F'"),
    ),
    "ua-perm": (
        "Ua edge permutation",
        ("R", "U'", "R", "U", "R", "U", "R", "U'", "R'", "U'", "R2"),
    ),
    "ub-perm": (
        "Ub edge permutation",
        ("R2", "U", "R", "U", "R'", "U'", "R'", "U'", "R'", "U", "R'"),
    ),
    "h-perm": (
        "H permutation",
        ("M2", "U", "M2", "U2", "M2", "U", "M2"),
    ),
    "z-perm": (
        "Z permutation",
        ("M'", "U", "M2", "U", "M2", "U", "M'", "U2", "M2"),
    ),
    "aa-perm": (
        "Aa corner permutation",
        ("x", "R'", "U", "R'", "D2", "R", "U'", "R'", "D2", "R2", "x'"),
    ),
    "ab-perm": (
        "Ab corner permutation",
        ("x", "R2", "D2", "R", "U", "R'", "D2", "R", "U'", "R", "x'"),
    ),
    "e-perm": (
        "E corner permutation",
        ("x'", "R", "U'", "R'", "D", "R", "U", "R'", "D'", "R", "U", "R'", "D", "R", "U'", "R'", "D'", "x"),
    ),
    "f-perm": (
        "F permutation",
        ("R'", "U'", "F'", "R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'", "U'", "R", "U", "R'", "U", "R"),
    ),
    "ja-perm": (
        "Ja adjacent corner swap",
        ("R'", "U", "L'", "U2", "R", "U'", "R'", "U2", "R", "L"),
    ),
    "jb-perm": (
        "Jb adjacent corner swap",
        ("R", "U", "R'", "F'", "R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'"),
    ),
    "na-perm": (
        "Na diagonal corner swap",
        ("L", "U'", "R", "U2", "L'", "U", "R'", "L", "U'", "R", "U2", "L'", "U", "R'"),
    ),
    "nb-perm": (
        "Nb diagonal corner swap",
        ("R'", "U", "L'", "U2", "R", "U'", "L", "R'", "U", "L'", "U2", "R", "U'", "L"),
    ),
    "ra-perm": (
        "Ra adjacent corner swap",
        ("R", "U", "R'", "F'", "R", "U2", "R'", "U2", "R'", "F", "R", "U", "R", "U2", "R'"),
    ),
    "rb-perm": (
        "Rb adjacent corner swap",
        ("R'", "U2", "R", "U2", "R'", "F", "R", "U", "R'", "U'", "R'", "F'", "R2"),
    ),
    "ga-perm": (
        "Ga permutation",
        ("R2", "U", "R'", "U", "R'", "U'", "R", "U'", "R2", "U'", "D", "R'", "U", "R", "D'"),
    ),
    "gb-perm": (
        "Gb permutation",
        ("R'", "U'", "R", "U", "D'", "R2", "U", "R'", "U", "R", "U'", "R", "U'", "R2", "D"),
    ),
    "gc-perm": (
        "Gc permutation",
        ("R2", "U'", "R", "U'", "R", "U", "R'", "U", "R2", "U", "D'", "R", "U'", "R'", "D"),
    ),
    "gd-perm": (
        "Gd permutation",
        ("R", "U", "R'", "U'", "D", "R2", "U'", "R", "U'", "R'", "U", "R'", "U", "R2", "D'"),
    ),
    "v-perm": (
        "V diagonal corner swap",
        ("R'", "U", "R'", "U'", "y", "R'", "F'", "R2", "U'", "R'", "U", "R'", "F", "R", "F"),
    ),
}
RESERVED_BIND_KEYS = frozenset("qh?")
BIND_PRESETS = {
    "numpad": {
        "*": "x",
        "+": "y",
        "/": "z",
        "1": "U'",
        "2": "D'",
        "3": "L'",
        "4": "R'",
        "5": "F'",
        "6": "B'",
        "7": "U2",
        "8": "D2",
        "9": "L2",
        "0": "R2",
        ".": "F2",
        "-": "B2",
    },
    "home": {
        "t": "U",
        "g": "D",
        "j": "L",
        "c": "R",
        "v": "F",
        "n": "B",
    },
    "practice": {
        "a": "R U R' U'",
        "p": "F R U R' U' F'",
    },
    "dev": {
        ".": "y",
        "0": "x",
        "1": "L",
        "3": "R'",
        "4": "L'",
        "5": "Rw'",
        "6": "R",
        "7": "U",
        "8": "Rw",
        "9": "U'",
        "a": "F'",
        "d": "F",
        "e": "Fw'",
        "f": "Fw",
        "s": "M",
        "w": "M'",
        "x": "S",
    },
}


def _project(point):
    x, y, z = point
    return round(26 + (x - z) * 8), round(27 + (x + z) * 4 - y * 8 + 4)


def _project_face(point, face, size=3):
    x, y = _project(point)
    offsets = TWO_BY_TWO_SCREEN_OFFSETS if size == 2 else FACE_SCREEN_OFFSETS
    offset_x, offset_y = offsets[face]
    return x + offset_x, y + offset_y


def _point_in_polygon(x, y, polygon):
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            crossing_x = (previous_x - current_x) * (y - current_y) / (
                previous_y - current_y
            ) + current_x
            if x < crossing_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def print_box(content, theme="default", color=None):
    palette = _get_theme(theme)
    if color is None:
        color = sys.stdout.isatty()
    color = color and "NO_COLOR" not in os.environ
    lines = content.splitlines() or [""]
    width = max(
        (
            len(re.sub(r"\033\[[0-9;]*m", "", line))
            for line in lines
        ),
        default=0,
    )
    border = "+" + "-" * (width + 2) + "+"
    if color:
        border_color = _theme_foreground(palette, "accent")
        print(f"{border_color}{border}{COLOR_RESET}")
    else:
        print(border)
    for index, line in enumerate(lines):
        visible_width = len(re.sub(r"\033\[[0-9;]*m", "", line))
        if color and "\033[" not in line:
            stripped = line.strip()
            is_heading = (
                index == 0
                or stripped.endswith(":")
                or (stripped and stripped.isupper())
            )
            color_name = (
                "tertiary"
                if is_heading
                else "secondary" if index % 2 else "accent"
            )
            line = f"{_theme_foreground(palette, color_name)}{line}{COLOR_RESET}"
        print(f"| {line}{' ' * (width - visible_width)} |")
    if color:
        print(f"{border_color}{border}{COLOR_RESET}")
    else:
        print(border)


def clear_terminal():
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def _get_theme(theme):
    try:
        return THEMES[_normalize_theme_name(theme)]
    except (AttributeError, KeyError) as error:
        choices = ", ".join(THEMES)
        raise ValueError(
            f"Unknown theme {theme!r}. Available themes: {choices}"
        ) from error


def _normalize_theme_name(theme):
    theme_name = theme.casefold()
    return THEME_ALIASES.get(theme_name, theme_name)


def _theme_foreground(palette, color_name):
    color = palette[color_name]
    return color if isinstance(color, str) else f"\033[38;5;{color}m"


def _append_help_panel(rendered, color=False, theme="default"):
    palette = _get_theme(theme)
    help_lines = (
        (("QUICK HELP", "title"),),
        (("Moves: U D L R F B | ' reverse | 2 half", "description"),),
        (("Wide: Rw Uw | Slices: M E S | Rotate: x y z", "description"),),
        (("Enter moves, e.g. R U R'", "description"),),
        (
            ("solve", "command"),
            (" = solve cube | ", "description"),
            ("guide", "command"),
            (" = step-by-step", "description"),
        ),
        (
            ("scramble", "command"),
            (" | ", "description"),
            ("undo", "command"),
            (" | ", "description"),
            ("redo", "command"),
        ),
        (
            ("timed", "command"),
            (" = keypress solve | ", "description"),
            ("manual", "command"),
            (" = real cube", "description"),
        ),
        (("stats", "command"), (" = averages and solve history", "description")),
        (("save/load <name>", "command"), (" | 2x2/3x3", "description")),
        (("theme <name>", "command"), (" = graphics colors", "description")),
        (("net/cube", "command"), (" = view", "description")),
        (
            ("help", "command"),
            (" = full guide | ", "description"),
            ("q", "command"),
            (" = quit", "description"),
        ),
    )
    lines = rendered.splitlines()
    content_width = max(
        (
            len(re.sub(r"\033\[[0-9;]*m", "", line))
            for line in lines
        ),
        default=0,
    )
    panel_width = max(
        sum(len(text) for text, _style in line) for line in help_lines
    )
    separator = "  |  "
    combined_lines = []
    command_color_index = 0
    for index in range(max(len(lines), len(help_lines))):
        left = lines[index] if index < len(lines) else ""
        right_segments = help_lines[index] if index < len(help_lines) else ()
        right_width = sum(len(text) for text, _style in right_segments)
        right_parts = []
        command_colors = palette.get("command_colors", (palette["accent"],))
        for text, style in right_segments:
            if color and style == "title":
                text = f"{_theme_foreground(palette, 'tertiary')}{text}\033[0m"
            elif color and style == "command":
                command_color = command_colors[
                    command_color_index % len(command_colors)
                ]
                command_color_index += 1
                command_escape = (
                    command_color
                    if isinstance(command_color, str)
                    else f"\033[38;5;{command_color}m"
                )
                text = f"{command_escape}{text}\033[0m"
            elif color and style == "description":
                text = f"{_theme_foreground(palette, 'secondary')}{text}\033[0m"
            right_parts.append(text)
        right = "".join(right_parts)
        visible_width = len(re.sub(r"\033\[[0-9;]*m", "", left))
        padding = " " * max(0, content_width - visible_width)
        right_padding = " " * (panel_width - right_width)
        combined_lines.append(f"{left}{padding}{separator}{right}{right_padding}")
    return "\n".join(combined_lines)


def _dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def _cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _rotate_clockwise(vector, axis):
    """Rotate a vector 90 degrees clockwise when viewed along the face normal."""
    cross = _cross(axis, vector)
    parallel = _dot(axis, vector)
    return tuple(axis[i] * parallel - cross[i] for i in range(3))


def _cell_position(face, row, column, size=3):
    normal, right, up = FACE_GEOMETRY[face]
    middle = (size - 1) / 2
    scale = 1 / middle if middle else 1
    return tuple(
        normal[i]
        + (column - middle) * scale * right[i]
        + (middle - row) * scale * up[i]
        for i in range(3)
    )


def _render_cell_position(face, row, column, size):
    normal, right, up = FACE_GEOMETRY[face]
    middle = (size - 1) / 2
    return tuple(
        normal[i] + (column - middle) * right[i] + (middle - row) * up[i]
        for i in range(3)
    )


def _cell_lookup(size):
    return {
        (_cell_position(face, row, column, size), FACE_GEOMETRY[face][0]): (
            face,
            row,
            column,
        )
        for face in FACE_ORDER
        for row in range(size)
        for column in range(size)
    }


CELL_LOOKUP = {
    (_cell_position(face, row, column), FACE_GEOMETRY[face][0]): (
        face,
        row,
        column,
    )
    for face in FACE_ORDER
    for row in range(3)
    for column in range(3)
}


class Cube:
    """A 2x2 or 3x3 cube whose faces contain single-letter color labels."""

    def __init__(self, size=3):
        if size not in (2, 3):
            raise ValueError("Cube size must be 2 or 3.")
        self.size = size
        self.cell_lookup = _cell_lookup(size)
        self.undo_history = []
        self.redo_history = []
        self.reset()

    def reset(self):
        """Return the cube to its solved state."""
        self.faces = {
            face: [[FACE_COLORS[face]] * self.size for _ in range(self.size)]
            for face in FACE_ORDER
        }
        self.undo_history.clear()
        self.redo_history.clear()

    def turn(self, move):
        """Apply one parsed face move (for example, R, U', or F2)."""
        match = FACE_MOVE_PATTERN.fullmatch(move)
        if match is None:
            raise ValueError(f"Invalid move: {move}")

        face = match.group(1).upper()
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        axis = FACE_GEOMETRY[face][0]
        self._turn_layers(axis, lambda position: _dot(position, axis) == 1, turns)

    def turn_wide(self, move):
        """Apply a wide turn such as Rw, rotating outer and middle layers."""
        match = WIDE_MOVE_PATTERN.fullmatch(move)
        if match is None:
            raise ValueError(f"Invalid wide move: {move}")

        face = match.group(1).upper()
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        axis = FACE_GEOMETRY[face][0]
        if self.size == 2:
            self._turn_layers(axis, lambda _position: True, turns)
        else:
            self._turn_layers(axis, lambda position: _dot(position, axis) >= 0, turns)

    def turn_slice(self, move):
        """Apply a middle-slice move using standard M, E, and S directions."""
        match = SLICE_MOVE_PATTERN.fullmatch(move)
        if match is None:
            raise ValueError(f"Invalid slice move: {move}")

        slice_name = match.group(1).upper()
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        if self.size == 2:
            equivalents = {
                "M": ("L'", "x'", "R"),
                "E": ("D'", "y'", "U"),
                "S": ("B", "z", "F'"),
            }
            sequence = equivalents[slice_name]
            if suffix == "'":
                sequence = tuple(
                    move
                    if move.endswith("2")
                    else move[:-1]
                    if move.endswith("'")
                    else move + "'"
                    for move in reversed(sequence)
                )
            repetitions = 2 if suffix == "2" else 1
            for _ in range(repetitions):
                for equivalent_move in sequence:
                    self._apply_move(equivalent_move)
            return

        axis = SLICE_AXES[slice_name]
        self._turn_layers(axis, lambda position: _dot(position, axis) == 0, turns)

    def _turn_layers(self, axis, includes_position, turns):
        for _ in range(turns):
            updated = {
                name: [row[:] for row in grid] for name, grid in self.faces.items()
            }
            for source_face in FACE_ORDER:
                for row in range(self.size):
                    for column in range(self.size):
                        position = _cell_position(
                            source_face, row, column, self.size
                        )
                        normal = FACE_GEOMETRY[source_face][0]
                        if includes_position(position):
                            position = _rotate_clockwise(position, axis)
                            normal = _rotate_clockwise(normal, axis)
                        target_face, target_row, target_column = self.cell_lookup[
                            (position, normal)
                        ]
                        updated[target_face][target_row][target_column] = self.faces[
                            source_face
                        ][row][column]
            self.faces = updated

    def apply_moves(self, moves):
        previous_faces = {
            face: [row[:] for row in grid] for face, grid in self.faces.items()
        }
        try:
            for move in moves:
                self._apply_move(move)
        except (IndexError, KeyError, TypeError, ValueError):
            self.faces = previous_faces
            raise
        if self.faces != previous_faces:
            self.undo_history.append(previous_faces)
            self.redo_history.clear()

    def _apply_move(self, move):
        if move[0] in ROTATION_AXES:
            self.rotate(move)
        elif move[0].upper() in "MES":
            self.turn_slice(move.upper())
        elif "w" in move.casefold():
            self.turn_wide(move)
        else:
            self.turn(move.upper())

    def undo(self):
        if not self.undo_history:
            return False
        self.redo_history.append(
            {face: [row[:] for row in grid] for face, grid in self.faces.items()}
        )
        self.faces = self.undo_history.pop()
        return True

    def redo(self):
        if not self.redo_history:
            return False
        self.undo_history.append(
            {face: [row[:] for row in grid] for face, grid in self.faces.items()}
        )
        self.faces = self.redo_history.pop()
        return True

    def solve(self):
        """Return a solution for the current sticker state, independent of move history."""
        if self.is_solved():
            return []

        try:
            from rubik_solver import utils as rubik_solver_utils
            from rubik_solver.CubieCube import (
                DupedCorner,
                DupedEdge,
                FlipError,
                ParityError,
                TwistError,
            )
            from rubik_solver.Solver.Kociemba.Search import (
                DupedFacelet,
                NoSolution,
                SolverTimeoutError,
            )
        except ImportError as error:
            raise RuntimeError(
                "The solver dependency is missing. Install it with "
                "'python -m pip install --no-deps -r requirements.txt'."
            ) from error

        if self.size == 3:
            color_to_face = {self.faces[face][1][1]: face for face in FACE_ORDER}
            if len(color_to_face) != len(FACE_ORDER):
                raise ValueError("The cube must have six distinct center colors.")
            solver_faces = self.faces
        else:
            color_to_face = {FACE_COLORS[face]: face for face in FACE_ORDER}
            solver_faces = self._as_three_by_three_faces()

        stickers = [
            color
            for face in FACE_ORDER
            for row in self.faces[face]
            for color in row
        ]
        if set(stickers) != set(color_to_face) or any(
            stickers.count(color) != self.size * self.size for color in color_to_face
        ):
            expected_count = "four" if self.size == 2 else "nine"
            raise ValueError(
                f"The cube must contain {expected_count} stickers of each "
                "center color."
            )
        face_to_solver_color = {
            "U": "y",
            "L": "b",
            "F": "r",
            "R": "g",
            "B": "o",
            "D": "w",
        }

        def make_facelets():
            return "".join(
                face_to_solver_color[color_to_face[color]]
                for face in ("U", "L", "F", "R", "B", "D")
                for row in solver_faces[face]
                for color in row
            )

        facelets = make_facelets()
        try:
            solver_moves = rubik_solver_utils.solve(facelets, "Kociemba")
            return parse_moves(" ".join(str(move) for move in solver_moves))
        except ParityError:
            if self.size != 2:
                raise
            self._swap_two_synthetic_edges(solver_faces)
            facelets = make_facelets()
            try:
                solver_moves = rubik_solver_utils.solve(facelets, "Kociemba")
                return parse_moves(" ".join(str(move) for move in solver_moves))
            except (
                ValueError,
                DupedCorner,
                DupedEdge,
                DupedFacelet,
                FlipError,
                NoSolution,
                ParityError,
                TwistError,
            ) as error:
                raise ValueError(f"Could not solve this cube state: {error}") from error
        except (
            ValueError,
            DupedCorner,
            DupedEdge,
            DupedFacelet,
            FlipError,
            NoSolution,
            ParityError,
            TwistError,
        ) as error:
            raise ValueError(f"Could not solve this cube state: {error}") from error
        except SolverTimeoutError as error:
            raise RuntimeError(f"The cube solver timed out: {error}") from error

    def _as_three_by_three_faces(self):
        faces = {
            face: [[FACE_COLORS[face]] * 3 for _ in range(3)]
            for face in FACE_ORDER
        }
        for face in FACE_ORDER:
            for row in range(self.size):
                for column in range(self.size):
                    target_row = row * 2
                    target_column = column * 2
                    faces[face][target_row][target_column] = self.faces[face][row][
                        column
                    ]
        return faces

    @staticmethod
    def _swap_two_synthetic_edges(faces):
        edges = {}
        for face in FACE_ORDER:
            for row in range(3):
                for column in range(3):
                    if (row, column) in ((1, 1),) or (
                        row in (0, 2) and column in (0, 2)
                    ):
                        continue
                    position = _cell_position(face, row, column)
                    edges.setdefault(position, []).append((face, row, column))

        edge_slots = [
            slots for slots in edges.values() if len(slots) == 2
        ]
        for first_index, first in enumerate(edge_slots):
            for second in edge_slots[first_index + 1 :]:
                first_faces = {slot[0] for slot in first}
                second_faces = {slot[0] for slot in second}
                shared_faces = first_faces & second_faces
                if not shared_faces:
                    continue
                first_outer = next(slot for slot in first if slot[0] not in shared_faces)
                second_outer = next(
                    slot for slot in second if slot[0] not in shared_faces
                )
                first_face, first_row, first_column = first_outer
                second_face, second_row, second_column = second_outer
                faces[first_face][first_row][first_column], faces[second_face][
                    second_row
                ][second_column] = (
                    faces[second_face][second_row][second_column],
                    faces[first_face][first_row][first_column],
                )
                return

    def rotate(self, rotation):
        """Rotate the whole cube using x, y, or z notation."""
        match = re.fullmatch(r"([xyz])([2']?)", rotation)
        if match is None:
            raise ValueError(f"Invalid cube rotation: {rotation}")

        axis = ROTATION_AXES[match.group(1)]
        suffix = match.group(2)
        turns = 2 if suffix == "2" else (3 if suffix == "'" else 1)
        for _ in range(turns):
            updated = {
                face: [[None] * self.size for _ in range(self.size)]
                for face in FACE_ORDER
            }
            for source_face in FACE_ORDER:
                for row in range(self.size):
                    for column in range(self.size):
                        position = _cell_position(
                            source_face, row, column, self.size
                        )
                        normal = FACE_GEOMETRY[source_face][0]
                        target = self.cell_lookup[
                            (
                                _rotate_clockwise(position, axis),
                                _rotate_clockwise(normal, axis),
                            )
                        ]
                        target_face, target_row, target_column = target
                        updated[target_face][target_row][target_column] = self.faces[
                            source_face
                        ][row][column]
            self.faces = updated

    def is_solved(self):
        return all(
            all(color == grid[0][0] for row in grid for color in row)
            for grid in self.faces.values()
        )

    def _render_cube(self, theme="default"):
        """Draw three offset isometric faces with visible gaps between them."""
        palette = _get_theme(theme)
        pixels = [[" " for _ in range(RENDER_SIZE)] for _ in range(RENDER_SIZE)]
        for face in ("U", "F", "R"):
            _normal, right, up = FACE_GEOMETRY[face]
            for row in range(self.size):
                for column in range(self.size):
                    center = _render_cell_position(
                        face, row, column, self.size
                    )
                    corners = [
                        _project_face(
                            tuple(
                                center[index]
                                + right_sign * right[index]
                                + up_sign * up[index]
                                for index in range(3)
                            ),
                            face,
                            self.size,
                        )
                        for right_sign, up_sign in (
                            (-0.5, -0.5),
                            (0.5, -0.5),
                            (0.5, 0.5),
                            (-0.5, 0.5),
                        )
                    ]
                    min_x = max(0, min(point[0] for point in corners))
                    max_x = min(RENDER_SIZE - 1, max(point[0] for point in corners))
                    min_y = max(0, min(point[1] for point in corners))
                    max_y = min(RENDER_SIZE - 1, max(point[1] for point in corners))
                    for y in range(min_y, max_y + 1):
                        for x in range(min_x, max_x + 1):
                            if _point_in_polygon(x + 0.5, y + 0.5, corners):
                                pixels[y][x] = "edge"

        for face in ("U", "F", "R"):
            _normal, right, up = FACE_GEOMETRY[face]
            for row in range(self.size):
                for column in range(self.size):
                    center = _render_cell_position(
                        face, row, column, self.size
                    )
                    corners = []
                    for right_sign, up_sign in (
                        (-0.38, -0.38),
                        (0.38, -0.38),
                        (0.38, 0.38),
                        (-0.38, 0.38),
                    ):
                        point = tuple(
                            center[index]
                            + right_sign * right[index]
                            + up_sign * up[index]
                            for index in range(3)
                        )
                        corners.append(_project_face(point, face, self.size))

                    min_x = max(0, min(point[0] for point in corners))
                    max_x = min(RENDER_SIZE - 1, max(point[0] for point in corners))
                    min_y = max(0, min(point[1] for point in corners))
                    max_y = min(RENDER_SIZE - 1, max(point[1] for point in corners))
                    color = self.faces[face][row][column]
                    for y in range(min_y, max_y + 1):
                        for x in range(min_x, max_x + 1):
                            if _point_in_polygon(x + 0.5, y + 0.5, corners):
                                pixels[y][x] = color

        lines = ["3D view: U top | F front | R right"]
        for y in range(0, RENDER_SIZE, 2):
            rendered_row = []
            for x in range(RENDER_SIZE):
                top_pixel = pixels[y][x]
                bottom_pixel = (
                    pixels[y + 1][x] if y + 1 < RENDER_SIZE else " "
                )
                top = top_pixel if top_pixel not in (" ", "edge") else None
                bottom = (
                    bottom_pixel if bottom_pixel not in (" ", "edge") else None
                )
                if top_pixel == "edge" and bottom_pixel == "edge":
                    rendered_row.append(f"\033[48;5;{palette['edge']}m \033[0m")
                elif top_pixel == "edge" and bottom is not None:
                    rendered_row.append(
                        f"\033[38;5;{palette['stickers'][bottom]};"
                        f"48;5;{palette['edge']}m▄\033[0m"
                    )
                elif bottom_pixel == "edge" and top is not None:
                    rendered_row.append(
                        f"\033[38;5;{palette['stickers'][top]};"
                        f"48;5;{palette['edge']}m▀\033[0m"
                    )
                elif top is None and bottom is None:
                    rendered_row.append(" ")
                elif top is None:
                    rendered_row.append(
                        f"\033[38;5;{palette['stickers'][bottom]}m▄\033[0m"
                    )
                elif bottom is None:
                    rendered_row.append(
                        f"\033[38;5;{palette['stickers'][top]}m▀\033[0m"
                    )
                else:
                    rendered_row.append(
                        f"\033[38;5;{palette['stickers'][top]};"
                        f"48;5;{palette['stickers'][bottom]}m▀\033[0m"
                    )
            lines.append("".join(rendered_row).rstrip())
        return "\n".join(lines)

    def render(self, color=True, view="cube", show_help=False, theme="default"):
        """Render a perspective cube or the full unfolded net."""
        palette = _get_theme(theme)
        theme_name = _normalize_theme_name(theme)
        if view == "cube" and color:
            rendered = self._render_cube(theme)
            return (
                _append_help_panel(rendered, color, theme)
                if show_help
                else rendered
            )

        def tile(label):
            if color:
                background = (
                    COLOR_CODES[label]
                    if theme_name in ("default", "rubiks")
                    else f"\033[48;5;{palette['stickers'][label]}m"
                )
                return f"{background}   {COLOR_RESET}"
            return f" {label} "

        def render_face_row(row):
            return " ".join(tile(label) for label in row)

        if view not in ("cube", "net"):
            raise ValueError("View must be 'cube' or 'net'.")

        lines = ["       U"]
        lines.extend(f"      {render_face_row(row)}" for row in self.faces["U"])
        face_width = self.size * 4 - 1
        face_labels = " | ".join(
            face.center(face_width) for face in ("L", "F", "R", "B")
        )
        lines.append("   " + face_labels)
        for row in range(self.size):
            sides = [
                render_face_row(self.faces[face][row])
                for face in ("L", "F", "R", "B")
            ]
            lines.append("   " + " | ".join(sides))
        lines.append("       D")
        lines.extend(f"      {render_face_row(row)}" for row in self.faces["D"])
        rendered = "\n".join(lines)
        return (
            _append_help_panel(rendered, color, theme)
            if show_help
            else rendered
        )


def parse_moves(text):
    """Parse face, wide, slice, and whole-cube rotation notation."""
    tokens = text.split()
    if not tokens:
        raise ValueError("Enter at least one move.")

    moves = []
    for token in tokens:
        rotation_match = re.fullmatch(r"([xyz])([2']?)", token)
        wide_match = WIDE_MOVE_PATTERN.fullmatch(token)
        face_match = FACE_MOVE_PATTERN.fullmatch(token)
        slice_match = SLICE_MOVE_PATTERN.fullmatch(token)
        match = rotation_match or face_match or wide_match or slice_match
        if match is None:
            raise ValueError(
                f"Invalid move {token!r}. Use U/D/L/R/F/B face turns (case "
                "does not matter), moves such as Rw/Uw for wide turns, M/E/S "
                "slice turns, or x/y/z rotations, optionally followed by ' or 2."
            )
        if rotation_match is not None:
            move = match.group(1) + match.group(2)
        elif wide_match is not None:
            move = match.group(1).upper() + "w" + match.group(2)
        elif face_match is not None:
            move = match.group(1).upper() + match.group(2)
        else:
            move = match.group(1).upper() + match.group(2)
        moves.append(move)
    return moves


def parse_bound_moves(text, keybinds):
    """Parse move notation and expand any user-defined key aliases."""
    moves = []
    for token in text.split():
        binding = keybinds.get(token.casefold())
        moves.extend(binding if binding is not None else parse_moves(token))
    if not moves:
        raise ValueError("Enter at least one move.")
    return moves


def timed_key_moves(key, keybinds):
    """Return moves for one timed-solve key, or an empty list if it is unmapped."""
    binding = keybinds.get(key.casefold())
    if binding is not None:
        return binding
    try:
        return parse_moves(key)
    except ValueError:
        return []


def timed_key_from_scan_code(scan_code):
    """Translate numpad navigation scan codes to their numpad key labels."""
    return {
        "G": "7",
        "H": "8",
        "I": "9",
        "K": "4",
        "M": "6",
        "O": "1",
        "P": "2",
        "Q": "3",
        "R": "0",
        "S": ".",
    }.get(scan_code.upper())


def set_keybind(keybinds, key, moves_text):
    """Bind one printable key to a valid move or move sequence."""
    normalized_key = key.casefold()
    if (
        len(key) != 1
        or not key.isascii()
        or not key.isprintable()
        or key.isspace()
        or normalized_key in RESERVED_BIND_KEYS
    ):
        raise ValueError(
            "Choose one printable key that is not reserved for help or quit."
        )
    moves = parse_moves(moves_text)
    keybinds[normalized_key] = moves
    return moves


def print_binds(keybinds, theme="default"):
    """Display active aliases and available built-in presets."""
    lines = ["Custom keybinds (these last for this run):"]
    if not keybinds:
        lines.append("  None")
    else:
        for key, moves in sorted(keybinds.items()):
            lines.append(f"  {key} -> {' '.join(moves)}")
    lines.extend(_bind_preset_lines())
    print_box("\n".join(lines), theme)


def print_bind_presets(theme="default"):
    print_box("\n".join(_bind_preset_lines()), theme)


def _bind_preset_lines():
    lines = ["Presets (apply with: bind preset <name>):"]
    for name, bindings in BIND_PRESETS.items():
        lines.append(
            f"  {name}: "
            + ", ".join(f"{key} -> {moves}" for key, moves in bindings.items())
        )
    return lines


def apply_bind_preset(keybinds, name):
    """Merge a named built-in preset into the active custom key aliases."""
    preset = BIND_PRESETS.get(name.casefold())
    if preset is None:
        choices = ", ".join(BIND_PRESETS)
        raise ValueError(f"Unknown bind preset {name!r}. Available: {choices}")
    validated = {}
    for key, moves in preset.items():
        set_keybind(validated, key, moves)
    keybinds.update(validated)
    return validated


def print_algorithms(theme="default"):
    """Display the available named algorithm shortcuts and their sequences."""
    lines = ["Available algorithm shortcuts (run with: alg <name>):"]
    for name, (description, sequence) in ALGORITHM_SHORTCUTS.items():
        lines.append(f"  {name:<8} {description}: {' '.join(sequence)}")
    print_box("\n".join(lines), theme)


def apply_algorithm(cube, name):
    """Apply a named algorithm shortcut to a cube."""
    key = name.casefold()
    try:
        _description, sequence = ALGORITHM_SHORTCUTS[key]
    except KeyError as error:
        choices = ", ".join(ALGORITHM_SHORTCUTS)
        raise ValueError(f"Unknown algorithm {name!r}. Available: {choices}") from error
    cube.apply_moves(sequence)


def scramble(cube, length=20):
    """Apply and return a random sequence without consecutive same-face turns."""
    moves = []
    previous_face = None
    suffixes = ("", "'", "2")
    for _ in range(length):
        face = random.choice([face for face in "UDLRFB" if face != previous_face])
        move = face + random.choice(suffixes)
        moves.append(move)
        previous_face = face
    cube.apply_moves(moves)
    return moves


def _validate_solve_records(records):
    if not isinstance(records, list) or any(
        not isinstance(record, dict)
        or isinstance(record.get("time"), bool)
        or not isinstance(record.get("time"), (int, float))
        or not math.isfinite(record["time"])
        or record["time"] < 0
        or not isinstance(record.get("scramble"), str)
        or record.get("penalty", "none") not in ("none", "+2", "DNF")
        or record.get("mode", "virtual") not in ("virtual", "manual")
        or isinstance(record.get("size", 3), bool)
        or not isinstance(record.get("size", 3), int)
        or record.get("size", 3) not in (2, 3)
        for record in records
    ):
        raise ValueError("Solve history has an invalid format.")


def load_solve_records(path=SOLVE_RECORDS_PATH):
    try:
        with Path(path).open(encoding="utf-8") as records_file:
            records = json.load(records_file)
    except FileNotFoundError:
        return []
    _validate_solve_records(records)
    return records


def write_solve_records(records, path=SOLVE_RECORDS_PATH):
    _validate_solve_records(records)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as records_file:
        json.dump(records, records_file, indent=2)
        records_file.write("\n")


def clear_solve_records(path=SOLVE_RECORDS_PATH):
    write_solve_records([], path)


def save_solve_record(
    scramble_moves,
    elapsed,
    path=SOLVE_RECORDS_PATH,
    penalty="none",
    mode="virtual",
    size=3,
):
    if penalty not in ("none", "+2", "DNF"):
        raise ValueError("Penalty must be 'none', '+2', or 'DNF'.")
    if mode not in ("virtual", "manual"):
        raise ValueError("Solve mode must be 'virtual' or 'manual'.")
    if isinstance(size, bool) or not isinstance(size, int) or size not in (2, 3):
        raise ValueError("Cube size must be 2 or 3.")
    if not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("Solve time must be a non-negative finite number.")
    path = Path(path)
    records = load_solve_records(path)
    record = {
        "time": elapsed,
        "penalty": penalty,
        "scramble": " ".join(scramble_moves),
        "mode": mode,
        "size": size,
    }
    records.append(record)
    write_solve_records(records, path)
    return record


def parse_solve_time(value):
    try:
        if ":" in value:
            minutes_text, seconds_text = value.split(":", maxsplit=1)
            if not minutes_text.isdecimal():
                raise ValueError
            seconds_part = float(seconds_text)
            if not 0 <= seconds_part < 60:
                raise ValueError
            seconds = int(minutes_text) * 60 + seconds_part
        else:
            seconds = float(value)
    except ValueError as error:
        raise ValueError(
            "Enter a time in seconds or M:SS.ss format, such as 12.34 or 1:02.34."
        ) from error
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Solve time must be a non-negative finite number.")
    return seconds


def edit_solve_record(records, number, field, value):
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(records):
        raise ValueError(f"Solve number must be between 1 and {len(records)}.")
    record = records[number - 1]
    field = field.casefold()
    if field == "time":
        record["time"] = parse_solve_time(value)
    elif field == "penalty":
        penalty = value.upper() if value.casefold() == "dnf" else value
        if penalty not in ("none", "+2", "DNF"):
            raise ValueError("Penalty must be none, +2, or DNF.")
        record["penalty"] = penalty
    elif field == "scramble":
        moves = parse_moves(value)
        record["scramble"] = " ".join(moves)
    else:
        raise ValueError("Editable fields are time, penalty, and scramble.")
    _validate_solve_records(records)
    return record


def delete_solve_record(records, number):
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(records):
        raise ValueError(f"Solve number must be between 1 and {len(records)}.")
    return records.pop(number - 1)


def _validate_cube_faces(size, faces):
    if size not in (2, 3) or not isinstance(faces, dict) or set(faces) != set(FACE_ORDER):
        raise ValueError("Cube state has an invalid size or face list.")
    stickers = []
    for face in FACE_ORDER:
        grid = faces[face]
        if (
            not isinstance(grid, list)
            or len(grid) != size
            or any(
                not isinstance(row, list)
                or len(row) != size
                or any(not isinstance(color, str) for color in row)
                for row in grid
            )
        ):
            raise ValueError("Cube state has an invalid face layout.")
        stickers.extend(color for row in grid for color in row)
    colors = set(FACE_COLORS.values())
    if set(stickers) != colors or any(
        stickers.count(color) != size * size for color in colors
    ):
        raise ValueError("Cube state has invalid sticker colors or counts.")
    if size == 3 and len({faces[face][1][1] for face in FACE_ORDER}) != len(FACE_ORDER):
        raise ValueError("Cube state must have six distinct center colors.")


def _cube_state_path(name, directory=CUBE_STATES_PATH):
    if not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name) is None:
        raise ValueError("Choose a state name using 1-40 letters, numbers, _ or -.")
    return Path(directory) / f"{name}.json"


def save_cube_state(cube, name, directory=CUBE_STATES_PATH):
    _validate_cube_faces(cube.size, cube.faces)
    path = _cube_state_path(name, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as state_file:
        json.dump({"size": cube.size, "faces": cube.faces}, state_file, indent=2)
        state_file.write("\n")
    return path


def load_cube_state(name, directory=CUBE_STATES_PATH):
    path = _cube_state_path(name, directory)
    try:
        with path.open(encoding="utf-8") as state_file:
            state = json.load(state_file)
    except FileNotFoundError as error:
        raise ValueError(f"No saved cube state named {name!r}.") from error
    if (
        not isinstance(state, dict)
        or isinstance(state.get("size"), bool)
        or not isinstance(state.get("size"), int)
        or "faces" not in state
    ):
        raise ValueError("Saved cube state has an invalid format.")
    _validate_cube_faces(state["size"], state["faces"])
    cube = Cube(state["size"])
    cube.faces = state["faces"]
    return cube


def calculate_averages(records):
    def effective_time(record):
        if record.get("penalty", "none") == "DNF":
            return math.inf
        return record["time"] + (2 if record.get("penalty") == "+2" else 0)

    times = [effective_time(record) for record in records]

    def rolling_average(size):
        if len(times) < size:
            return None
        window = sorted(times[-size:])
        trim = 1 if size < 100 else size // 20
        counted_times = window[trim:-trim]
        if any(math.isinf(seconds) for seconds in counted_times):
            return math.inf
        return sum(counted_times) / len(counted_times)

    finite_times = [seconds for seconds in times if math.isfinite(seconds)]
    return {
        "ao5": rolling_average(5),
        "ao12": rolling_average(12),
        "ao100": rolling_average(100),
        "all_time": (
            sum(finite_times) / len(finite_times) if finite_times else None
        ),
        "best": min(finite_times) if finite_times else None,
    }


def format_time(seconds):
    total_centiseconds = round(seconds * 100)
    minutes, remaining_centiseconds = divmod(total_centiseconds, 6000)
    whole_seconds, centiseconds = divmod(remaining_centiseconds, 100)
    return f"{minutes}:{whole_seconds:02}.{centiseconds:02}"


def print_averages(records, session_records=None, theme="default"):
    print_box("\n".join(format_averages(records, session_records)), theme)


def format_averages(records, session_records=None):
    if not records:
        return ["No solves recorded yet."]

    session_records = session_records or []
    lines = ["Solve averages (trimmed rolling averages):"]
    for size in (3, 2):
        for mode in ("virtual", "manual"):
            group_records = [
                (number, record)
                for number, record in enumerate(records, start=1)
                if record.get("size", 3) == size
                and record.get("mode", "virtual") == mode
            ]
            group_session_records = [
                record
                for record in session_records
                if record.get("size", 3) == size
                and record.get("mode", "virtual") == mode
            ]
            averages = calculate_averages(
                [record for _number, record in group_records]
            )
            solve_type = "timed" if mode == "virtual" else "manual"
            lines.append(f"  {size}x{size} {solve_type} solves:")
            for label, key, required in (
                ("Average of 5", "ao5", 5),
                ("Average of 12", "ao12", 12),
                ("Average of 100", "ao100", 100),
            ):
                average = averages[key]
                result = (
                    "DNF"
                    if average is not None and math.isinf(average)
                    else format_time(average)
                    if average is not None
                    else f"N/A (need {required})"
                )
                lines.append(f"    {label}: {result}")
            best = averages["best"]
            all_time = averages["all_time"]
            lines.append(
                f"    Personal best: {format_time(best) if best is not None else 'N/A'}"
            )
            lines.append(
                f"    All-time average: {format_time(all_time) if all_time is not None else 'N/A'}"
            )
            if session_records:
                session_average = calculate_averages(
                    group_session_records
                )["all_time"]
                lines.append(
                    "    Session average: "
                    f"{format_time(session_average) if session_average is not None else 'N/A'}"
                )
            if group_records:
                lines.append("    Solve history:")
                for number, record in group_records:
                    penalty = record.get("penalty", "none")
                    result = "DNF" if penalty == "DNF" else format_time(
                        record["time"] + (2 if penalty == "+2" else 0)
                    )
                    details = (
                        "Manual solve"
                        if record.get("mode") == "manual"
                        else record["scramble"]
                    )
                    lines.append(f"      {number}. {result} ({penalty})  {details}")
            else:
                lines.append("    No solves recorded.")
    return lines


def run_stats_menu(path=SOLVE_RECORDS_PATH, session_records=None, theme="default"):
    session_records = session_records if session_records is not None else []
    try:
        records = load_solve_records(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Could not read solve history: {error}")
        return
    session_start = max(0, len(records) - len(session_records))

    while True:
        lines = format_averages(records, session_records)
        if not records:
            lines.append("  No solves to edit yet.")
        lines.append(
            "Commands: edit <number> <time|penalty|scramble> <value> | "
            "delete <number> | clear | back"
        )
        print_box("\n".join(lines), theme)
        try:
            entry = input("stats> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        parts = entry.split(maxsplit=3)
        command = parts[0].casefold() if parts else ""
        if command in ("back", "return", "q"):
            return
        if command == "clear":
            if len(parts) != 1:
                print("Usage: clear")
                continue
            if not records:
                print("There are no solves to clear.")
                continue
            try:
                confirmation = input(
                    f"Clear all {len(records)} solves? Type yes to confirm: "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nClear canceled.")
                continue
            if confirmation.casefold() != "yes":
                print("Clear canceled.")
                continue
            try:
                clear_solve_records(path)
            except OSError as error:
                print(f"Could not clear solve history: {error}")
                continue
            records.clear()
            session_records.clear()
            session_start = 0
            print("All solve records cleared.")
            continue
        if command == "edit":
            if len(parts) != 4 or not parts[1].isdecimal():
                print("Usage: edit <number> <time|penalty|scramble> <value>")
                continue
            number = int(parts[1])
            try:
                updated = edit_solve_record(
                    records, number, parts[2], parts[3]
                )
                write_solve_records(records, path)
            except (OSError, ValueError) as error:
                print(f"Could not edit solve: {error}")
                records = load_solve_records(path)
                continue
            if number > session_start:
                session_records[number - session_start - 1] = updated.copy()
            print(f"Updated solve {number}.")
            continue
        if command == "delete":
            if len(parts) != 2 or not parts[1].isdecimal():
                print("Usage: delete <number>")
                continue
            number = int(parts[1])
            if not 1 <= number <= len(records):
                print(f"Solve number must be between 1 and {len(records)}.")
                continue
            try:
                confirmation = input(
                    f"Delete solve {number}? Type yes to confirm: "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nDeletion canceled.")
                continue
            if confirmation.casefold() != "yes":
                print("Deletion canceled.")
                continue
            delete_solve_record(records, number)
            try:
                write_solve_records(records, path)
            except OSError as error:
                print(f"Could not save solve history: {error}")
                records = load_solve_records(path)
                continue
            if number <= session_start:
                session_start -= 1
            else:
                del session_records[number - session_start - 1]
            print(f"Deleted solve {number}.")
            continue
        print("Use edit, delete, clear, or back.")


def inspection_penalty(seconds):
    if seconds >= DNF_INSPECTION_SECONDS:
        return "DNF"
    if seconds >= INSPECTION_SECONDS:
        return "+2"
    return "none"


def run_speed_timer():
    """Run the interactive Windows console timer and return time and penalty."""
    import msvcrt

    inspection_started = time.perf_counter()
    print(
        f"Inspection: press SPACE to start "
        f"({INSPECTION_SECONDS}s; +2 after, DNF after {DNF_INSPECTION_SECONDS}s)."
    )
    last_display = None
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key == " ":
                penalty = inspection_penalty(time.perf_counter() - inspection_started)
                break
        elapsed_inspection = time.perf_counter() - inspection_started
        if elapsed_inspection < INSPECTION_SECONDS:
            display = f"Inspection: {INSPECTION_SECONDS - int(elapsed_inspection):2d}s"
        elif elapsed_inspection < DNF_INSPECTION_SECONDS:
            display = "Inspection: +2"
        else:
            display = "Inspection: DNF"
        if display != last_display:
            print(f"\r{display} ", end="", flush=True)
            last_display = display
        time.sleep(0.01)

    print("\nSolve: press SPACE to stop.")
    started = time.perf_counter()
    last_display = None
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key == " ":
                elapsed = time.perf_counter() - started
                break
        display = format_time(time.perf_counter() - started)
        if display != last_display:
            print(f"\r{display}", end="", flush=True)
            last_display = display
        time.sleep(0.01)
    print()
    return elapsed, penalty


def describe_move(move):
    face_names = {
        "U": "up",
        "D": "down",
        "L": "left",
        "R": "right",
        "F": "front",
        "B": "back",
    }
    if move[0] in "xyz":
        axis = {"x": "left/right", "y": "up/down", "z": "front/back"}[move[0]]
        action = "half-turn" if move.endswith("2") else (
            "counterclockwise turn" if move.endswith("'") else "clockwise turn"
        )
        return f"Rotate the whole cube around the {axis} axis: {action}."
    face = move[0].upper()
    if face in face_names:
        target = f"{face_names[face]} face"
        if "w" in move.casefold():
            target = f"{face_names[face]} face and its adjacent layer"
    elif face in "MES":
        target = {"M": "middle vertical slice", "E": "middle horizontal slice", "S": "middle front-to-back slice"}[face]
    else:
        target = "slice"
    action = "half-turn" if move.endswith("2") else (
        "counterclockwise turn" if move.endswith("'") else "clockwise turn"
    )
    return f"Turn the {target}: {action}."


def print_help(theme="default"):
    palette = _get_theme(theme)
    content = (
        "MOVES\n"
        "  Enter turns separated by spaces, for example: R U R' U'\n"
        "  Faces: U up, D down, L left, R right, F front, B back\n"
        "  Uppercase and lowercase face turns are the same.\n"
        "  Wide turns use w: Rw, Uw, Lw. Slices: M, E, S.\n"
        "  Rotate the whole cube with x, y, or z. Turns follow the current view.\n"
        "  Add ' for a counterclockwise turn or 2 for a half-turn.\n"
        "\n"
        "COMMANDS\n"
        "SOLVING\n"
        "  scramble      Randomize the cube\n"
        "  timed         Scramble virtual cube; timer stops when solved\n"
        "                Press move/bind keys directly; Esc cancels\n"
        "  manual        Timer-only mode for solving a physical cube\n"
        "  cancel timer  Cancel an active virtual timed solve\n"
        "  solve         Solve the current cube from its sticker state\n"
        "  guide         Follow a move-by-move guided solution\n"
        "  algorithms    List algorithm shortcuts\n"
        "  alg <name>    Run an algorithm shortcut\n"
        "\n"
        "CUBE AND DISPLAY\n"
        "  2x2 / 3x3     Switch cube size (starts a solved cube)\n"
        "  save <name>   Save the current cube state\n"
        "  load <name>   Load a saved cube state\n"
        "  theme <name>  Change graphics colors; use themes to list options\n"
        "  themes        List available graphics themes\n"
        "  net / cube    Change the display view\n"
        "  The 3D view shows the top, front, and right faces; net shows all faces.\n"
        "  Tile colors: white, yellow, green, blue, red, orange.\n"
        "\n"
        "BINDINGS\n"
        "  bind <key> <moves>  Bind a key to one move or a move sequence\n"
        "  binds         Show custom keybinds and available presets\n"
        "  bind presets  List built-in bind presets\n"
        "  bind preset <name>  Apply a preset (numpad, home, practice, dev)\n"
        "  clear binds   Remove custom keybinds\n"
        "\n"
        "STATISTICS AND HISTORY\n"
        "  stats         View averages by size/mode and edit solve history\n"
        "  undo / redo   Reverse or restore the last move sequence\n"
        "\n"
        "GENERAL\n"
        "  help          Show this help\n"
        "  quit          Exit the program"
    )
    use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    if use_color:
        sections = {
            "MOVES",
            "COMMANDS",
            "SOLVING",
            "CUBE AND DISPLAY",
            "BINDINGS",
            "STATISTICS AND HISTORY",
            "GENERAL",
        }
        command_colors = palette.get(
            "command_colors", (palette["accent"], palette["secondary"])
        )
        command_color_index = 0
        colored_lines = []
        for line in content.splitlines():
            if line in sections:
                colored_lines.append(
                    f"\033[1m{_theme_foreground(palette, 'tertiary')}{line}\033[0m"
                )
                continue
            command = re.match(r"^  (\S.*?)( {2,})(.+)$", line)
            if command is not None:
                name, separator, description = command.groups()
                command_color = command_colors[
                    command_color_index % len(command_colors)
                ]
                if isinstance(command_color, str):
                    command_escape = command_color
                else:
                    command_escape = f"\033[38;5;{command_color}m"
                command_color_index += 1
                colored_lines.append(
                    f"  {command_escape}"
                    f"{name}\033[0m"
                    f"{separator}{description}"
                )
            else:
                colored_lines.append(line)
        content = "\n".join(colored_lines)
    print_box(content, theme, color=use_color)


def print_themes(current=None, theme="default"):
    lines = ["Graphics themes (apply with: theme <name>):"]
    for theme_name, palette in THEMES.items():
        active = " (current)" if theme_name == current else ""
        description = palette["name"]
        if sys.stdout.isatty() and "NO_COLOR" not in os.environ:
            colors = tuple(
                dict.fromkeys(
                    color
                    for sticker, color in palette["stickers"].items()
                    if sticker != "W"
                )
            )
            colored_description = []
            color_index = 0
            for character in description:
                if character.isspace():
                    colored_description.append(character)
                    continue
                color_code = colors[color_index % len(colors)]
                colored_description.append(
                    f"\033[38;5;{color_code}m{character}{COLOR_RESET}"
                )
                color_index += 1
            description = "".join(colored_description)
        lines.append(f"  {theme_name:<18} {description}{active}")
    print_box("\n".join(lines), theme)


def _solved_banner(color, theme="default"):
    border = "+" + "-" * 38 + "+"
    title = "|" + "THE CUBE IS SOLVED!".center(38) + "|"
    if color:
        border_color, title_color, bottom_color = _get_theme(theme)["banner"]
        return "\n".join(
            (
                f"\033[38;5;{border_color}m{border}{COLOR_RESET}",
                f"\033[38;5;{title_color}m{title}{COLOR_RESET}",
                f"\033[38;5;{bottom_color}m{border}{COLOR_RESET}",
            )
        )
    return "\n".join((border, title, border))


def main():
    cube = Cube()
    display = "cube"
    theme = "default"
    keybinds = {}
    session_records = []
    virtual_attempt = None
    print("Virtual Rubik's Cube")

    def finish_virtual_attempt():
        nonlocal virtual_attempt
        if virtual_attempt is None or not cube.is_solved():
            return
        elapsed = time.perf_counter() - virtual_attempt["started_at"]
        scramble_moves = virtual_attempt["scramble"]
        virtual_attempt = None
        try:
            record = save_solve_record(
                scramble_moves,
                elapsed,
                SOLVE_RECORDS_PATH,
                penalty="none",
                mode="virtual",
                size=cube.size,
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Solved in {format_time(elapsed)}, but the result was not saved: {error}")
        else:
            session_records.append(record)
            print(f"Virtual timed solve: {format_time(elapsed)}. Result saved.")

    def run_virtual_attempt_input():
        nonlocal virtual_attempt
        try:
            import msvcrt
        except ImportError as error:
            virtual_attempt = None
            print(f"Virtual timer canceled; instant key input is unavailable: {error}")
            return True

        print("Timed solve: press move/bind keys; Esc cancels; q quits.")
        while virtual_attempt is not None:
            try:
                key = msvcrt.getwch()
            except KeyboardInterrupt:
                clear_terminal()
                print("\nGoodbye!")
                return False

            if key in ("\x00", "\xe0"):
                key = timed_key_from_scan_code(msvcrt.getwch())
                if key is None:
                    continue
            elif key == "\x1b":
                virtual_attempt = None
                print("Virtual timed solve canceled; result not recorded.")
                return True
            elif key.casefold() == "q":
                clear_terminal()
                print("\nGoodbye!")
                return False

            moves = timed_key_moves(key, keybinds)
            if moves:
                cube.apply_moves(moves)
                finish_virtual_attempt()
                print(f"{key} -> {' '.join(moves)}", flush=True)
                use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
                print(
                    cube.render(
                        color=use_color, view=display, show_help=True, theme=theme
                    ),
                    flush=True,
                )
        return True

    def select_penalty(inspection_result):
        penalty_rank = {"none": 0, "+2": 1, "DNF": 2}
        while True:
            try:
                choice = input("Penalty [none/+2/DNF] (Enter for none): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nNo penalty entered; using inspection result.")
                return inspection_result
            choice = choice or "none"
            if choice not in penalty_rank:
                print("Enter none, +2, or DNF.")
                continue
            return max(
                (inspection_result, choice),
                key=lambda penalty: penalty_rank[penalty],
            )

    while True:
        if virtual_attempt is not None:
            if not run_virtual_attempt_input():
                break
            continue

        print()
        use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        print(
            cube.render(
                color=use_color, view=display, show_help=True, theme=theme
            )
        )
        if cube.is_solved():
            print(f"\n{_solved_banner(use_color, theme)}")

        try:
            entry = input("\nMove(s) or command: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        command = entry.casefold()
        if command in ("quit", "exit", "q"):
            clear_terminal()
            print("Goodbye!")
            break
        if command in ("theme", "themes"):
            print_themes(theme, theme)
            continue
        if command.startswith("theme "):
            requested_theme = entry.split(maxsplit=1)[1]
            try:
                _get_theme(requested_theme)
            except ValueError as error:
                print(error)
            else:
                theme = _normalize_theme_name(requested_theme)
                print(f"Graphics theme set to {THEMES[theme]['name']}.")
            continue
        if command in ("help", "h", "?"):
            print_help(theme)
            continue
        if command == "binds":
            print_binds(keybinds, theme)
            continue
        if command in ("clear binds", "reset binds"):
            keybinds.clear()
            print("Custom keybinds reset.")
            continue
        if command == "bind" or command.startswith("bind "):
            parts = entry.split(maxsplit=2)
            if len(parts) == 2 and parts[1].casefold() == "presets":
                print_bind_presets(theme)
                continue
            if (
                len(parts) == 3
                and parts[1].casefold() == "preset"
            ):
                try:
                    applied = apply_bind_preset(keybinds, parts[2])
                except ValueError as error:
                    print(error)
                else:
                    print(
                        f"Applied {parts[2].casefold()} preset "
                        f"({len(applied)} bindings). Existing keys in the "
                        "preset were replaced; other bindings were kept."
                    )
                continue
            if len(parts) != 3:
                print(
                    "Usage: bind <key> <move sequence>, "
                    "bind presets, or bind preset <name>"
                )
                continue
            try:
                moves = set_keybind(keybinds, parts[1], parts[2])
            except ValueError as error:
                print(error)
            else:
                print(f"Bound {parts[1]} to {' '.join(moves)}.")
            continue
        if command == "algorithms":
            print_algorithms(theme)
            continue
        if command.startswith("alg "):
            name = command[4:].strip()
            if not name:
                print("Usage: alg <name>. Type algorithms to list shortcuts.")
                continue
            try:
                apply_algorithm(cube, name)
            except ValueError as error:
                print(error)
            finish_virtual_attempt()
            continue
        if command == "timed":
            if virtual_attempt is not None:
                print("A virtual timed solve is already active.")
                continue
            if not cube.is_solved():
                print("Solve the current cube before starting a timed solve.")
                continue
            scramble_moves = scramble(cube)
            print("Scramble:", " ".join(scramble_moves))
            print(
                cube.render(
                    color=use_color, view=display, show_help=True, theme=theme
                )
            )
            virtual_attempt = {
                "scramble": scramble_moves,
                "started_at": time.perf_counter(),
            }
            print("Virtual timer started. Press move/bind keys to solve the cube.")
            continue
        if command in ("manual", "timed manual"):
            if virtual_attempt is not None:
                print("Cancel the active virtual timer before starting manual mode.")
                continue
            try:
                elapsed, inspection_result = run_speed_timer()
            except (ImportError, OSError, KeyboardInterrupt) as error:
                print(f"Manual timer canceled: {error or 'interrupted'}.")
                continue
            penalty = select_penalty(inspection_result)
            try:
                record = save_solve_record(
                    [],
                    elapsed,
                    SOLVE_RECORDS_PATH,
                    penalty,
                    mode="manual",
                    size=cube.size,
                )
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(
                    f"Manual time {format_time(elapsed)}; result was not saved: {error}"
                )
            else:
                session_records.append(record)
                result = (
                    "DNF"
                    if penalty == "DNF"
                    else format_time(elapsed + (2 if penalty == "+2" else 0))
                )
                print(f"Manual solve time: {result}. Result saved.")
            continue
        if command == "cancel timer":
            if virtual_attempt is None:
                print("No virtual timed solve is active.")
            else:
                virtual_attempt = None
                print("Virtual timed solve canceled; result not recorded.")
            continue
        if command in ("average", "stats"):
            run_stats_menu(SOLVE_RECORDS_PATH, session_records, theme)
            continue
        if command == "undo":
            if cube.undo():
                print("Undid the last move sequence.")
                finish_virtual_attempt()
            else:
                print("Nothing to undo.")
            continue
        if command == "redo":
            if cube.redo():
                print("Redid the last undone move sequence.")
                finish_virtual_attempt()
            else:
                print("Nothing to redo.")
            continue
        if command == "save" or command.startswith("save "):
            parts = entry.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: save <name>")
                continue
            try:
                path = save_cube_state(cube, parts[1])
            except (OSError, ValueError) as error:
                print(f"Could not save cube state: {error}")
            else:
                print(f"Cube state saved as {path.stem}.")
            continue
        if command == "load" or command.startswith("load "):
            parts = entry.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: load <name>")
                continue
            try:
                cube = load_cube_state(parts[1])
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"Could not load cube state: {error}")
            else:
                if virtual_attempt is not None:
                    virtual_attempt = None
                    print("Virtual timed solve canceled; result not recorded.")
                print(f"Loaded {cube.size}x{cube.size} cube state {parts[1]!r}.")
            continue
        if command in ("2x2", "3x3"):
            new_size = int(command[0])
            if new_size != cube.size:
                if virtual_attempt is not None:
                    virtual_attempt = None
                    print("Virtual timed solve canceled; result not recorded.")
                cube = Cube(new_size)
                print(f"Switched to a solved {new_size}x{new_size} cube.")
            else:
                print(f"Already using a {new_size}x{new_size} cube.")
            continue
        if command in ("solve", "guide"):
            try:
                solution = cube.solve()
            except (RuntimeError, ValueError) as error:
                print(error)
                continue
            if command == "guide":
                if not solution:
                    print("The cube is already solved.")
                    continue
                for move_count, move in enumerate(solution, start=1):
                    print(
                        f"Step {move_count}/{len(solution)}: {move} - "
                        f"{describe_move(move)}"
                    )
                    try:
                        choice = input("Press Enter to apply, or q to stop: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nGuided solve stopped.")
                        break
                    if choice.casefold() == "q":
                        print("Guided solve stopped.")
                        break
                    cube.apply_moves([move])
                    print(
                        cube.render(
                            color=use_color,
                            view=display,
                            show_help=True,
                            theme=theme,
                        )
                    )
                if cube.is_solved():
                    print(_solved_banner(use_color, theme))
                    finish_virtual_attempt()
                continue
            for move_count, move in enumerate(solution, start=1):
                cube.apply_moves([move])
                print(f"Solving... {move_count}/{len(solution)}: {move}")
                print(
                    cube.render(
                        color=use_color, view=display, show_help=True, theme=theme
                    )
                )
                if move_count < len(solution):
                    time.sleep(SOLVE_STEP_DELAY)
            if not solution:
                print("The cube is already solved.")
            finish_virtual_attempt()
            continue
        if command == "net":
            display = "net"
            continue
        if command == "cube":
            display = "cube"
            continue
        if command == "scramble":
            if virtual_attempt is not None:
                virtual_attempt = None
                print("Virtual timed solve canceled; result not recorded.")
            moves = scramble(cube)
            print("Scramble:", " ".join(moves))
            continue
        if not entry:
            continue

        try:
            cube.apply_moves(parse_bound_moves(entry, keybinds))
        except ValueError as error:
            print(error)
        else:
            finish_virtual_attempt()


if __name__ == "__main__":
    main()