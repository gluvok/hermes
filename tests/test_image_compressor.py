import io
import unittest

from PIL import Image, ImageDraw

from src.config.constants import ANPR_CAPTURE_INTERVAL, POST_STABILITY_DURATION
from src.core.session import WeighbridgeSessionManager
from src.core.stability import ScaleStabilityMachine, ScaleState
from src.services.image_compressor import compress_image_bytes


def _jpeg(size: tuple[int, int], text: str = "") -> bytes:
    """Q100 JPEG of a black frame with optional white text (stand-in for a camera snapshot)."""
    img = Image.new("RGB", size, (128, 128, 128) if not text else (0, 0, 0))
    if text:
        ImageDraw.Draw(img).text((size[0] // 8, size[1] // 2), text, fill=(255, 255, 255), font_size=size[1] // 10)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=100)
    return buf.getvalue()


class TestImageCompressor(unittest.TestCase):
    def test_compress_none_or_empty(self):
        self.assertIsNone(compress_image_bytes(None))
        self.assertIsNone(compress_image_bytes(b""))

    def test_compress_corrupt_bytes_returns_original(self):
        corrupt = b"not_an_image_stream"
        res = compress_image_bytes(corrupt)
        self.assertEqual(res, corrupt)

    def test_compress_4k_image_downscaled_to_1920(self):
        raw_bytes = _jpeg((3840, 2160), "RJ45CX3690")

        compressed = compress_image_bytes(raw_bytes, max_dim=1920, quality=85)
        self.assertIsNotNone(compressed)
        assert compressed is not None

        self.assertEqual(Image.open(io.BytesIO(compressed)).size, (1920, 1080))
        self.assertLess(len(compressed), len(raw_bytes))

    def test_compress_1080p_image_dimensions_preserved(self):
        raw_bytes = _jpeg((1920, 1080), "PLATE")

        compressed = compress_image_bytes(raw_bytes, max_dim=1920, quality=85)
        self.assertIsNotNone(compressed)
        assert compressed is not None

        self.assertEqual(Image.open(io.BytesIO(compressed)).size, (1920, 1080))

    def test_compress_always_runs_for_small_image(self):
        raw_bytes = _jpeg((200, 200))

        # Should still run compression with quality=75 and produce smaller payload
        compressed = compress_image_bytes(raw_bytes, quality=75)
        self.assertIsNotNone(compressed)
        assert compressed is not None
        self.assertLess(len(compressed), len(raw_bytes))

    def test_compress_applies_exif_orientation(self):
        img = Image.new("RGB", (400, 200), (10, 20, 30))
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation: rotate 90 CW -> displayed as 200x400
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=95, exif=exif.tobytes())
        compressed = compress_image_bytes(buf.getvalue())
        assert compressed is not None
        self.assertEqual(Image.open(io.BytesIO(compressed)).size, (200, 400))


class TestMidStabilityAndShortPostStability(unittest.TestCase):
    def setUp(self):
        self.sm = WeighbridgeSessionManager()
        self.machine = ScaleStabilityMachine()

    def tearDown(self):
        self.sm.reset_session()
        self.machine.reset()

    def test_post_stability_duration_is_5_seconds(self):
        self.assertEqual(POST_STABILITY_DURATION, 5.0)

    def test_anpr_capture_interval_is_1_second(self):
        self.assertEqual(ANPR_CAPTURE_INTERVAL, 1.0)

    def test_mid_stability_triggers_at_half_duration(self):
        self.machine.state = ScaleState.SCALE_STABILIZING
        self.machine._current_stable_candidate = 25000.0
        self.machine._candidate_start_time = 1000.0
        self.machine._mid_stability_triggered = False

        # At t = 1004.0 (elapsed = 4.0s < 5.0s halfway): should not trigger
        self.machine._evaluate_stability_window(25000.5, 1004.0)
        self.assertFalse(self.machine._mid_stability_triggered)
        self.assertEqual(self.machine.state, ScaleState.SCALE_STABILIZING)

        # At t = 1005.1 (elapsed = 5.1s >= 5.0s halfway): should trigger
        self.machine._evaluate_stability_window(25000.5, 1005.1)
        self.assertTrue(self.machine._mid_stability_triggered)
        self.assertEqual(self.machine.state, ScaleState.SCALE_STABILIZING)

        # At t = 1010.1 (elapsed = 10.1s >= 10.0s stability confirmed): stable recorded
        self.machine._evaluate_stability_window(25000.5, 1010.1)
        self.assertEqual(self.machine.state, ScaleState.SCALE_STABLE_RECORDED)

    def test_weight_shift_resets_mid_stability_trigger(self):
        self.machine.state = ScaleState.SCALE_STABILIZING
        self.machine._current_stable_candidate = 25000.0
        self.machine._candidate_start_time = 1000.0
        self.machine._mid_stability_triggered = True

        # Weight shifts by 50 kg (> 2.0 kg tolerance)
        self.machine._evaluate_stability_window(25050.0, 1007.0)
        self.assertFalse(self.machine._mid_stability_triggered)
        self.assertEqual(self.machine._current_stable_candidate, 25050.0)
