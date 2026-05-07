import unittest
import sys
import os
from io import BytesIO

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from docx_logic import fetch_word_data, create_vocabulary_docx

class TestVocabularyLogic(unittest.TestCase):
    def test_fetch_word_data_valid(self):
        """Test fetching data for a common word."""
        result = fetch_word_data("apple")
        self.assertIsNotNone(result)
        headword, data = result
        self.assertEqual(headword, "apple")
        self.assertGreater(len(data), 0)
        self.assertIn("pos", data[0]["word_info"])
        self.assertIn("def", data[0]["meaning_data"])

    def test_fetch_word_data_normalization(self):
        """Test that inflected words are normalized."""
        result = fetch_word_data("books")
        self.assertIsNotNone(result)
        headword, data = result
        self.assertEqual(headword, "book")

    def test_fetch_word_data_invalid(self):
        """Test fetching data for a non-existent word."""
        data = fetch_word_data("thisisnotarealword12345")
        self.assertIsNone(data)

    def test_create_vocabulary_docx(self):
        """Test the document generation process."""
        words = ["apple", "test"]
        doc, failed = create_vocabulary_docx(words)
        
        self.assertEqual(len(failed), 0)
        self.assertIsNotNone(doc)
        
        # Test saving to memory
        buffer = BytesIO()
        doc.save(buffer)
        self.assertGreater(buffer.tell(), 0)

if __name__ == '__main__':
    unittest.main()
