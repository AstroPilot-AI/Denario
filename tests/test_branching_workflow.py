import tempfile
import unittest
from pathlib import Path

from denario import Denario
from denario.config import (
    IDEA_CANDIDATES_FILE,
    IDEA_COMPARISON_FILE,
    IDEA_FILE,
    INPUT_FILES,
    METHOD_CANDIDATES_FILE,
    METHOD_COMPARISON_FILE,
    METHOD_FILE,
)


class FakeBranchDenario(Denario):
    def get_idea(self, **kwargs) -> None:  # type: ignore[override]
        idea = f"Idea from {Path(self.project_dir).name}"
        self.research.idea = idea
        with open(Path(self.project_dir) / INPUT_FILES / IDEA_FILE, "w") as f:
            f.write(idea)

    def get_method(self, **kwargs) -> None:  # type: ignore[override]
        method = f"Method from {Path(self.project_dir).name} using {self.research.idea}"
        self.research.methodology = method
        with open(Path(self.project_dir) / INPUT_FILES / METHOD_FILE, "w") as f:
            f.write(method)


class BranchingWorkflowTests(unittest.TestCase):
    def test_generate_idea_branches_persists_candidates_and_comparison(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            den = FakeBranchDenario(project_dir=tmpdir)
            den.set_data_description("Dataset description")

            candidates = den.generate_idea_branches(count=3)

            self.assertEqual(len(candidates), 3)
            self.assertEqual(den.research.idea, "")
            self.assertTrue(
                (Path(tmpdir) / INPUT_FILES / IDEA_CANDIDATES_FILE).exists()
            )
            self.assertTrue(
                (Path(tmpdir) / INPUT_FILES / IDEA_COMPARISON_FILE).exists()
            )

    def test_select_idea_candidate_promotes_candidate_to_primary_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            den = Denario(project_dir=tmpdir)
            den.set_idea_candidates(["Idea A", "Idea B"])

            selected = den.select_idea_candidate(2)

            self.assertEqual(selected, "Idea B")
            self.assertEqual(den.research.idea, "Idea B")
            self.assertEqual((Path(tmpdir) / INPUT_FILES / IDEA_FILE).read_text(), "Idea B")

    def test_generate_method_branches_uses_selected_idea_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            den = FakeBranchDenario(project_dir=tmpdir)
            den.set_data_description("Dataset description")
            den.set_idea("Chosen idea")

            candidates = den.generate_method_branches(count=2)

            self.assertEqual(len(candidates), 2)
            self.assertTrue(
                (Path(tmpdir) / INPUT_FILES / METHOD_CANDIDATES_FILE).exists()
            )
            self.assertTrue(
                (Path(tmpdir) / INPUT_FILES / METHOD_COMPARISON_FILE).exists()
            )

            reloaded = Denario(project_dir=tmpdir)
            self.assertEqual(len(reloaded.research.method_candidates), 2)


if __name__ == "__main__":
    unittest.main()
