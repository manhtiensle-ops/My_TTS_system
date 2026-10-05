import os
import shutil
import subprocess
import tempfile
import unittest

from src.processors.audio_concat import AudioConcatenator, concat_wav_files


class TestAudioConcatenator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_tts_audio_")
        self.concatenator = AudioConcatenator()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _generate_tone(self, path: str, duration_sec: float = 1.0, freq: int = 440):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={freq}:duration={duration_sec}",
            "-ar", "48000",
            path
        ]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            self.skipTest("FFmpeg không khả dụng để chạy test audio")

    def test_concat_multiple_wavs(self):
        wav1 = os.path.join(self.test_dir, "t1.wav")
        wav2 = os.path.join(self.test_dir, "t2.wav")
        self._generate_tone(wav1, 1.0, 440)
        self._generate_tone(wav2, 1.0, 880)

        out_wav = os.path.join(self.test_dir, "merged.wav")
        self.concatenator.concat([wav1, wav2], out_wav)

        self.assertTrue(os.path.exists(out_wav))
        self.assertGreater(os.path.getsize(out_wav), 1000)

    def test_concat_to_mp3(self):
        wav1 = os.path.join(self.test_dir, "t1.wav")
        wav2 = os.path.join(self.test_dir, "t2.wav")
        self._generate_tone(wav1, 1.0, 440)
        self._generate_tone(wav2, 1.0, 880)

        out_mp3 = os.path.join(self.test_dir, "merged.mp3")
        self.concatenator.concat([wav1, wav2], out_mp3)

        self.assertTrue(os.path.exists(out_mp3))
        self.assertGreater(os.path.getsize(out_mp3), 500)


if __name__ == "__main__":
    unittest.main()
