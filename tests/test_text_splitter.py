import unittest

from src.processors.text_splitter import NovelTextSplitter, split_chapter


class TestNovelTextSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = NovelTextSplitter(default_target_words=100)

    def test_empty_text(self):
        chunks = self.splitter.split("")
        self.assertEqual(chunks, [])

    def test_short_text_single_chunk(self):
        text = "Đây là một đoạn văn ngắn dưới 100 từ.\nChỉ có hai câu."
        chunks = self.splitter.split(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_split_by_threshold_and_newline(self):
        # Tạo 3 đoạn văn, mỗi đoạn ~60 từ
        para1 = " ".join(["từ"] * 60)
        para2 = " ".join(["đoạn"] * 60)
        para3 = " ".join(["kết"] * 50)
        text = f"{para1}\n{para2}\n{para3}"

        chunks = self.splitter.split(text, target_words=100)
        # para1 (60 words) + para2 (60 words) >= 100 => chunk 1 có 120 từ
        # para3 (50 words) => chunk 2 có 50 từ
        self.assertEqual(len(chunks), 2)
        self.assertIn("từ", chunks[0])
        self.assertIn("đoạn", chunks[0])
        self.assertIn("kết", chunks[1])

    def test_helper_function_compatibility(self):
        text = "Dòng 1 câu chuyện.\nDòng 2 tiếp tục."
        chunks = split_chapter(text, target_words=5)
        self.assertTrue(len(chunks) >= 1)


if __name__ == "__main__":
    unittest.main()
