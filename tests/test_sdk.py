import unittest
import tempfile
import json
from pathlib import Path
from vieneu_sdk.sorter import NaturalSorter
from vieneu_sdk.processor import NovelBatchProcessor
from vieneu_sdk.client import VieneuClient


class DummyClient(VieneuClient):
    """Mock client không gọi network thực tế."""
    def __init__(self):
        self.base_url = "http://localhost:8000"

    def check_health(self):
        return {"status": "ok"}

    def load_gpu(self, model_name="v3turbo", voice_preload=None, idle_timeout_seconds=600):
        return {"status": "ok"}

    def unload_gpu(self, force=False):
        return {"status": "unloaded"}

    def render_chapter_video(
        self,
        chapter_text: str,
        cover_image_path: Path,
        output_file_path: Path,
        chapter_name: str = "",
        voice: str = "Ngọc Huyền",
        speed: float = 1.2,
        resolution: str = "1920x1080",
        target_words: int = 100,
    ) -> Path:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_bytes(b"dummy mp4 video content")
        return output_file_path


class TestVieneuSDK(unittest.TestCase):

    def test_natural_sorter(self):
        files = [
            Path("chap_10.txt"),
            Path("chap_1.txt"),
            Path("chap_2.txt"),
            Path("chap_20.txt"),
            Path("chap_3.txt"),
        ]
        sorted_files = NaturalSorter.sort_files(files)
        names = [f.name for f in sorted_files]
        self.assertEqual(names, ["chap_1.txt", "chap_2.txt", "chap_3.txt", "chap_10.txt", "chap_20.txt"])

    def test_batch_processor_range_and_limit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            chapters_dir = tmp_path / "chapters"
            chapters_dir.mkdir()

            for i in range(1, 11):
                (chapters_dir / f"chap_{i}.txt").write_text(f"Nội dung chương {i}", encoding="utf-8")

            cover_path = tmp_path / "cover.jpg"
            cover_path.write_bytes(b"dummy cover")

            out_dir = tmp_path / "output_mp4"

            mock_client = DummyClient()
            processor = NovelBatchProcessor(client=mock_client)

            # Test filter start 2, end 5
            filtered = processor.scan_and_filter(chapters_dir, start_chapter=2, end_chapter=5)
            self.assertEqual(len(filtered), 4)
            self.assertEqual([f.name for f in filtered], ["chap_2.txt", "chap_3.txt", "chap_4.txt", "chap_5.txt"])

            # Test limit=3
            filtered_limit = processor.scan_and_filter(chapters_dir, limit=3)
            self.assertEqual(len(filtered_limit), 3)

            # Test full process execution with checkpoint
            summary = processor.process(
                folder_path=chapters_dir,
                cover_path=cover_path,
                output_dir=out_dir,
                start_chapter=1,
                end_chapter=3,
            )

            self.assertEqual(summary["processed"], 3)
            self.assertTrue((out_dir / "chap_1.mp4").exists())
            self.assertTrue((out_dir / ".batch_checkpoint.json").exists())

            # Test resume (should skip completed chapters)
            summary_resume = processor.process(
                folder_path=chapters_dir,
                cover_path=cover_path,
                output_dir=out_dir,
                start_chapter=1,
                end_chapter=3,
                resume=True,
            )
            self.assertEqual(summary_resume["processed"], 0)
            self.assertEqual(summary_resume["skipped"], 3)


if __name__ == "__main__":
    unittest.main()
