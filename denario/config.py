from pathlib import Path

# Using pathlib (modern approach) to define the base directory as the directory that contains this file.
BASE_DIR = Path(__file__).resolve().parent

# REPO_DIR is defined as one directory above the package
REPO_DIR = BASE_DIR.parent
## in colab we need REPO_DIR = "/content/Denario/"

LaTeX_DIR = BASE_DIR / "paper_agents" / "LaTeX"

DEFAUL_PROJECT_NAME = "project"
"""Default name of the project"""

# Constants for defining .md files and folder names
INPUT_FILES = "input_files"
PLOTS_FOLDER = "plots"
PAPER_FOLDER = "paper"

DESCRIPTION_FILE = "data_description.md"
RESEARCHER_STATEMENT_FILE = "researcher_statement.md"
IDEA_FILE = "idea.md"
METHOD_FILE = "methods.md"
RESULTS_FILE = "results.md"
LITERATURE_FILE = "literature.md"
REFEREE_FILE = "referee.md"
AUTHORSHIP_CONFIRMATION_FILE = "authorship_confirmation.md"
