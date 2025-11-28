"""Snow falls and accumulates, gradually revealing the text as snowflakes stick to it.

Classes:
    Christmas: Snow falls continuously with some sticking to reveal the text.
    ChristmasConfig: Configuration for the Christmas effect.
    ChristmasIterator: Iterator for the Christmas effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "christmas", Christmas, ChristmasConfig


@dataclass
class ChristmasConfig(BaseConfig):
    """Configuration for the Christmas effect.

    Attributes:
        snow_colors (tuple[Color, ...]): Colors for the falling snow.
        snow_symbols (tuple[str, ...]): Symbols to use for snowflakes.
        final_gradient_stops (tuple[Color, ...]): Colors for the final gradient.
        final_gradient_steps (tuple[int, ...] | int): Number of gradient steps.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        movement_speed (float): Speed of falling snow.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="christmas",
        help="Snow falls and accumulates, gradually revealing the text.",
        description="christmas | Snow falls and gradually reveals the text as it sticks.",
        epilog=(
            "Example: terminaltexteffects christmas --snow-colors ffffff e0ffff b0e0e6 "
            "--final-gradient-stops ff0000 00ff00 ffd700"
        ),
    )

    snow_colors: tuple[Color, ...] = ArgSpec(
        name="--snow-colors",
        type=argutils.ColorArg.type_parser,
        metavar=argutils.ColorArg.METAVAR,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("ffffff"), Color("e0ffff"), Color("b0e0e6")),
        help="Space separated list of colors for the falling snow.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Colors for the falling snow."

    snow_symbols: tuple[str, ...] = ArgSpec(
        name="--snow-symbols",
        type=argutils.Symbol.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=("*", ".", "o", "+"),
        metavar=argutils.Symbol.METAVAR,
        help="Space separated list of symbols to use for snowflakes.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[str, ...] : Symbols to use for snowflakes."

    movement_speed: float = ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.1,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Movement speed of the snowflakes.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Movement speed of the snowflakes."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("ff0000"), Color("00ff00"), Color("ffd700")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Colors for the final gradient."

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of gradient steps to use.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, ...] | int : Number of gradient steps."

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.HORIZONTAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class ChristmasIterator(BaseEffectIterator[ChristmasConfig]):
    """Iterator for the Christmas effect."""

    def __init__(self, effect: Christmas) -> None:
        """Initialize the effect iterator.

        Args:
            effect (Christmas): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.background_snow: list[EffectCharacter] = []
        self.bottom_pile_height: dict[int, int] = {}
        self.text_spawn_delay: int = 0
        self.background_spawn_delay: int = 0
        self.text_complete: bool = False
        self.fadeout_counter: int = 0
        self.spawn_stopped: bool = False
        self.build()

    def is_outline_character(self, character: EffectCharacter) -> bool:
        """Check if a character is on the outline (has at least one space neighbor).

        Args:
            character: The character to check.

        Returns:
            bool: True if character is on the outline, False if interior.
        """
        coord = character.input_coord
        # Check all 4 neighbors (up, down, left, right)
        neighbors = [
            Coord(coord.column, coord.row - 1),  # up
            Coord(coord.column, coord.row + 1),  # down
            Coord(coord.column - 1, coord.row),  # left
            Coord(coord.column + 1, coord.row),  # right
        ]

        # If any neighbor is a space (or doesn't exist), this is an outline character
        all_chars = {char.input_coord: char for char in self.terminal.get_characters()}
        for neighbor_coord in neighbors:
            if neighbor_coord not in all_chars:
                return True  # Edge of text = outline
        return False

    def build(self) -> None:
        """Build the initial state of the effect."""
        # Christmas tree ASCII art
        tree_lines = [
            "                        ,",
            "                      _/^\\_",
            "                     <     >",
            "                      /.-.\          ",
            "                      `/&\`                    ",
            "                     ,@.*;@,",
            "                    /_o.I %_\\     ",
            "                   (`'--:o(_@;",
            "                  /`;--.,__ `')              ",
            "                 ;@`o % O,*`'`&\\ ",
            "                (`'--)_@ ;o %'()\\       ",
            "                /`;--._`''--._O'@;",
            "               /&*,()~o`;-.,_ `\"\"\")",
            "               /`,@ ;+& () o*`;-';\\",
            "              (`\"\"--.,_0 +% @' &()\\",
            "              /-.,_    ``''--....-'`)  *",
            "              /@%;o`:;'--,.__   __.\'\\",
            "             ;*,&(); @ % &^;~`\"`o;@();          ",
            "             /(); o^~; & ().o@*&`;&%O\\",
            "             `\"=\"==\"\"==,,,.,=\"==\"===\"`",
            "          __.----.---''#####---...___...-----._",
            "        '`            `\"\"\"\"\"`",
        ]

        # Ornament symbols that get bright colors
        ornament_symbols = {'*', '@', '&', '%', 'O', 'o', '+'}
        ornament_colors = [
            Color("ff0000"),  # Red
            Color("ff69b4"),  # Pink
            Color("ffd700"),  # Gold
            Color("00ffff"),  # Cyan
            Color("ff00ff"),  # Magenta
            Color("ff8c00"),  # Dark orange
        ]

        # Calculate horizontal center
        terminal_width = self.terminal.canvas.right - self.terminal.canvas.left + 1
        center_col = self.terminal.canvas.left + terminal_width // 2

        # Calculate tree positioning
        tree_height = len(tree_lines)
        max_line_width = max(len(line) for line in tree_lines)
        start_col = center_col - max_line_width // 2

        # Create tree characters - NOW WITH CORRECT COORDINATE SYSTEM!
        # Bottom = small number, Top = large number, ADD to go up
        for line_index, line in enumerate(tree_lines):
            # Trunk (last line) at bottom, star (first line) higher up
            # Reverse the tree so trunk is first
            reversed_index = tree_height - 1 - line_index
            row = self.terminal.canvas.bottom + reversed_index

            for col_offset, char in enumerate(line):
                if char != ' ':  # Skip spaces
                    col = start_col + col_offset

                    # Determine color based on position and symbol
                    if line_index < 3:
                        # Star at top - yellow/gold
                        final_color = Color("ffd700")
                    elif line_index >= tree_height - 2 or '#' in char:
                        # Trunk at bottom - brown
                        final_color = Color("8b4513")
                    elif char in ornament_symbols:
                        # Ornaments - colorful
                        final_color = random.choice(ornament_colors)
                    else:
                        # Tree body - green
                        final_color = Color("228b22")

                    tree_char = self.terminal.add_character(char, Coord(col, row))
                    scene = tree_char.animation.new_scene()
                    scene.add_frame(char, 1, colors=ColorPair(fg=final_color))
                    tree_char.animation.activate_scene(scene)
                    tree_char.motion.set_coordinate(Coord(col, row))
                    self.terminal.set_character_visibility(tree_char, is_visible=True)
                    self.active_characters.add(tree_char)

        # Mark as complete
        self.text_complete = True

    def spawn_background_snowflake(self, speed_multiplier: float = 1.0) -> None:
        """Spawn a background snowflake that falls to the bottom.

        Args:
            speed_multiplier: Multiplier for the falling speed (default 1.0).
        """
        snow_col = random.randint(self.terminal.canvas.left, self.terminal.canvas.right)
        snow_char = self.terminal.add_character(" ", Coord(snow_col, self.terminal.canvas.top))
        snow_char.layer = 1  # Behind text characters

        # Snow appearance
        snow_symbol = random.choice(self.config.snow_symbols)
        snow_color = random.choice(self.config.snow_colors)
        snow_scene = snow_char.animation.new_scene()
        snow_scene.add_frame(snow_symbol, 1, colors=ColorPair(fg=snow_color))
        snow_char.animation.activate_scene(snow_scene)

        # Set starting position at top
        snow_char.motion.set_coordinate(Coord(snow_col, self.terminal.canvas.top))

        # Create falling path with gentle swaying
        snowflake_speed = self.config.movement_speed * random.uniform(0.7, 1.3) * speed_multiplier
        fall_path = snow_char.motion.new_path(speed=snowflake_speed, ease=easing.in_out_sine)

        # Add sway waypoints for natural movement
        num_sways = random.randint(2, 4)
        fall_distance = self.terminal.canvas.top - self.terminal.canvas.bottom
        current_column = snow_col

        for i in range(1, num_sways):
            progress = i / num_sways
            sway_row = self.terminal.canvas.top - int(fall_distance * progress)
            sway_direction = 1 if i % 2 == 0 else -1
            sway_amount = random.randint(1, 3)
            current_column = current_column + (sway_direction * sway_amount)
            sway_column = max(self.terminal.canvas.left, min(self.terminal.canvas.right, current_column))
            fall_path.new_waypoint(Coord(sway_column, sway_row))

        # Final waypoint at bottom
        final_column = max(self.terminal.canvas.left, min(self.terminal.canvas.right, current_column))
        fall_path.new_waypoint(Coord(final_column, self.terminal.canvas.bottom))

        snow_char.motion.activate_path(fall_path)
        self.terminal.set_character_visibility(snow_char, is_visible=True)
        self.active_characters.add(snow_char)
        self.background_snow.append(snow_char)

    def check_background_snow_landing(self) -> None:
        """Check if background snow has landed and stack it."""
        for snow in list(self.background_snow):
            if not snow.motion.active_path:
                snow_coord = snow.motion.current_coord
                landing_column = snow_coord.column

                if landing_column not in self.bottom_pile_height:
                    self.bottom_pile_height[landing_column] = 0

                # Stack snow at bottom (max height 5) - subtract to stack upward
                if self.bottom_pile_height[landing_column] < 5:
                    stacked_row = self.terminal.canvas.bottom - self.bottom_pile_height[landing_column]
                    snow.motion.set_coordinate(Coord(landing_column, stacked_row))
                    self.bottom_pile_height[landing_column] += 1
                else:
                    # Pile is full, remove this snowflake
                    self.terminal.set_character_visibility(snow, is_visible=False)
                    self.background_snow.remove(snow)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        # Build tree from bottom to top
        if self.pending_chars:
            # Release 5-10 characters at a time for faster build (no delay)
            num_to_spawn = min(random.randint(5, 10), len(self.pending_chars))
            for _ in range(num_to_spawn):
                if self.pending_chars:
                    # Pop from front (bottom characters first due to reverse sort)
                    next_character = self.pending_chars.pop(0)
                    self.terminal.set_character_visibility(next_character, is_visible=True)
                    self.active_characters.add(next_character)

        elif not self.text_complete:
            # Check if all text characters have landed (completed their paths and turned red)
            all_text_landed = not self.pending_chars
            if all_text_landed:
                # Check if any text characters still have active paths
                for char in self.terminal.get_characters():
                    if char.motion.active_path:
                        all_text_landed = False
                        break

            if all_text_landed:
                # Text completely filled with red, start fadeout
                self.text_complete = True
                # Speed up all existing background snow by creating new fast paths
                for snow in self.background_snow:
                    if snow.motion.active_path:
                        # Get current position
                        current_pos = snow.motion.current_coord
                        # Create new fast path from current position to bottom
                        fast_speed = self.config.movement_speed * 5.0  # Half as fast (5x instead of 10x)
                        new_path = snow.motion.new_path(speed=fast_speed, ease=easing.in_quad)
                        new_path.new_waypoint(Coord(current_pos.column, self.terminal.canvas.bottom))
                        snow.motion.activate_path(new_path)

        # Spawn background snowflakes - gentle continuous snow
        if not self.spawn_stopped:
            if self.text_complete:
                self.fadeout_counter += 1
                if self.fadeout_counter > 600:  # Keep tree visible for ~5 seconds before stopping
                    self.spawn_stopped = True
                else:
                    if self.background_spawn_delay <= 0:
                        # After tree complete: gentle continuous snow
                        if random.random() < 0.15:  # 15% chance to spawn
                            self.spawn_background_snowflake()
                        self.background_spawn_delay = 3
                    else:
                        self.background_spawn_delay -= 1
            else:
                # While building tree - minimal background snow
                if self.background_spawn_delay <= 0:
                    if random.random() < 0.1:  # Only 10% chance to spawn
                        self.spawn_background_snowflake()
                    self.background_spawn_delay = 8  # Longer delay
                else:
                    self.background_spawn_delay -= 1

        # Check background snow landing
        self.check_background_snow_landing()

        # End when spawning stopped and all background snow is gone
        if self.spawn_stopped and len(self.background_snow) == 0:
            raise StopIteration

        # Keep animation running
        self.update()
        return self.frame


class Christmas(BaseEffect[ChristmasConfig]):
    """Snow falls and accumulates, gradually revealing the text.

    Attributes:
        effect_config (ChristmasConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    _config_cls = ChristmasConfig
    _iterator_cls = ChristmasIterator
