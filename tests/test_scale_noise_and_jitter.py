import unittest
from unittest.mock import patch
from src.devices.scale import ScaleUARTReader
from src.core.stability import ScaleStabilityMachine

class TestScaleNoiseAndJitter(unittest.TestCase):
    def setUp(self):
        self.reader = ScaleUARTReader()
        self.parsed = []

    def test_split_packets_and_noise_bytes_reconstruction(self):
        with patch("src.devices.scale.handle_scale_char_processed", side_effect=lambda w: self.parsed.append(w)):
            # Fragmented packet across buffer boundaries with framing noise
            self.reader.handle_scale_char("\x02NOISE_")
            self.reader.handle_scale_char("28450")
            self.reader.handle_scale_char("MN\r\n")
            self.assertEqual(len(self.parsed), 1)
            self.assertEqual(self.parsed[0], 28450.0)

    def test_weight_bounce_resets_stability_timer(self):
        machine = ScaleStabilityMachine()
        # Weight settles above threshold at 28450
        machine.process_new_weight(28450.0)
        initial_start_time = machine._candidate_start_time
        self.assertGreater(initial_start_time, 0.0)
        self.assertEqual(machine._current_stable_candidate, 28450.0)

        # Driver bounces on scale: spike to 28490 (+40kg > default tolerance 2.0kg)
        machine.process_new_weight(28490.0)
        # Candidate resets to the new weight and resets timer
        self.assertEqual(machine._current_stable_candidate, 28490.0)
        self.assertGreaterEqual(machine._candidate_start_time, initial_start_time)
