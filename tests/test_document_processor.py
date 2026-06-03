from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.document_processor import create_chunks, split_text


class DocumentProcessorTest(unittest.TestCase):
    def test_split_text_preserves_overlap(self):
        chunks = split_text("abcdefghij", chunk_size=6, chunk_overlap=2)
        self.assertEqual(chunks, ["abcdef", "efghij"])

    def test_split_text_rejects_invalid_overlap(self):
        with self.assertRaises(ValueError):
            split_text("abc", chunk_size=3, chunk_overlap=3)

    def test_create_chunks_from_markdown(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "notes.md"
            source.write_text("battery capacity monitoring", encoding="utf-8")
            chunks = create_chunks(source, chunk_size=100, chunk_overlap=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source, "notes.md")
        self.assertIn("capacity", chunks[0].text)


if __name__ == "__main__":
    unittest.main()
