import tempfile
import unittest

from denario import Denario
from denario.paper_agents.prompts import abstract_prompt


class ResearcherStatementTests(unittest.TestCase):
    def test_set_researcher_statement_persists_on_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            den = Denario(project_dir=tmpdir)
            den.set_researcher_statement(
                "Prioritize robustness over novelty and avoid causal language."
            )

            reloaded = Denario(project_dir=tmpdir)
            self.assertEqual(
                reloaded.research.researcher_statement,
                "Prioritize robustness over novelty and avoid causal language.",
            )

    def test_paper_prompts_include_researcher_statement_when_present(self):
        state = {
            "writer": "scientist",
            "idea": {
                "ResearcherStatement": "Keep the framing conservative and emphasize reproducibility.",
                "Idea": "Idea text",
                "Methods": "Method text",
                "Results": "Result text",
            },
            "paper": {"Abstract": ""},
        }

        prompt = abstract_prompt(state, 1)[1].content

        self.assertIn("Researcher statement:", prompt)
        self.assertIn("Keep the framing conservative", prompt)


if __name__ == "__main__":
    unittest.main()
