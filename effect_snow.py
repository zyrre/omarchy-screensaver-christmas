"""Snow falls and accumulates, gradually revealing the text as snowflakes stick to it.

Classes:
    Snow: Snow falls continuously with some sticking to reveal the text.
    SnowConfig: Configuration for the Snow effect.
    SnowIterator: Iterator for the Snow effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
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
    return "snow", Snow, SnowConfig


@dataclass
class SnowConfig(BaseConfig):
    """Configuration for the Snow effect.

    Attributes:
        snow_colors (tuple[Color, ...]): Colors for the falling snow.
        snow_symbols (tuple[str, ...]): Symbols to use for snowflakes.
        final_gradient_stops (tuple[Color, ...]): Colors for the final gradient.
        final_gradient_steps (tuple[int, ...] | int): Number of gradient steps.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        movement_speed (float): Speed of falling snow.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="snow",
        help="Snow falls and accumulates, gradually revealing the text.",
        description="snow | Snow falls and gradually reveals the text as it sticks.",
        epilog=(
            "Example: terminaltexteffects snow --snow-colors ffffff e0ffff b0e0e6 "
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


class SnowIterator(BaseEffectIterator[SnowConfig]):
    """Iterator for the Snow effect."""

    def __init__(self, effect: Snow) -> None:
        """Initialize the effect iterator.

        Args:
            effect (Snow): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
        # Setup text characters - falling snow effect
        for character in self.terminal.get_characters():
            # Snow appearance - keep as snowflakes throughout
            snow_symbol = random.choice(self.config.snow_symbols)
            snow_color = random.choice(self.config.snow_colors)
            snow_scene = character.animation.new_scene()
            snow_scene.add_frame(snow_symbol, 1, colors=ColorPair(fg=snow_color))

            character.animation.activate_scene(snow_scene)

            # Start above the canvas and fall to input position
            character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.canvas.top))

            # Create falling path with swaying
            snowflake_speed = self.config.movement_speed * random.uniform(0.7, 1.3)
            fall_path = character.motion.new_path(speed=snowflake_speed, ease=easing.in_out_sine)

            # Add some sway waypoints
            num_sways = random.randint(2, 4)
            fall_distance = self.terminal.canvas.top - character.input_coord.row
            current_column = character.input_coord.column

            for i in range(1, num_sways):
                progress = i / num_sways
                sway_row = self.terminal.canvas.top - int(fall_distance * progress)
                sway_direction = 1 if i % 2 == 0 else -1
                sway_amount = random.randint(1, 3)
                current_column = current_column + (sway_direction * sway_amount)
                sway_column = max(self.terminal.canvas.left, min(self.terminal.canvas.right, current_column))
                fall_path.new_waypoint(Coord(sway_column, sway_row))

            # Final waypoint at input position
            fall_path.new_waypoint(character.input_coord)

            character.motion.activate_path(fall_path)
            self.pending_chars.append(character)

        # Sort by row (bottom to top) so bottom letters fill first
        self.pending_chars.sort(key=lambda c: c.input_coord.row, reverse=True)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_chars or self.active_characters:
            if self.pending_chars:
                # Release a few characters at a time
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        self.terminal.set_character_visibility(next_character, is_visible=True)
                        self.active_characters.add(next_character)
                    else:
                        break

            self.update()
            return self.frame
        raise StopIteration


class Snow(BaseEffect[SnowConfig]):
    """Snow falls and accumulates, gradually revealing the text.

    Attributes:
        effect_config (SnowConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    _config_cls = SnowConfig
    _iterator_cls = SnowIterator
