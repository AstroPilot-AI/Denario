import tempfile
import unittest
from pathlib import Path

from denario import AuthorshipConfirmationError, Denario
from denario.config import AUTHORSHIP_CONFIRMATION_FILE, INPUT_FILES


class AuthorshipGateTests(unittest.TestCase):
    def test_get_paper_requires_authorship_confirmation_before_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            den = Denario(project_dir=tmpdir)
            den.set_data_description("Dataset description")
            den.set_idea("Research idea")
            den.set_method("Methodology")
            den.set_results("Results")

            with self.assertRaises(AuthorshipConfirmationError):
                den.get_paper()

    def test_confirmation_is_written_and_invalidated_on_artifact_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            den = Denario(project_dir=tmpdir)
            den.set_data_description("Dataset description")
            den.set_idea("Research idea")
            den.set_method("Methodology")
            den.set_results("Results")

            den.confirm_authorship(
                "Reviewed claims, checked citations, and rewrote the abstract/results framing."
            )

            confirmation_path = Path(tmpdir) / INPUT_FILES / AUTHORSHIP_CONFIRMATION_FILE
            self.assertTrue(confirmation_path.exists())
            self.assertIn("Reviewed claims: yes", confirmation_path.read_text())

            den.set_results("Updated results after manual review")

            self.assertFalse(confirmation_path.exists())
            self.assertEqual(den.research.authorship_confirmation, "")


if __name__ == "__main__":
    unittest.main()
