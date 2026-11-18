import unittest
from unittest.mock import patch
from src.devices.scale import ScaleUARTReader
from src.core.stability import ScaleStabilityMachine, ScaleState


class TestSystemSmoke(unittest.TestCase):
    def test_scale_uart_and_stability_transition(self):
        reader = ScaleUARTReader()
        parsed_weights = []

        with patch(
            "src.devices.scale.handle_scale_char_processed",
            side_effect=lambda w: parsed_weights.append(w),
        ):
            reader.handle_scale_char("28450MN\r\n")

        self.assertEqual(len(parsed_weights), 1)
        self.assertEqual(parsed_weights[0], 28450.0)

        machine = ScaleStabilityMachine()
        with (
            patch("src.core.stability.session_manager"),
            patch("src.devices.led_controller"),
        ):
            machine.process_new_weight(28450.0)

        self.assertEqual(machine.state, ScaleState.SCALE_STABILIZING)
