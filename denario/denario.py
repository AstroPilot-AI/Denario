from typing import List
import asyncio
import time
import os
import shutil
import re
from datetime import datetime, UTC
from pathlib import Path
from PIL import Image 
import cmbagent

from .config import DEFAUL_PROJECT_NAME, INPUT_FILES, PLOTS_FOLDER, DESCRIPTION_FILE, RESEARCHER_STATEMENT_FILE, IDEA_FILE, IDEA_CANDIDATES_FILE, IDEA_COMPARISON_FILE, METHOD_FILE, METHOD_CANDIDATES_FILE, METHOD_COMPARISON_FILE, RESULTS_FILE, LITERATURE_FILE, AUTHORSHIP_CONFIRMATION_FILE, BRANCH_WORKSPACES_DIR
from .research import Research
from .key_manager import KeyManager
from .llm import LLM, models
from .paper_agents.journal import Journal
from .idea import Idea
from .method import Method
from .experiment import Experiment
from .paper_agents.agents_graph import build_graph
from .utils import llm_parser, input_check, check_file_paths, in_notebook
from .langgraph_agents.agents_graph import build_lg_graph
from .exceptions import AuthorshipConfirmationError
from cmbagent import preprocess_task

class Denario:
    """
    Denario main class. Allows to set the data and tools description, generate a research idea, generate methodology and compute the results. The it can generate the latex draft of a scientific article with a given journal style from the computed results.
    
    It uses two main backends:

    - `cmbagent`,  for detailed planning and control involving numerous agents for the idea, methods and results generation.
    - `langgraph`, for faster idea and method generation, and for the paper writing.

    Args:
        research: Research object to use as initial state. If `None`, a default Research() is 
            created (and may be populated from files in project_dir/input_files via set_all()).
        project_dir: Directory project. If `None`, create a `project` folder in the current directory.
        clear_project_dir: Clear all files in project directory when initializing if `True`.
    """

    def __init__(self,
                 research: Research | None = None,
                 project_dir: str | None = None, 
                 clear_project_dir: bool = False,
                 ):
        
        if project_dir is None:
            project_dir = os.path.join( os.getcwd(), DEFAUL_PROJECT_NAME )
        if not os.path.exists(project_dir):
            os.mkdir(project_dir)

        if research is None:
            research = Research()  # Initialize with default values
        self.research = research
        self.clear_project_dir = clear_project_dir

        if os.path.exists(project_dir) and clear_project_dir:
            shutil.rmtree(project_dir)
            os.makedirs(project_dir, exist_ok=True)
        self.project_dir = project_dir

        self.plots_folder = os.path.join(self.project_dir, INPUT_FILES, PLOTS_FOLDER)
        self.authorship_confirmation_path = os.path.join(
            self.project_dir, INPUT_FILES, AUTHORSHIP_CONFIRMATION_FILE
        )
        # Ensure the folder exists
        os.makedirs(self.plots_folder, exist_ok=True)

        self._setup_input_files()

        # Get keys from environment if they exist
        self.keys = KeyManager()
        self.keys.get_keys_from_env()

        self.run_in_notebook = in_notebook()

        self.set_all()

    def _setup_input_files(self) -> None:
        input_files_dir = os.path.join(self.project_dir, INPUT_FILES)
        
        # If directory exists and want to clear it, remove it and all its contents
        if os.path.exists(input_files_dir) and self.clear_project_dir:
            shutil.rmtree(input_files_dir)
            
        # Create fresh input_files directory
        os.makedirs(input_files_dir, exist_ok=True)

    def reset(self) -> None:
        """Reset Research object"""

        self.research = Research()

    #---
    # Setters
    #---

    def setter(self, field: str | None, file: str) -> str:
        """Base method for setting the content of idea, method or results."""

        path = os.path.join(self.project_dir, INPUT_FILES, file)
        previous_value = None
        if os.path.exists(path):
            with open(path, 'r') as f:
                previous_value = f.read()

        if field is None:
            try:
                with open(path, 'r') as f:
                    field = f.read()
            except FileNotFoundError:
                raise FileNotFoundError("Please provide an input string or path to a markdown file.")

        field = input_check(field)
                
        with open(path, 'w') as f:
            f.write(field)

        if previous_value is not None and previous_value != field:
            self._invalidate_authorship_confirmation()

        return field

    def _invalidate_authorship_confirmation(self) -> None:
        self.research.authorship_confirmation = ""
        if os.path.exists(self.authorship_confirmation_path):
            os.remove(self.authorship_confirmation_path)

    def _load_authorship_confirmation(self) -> str:
        if self.research.authorship_confirmation:
            return self.research.authorship_confirmation

        try:
            with open(self.authorship_confirmation_path, 'r') as f:
                self.research.authorship_confirmation = f.read()
        except FileNotFoundError:
            self.research.authorship_confirmation = ""

        return self.research.authorship_confirmation

    def confirm_authorship(
        self,
        summary: str,
        *,
        reviewed_claims: bool = True,
        reviewed_citations: bool = True,
        accepts_responsibility: bool = True,
    ) -> str:
        """Record explicit human sign-off before paper generation.

        Args:
            summary: Brief description of what the human reviewed or rewrote.
            reviewed_claims: Confirm that claims were checked against the artifacts.
            reviewed_citations: Confirm that citations/references were checked.
            accepts_responsibility: Confirm that a human accepts authorship responsibility.
        """

        summary = input_check(summary).strip()
        if not summary:
            raise ValueError("Please provide a non-empty authorship review summary.")
        if not reviewed_claims or not reviewed_citations or not accepts_responsibility:
            raise ValueError(
                "Authorship confirmation requires claims review, citation review, and responsibility acceptance."
            )

        confirmed_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        confirmation = (
            "# Authorship Confirmation\n\n"
            f"Confirmed at: {confirmed_at}\n\n"
            "- Reviewed claims: yes\n"
            "- Reviewed citations: yes\n"
            "- Accepts human authorship responsibility: yes\n\n"
            "## Review Summary\n\n"
            f"{summary}\n"
        )

        with open(self.authorship_confirmation_path, 'w') as f:
            f.write(confirmation)

        self.research.authorship_confirmation = confirmation
        print(f"Authorship confirmation written to: {self.authorship_confirmation_path}")
        return confirmation

    def _require_authorship_confirmation(self) -> str:
        confirmation = self._load_authorship_confirmation()
        if confirmation.strip():
            return confirmation

        raise AuthorshipConfirmationError(
            "Paper generation requires explicit human sign-off. "
            "Review the generated artifacts, then call "
            "confirm_authorship(summary=...) before get_paper()."
        )

    def _candidate_file_for_kind(self, kind: str) -> str:
        if kind == "idea":
            return IDEA_CANDIDATES_FILE
        if kind == "method":
            return METHOD_CANDIDATES_FILE
        raise ValueError("Candidate kind must be either 'idea' or 'method'.")

    def _comparison_file_for_kind(self, kind: str) -> str:
        if kind == "idea":
            return IDEA_COMPARISON_FILE
        if kind == "method":
            return METHOD_COMPARISON_FILE
        raise ValueError("Comparison kind must be either 'idea' or 'method'.")

    def _candidate_attr_for_kind(self, kind: str) -> str:
        if kind == "idea":
            return "idea_candidates"
        if kind == "method":
            return "method_candidates"
        raise ValueError("Candidate kind must be either 'idea' or 'method'.")

    def _selected_setter_for_kind(self, kind: str):
        if kind == "idea":
            return self.set_idea
        if kind == "method":
            return self.set_method
        raise ValueError("Candidate kind must be either 'idea' or 'method'.")

    def _ensure_data_description_loaded(self) -> str:
        if not self.research.data_description:
            self.set_data_description()
        return self.research.data_description

    def _ensure_idea_loaded(self) -> str:
        if not self.research.idea:
            self.set_idea()
        return self.research.idea

    def _serialize_candidates(self, kind: str, candidates: list[str]) -> str:
        kind_title = "Idea" if kind == "idea" else "Method"
        sections = [f"# {kind_title} Candidates", ""]
        for index, candidate in enumerate(candidates, start=1):
            sections.extend(
                [
                    f"## Candidate {index}",
                    "",
                    candidate.strip(),
                    "",
                ]
            )
        return "\n".join(sections).strip() + "\n"

    def _parse_candidates(self, text: str) -> list[str]:
        matches = re.findall(
            r"(?ms)^## Candidate \d+\s*\n(.*?)(?=^## Candidate \d+\s*\n|\Z)",
            text.strip(),
        )
        candidates = [match.strip() for match in matches if match.strip()]
        if candidates:
            return candidates
        text = text.strip()
        return [text] if text else []

    def _set_candidates(self, kind: str, candidates: list[str] | str | None) -> list[str]:
        path = os.path.join(
            self.project_dir, INPUT_FILES, self._candidate_file_for_kind(kind)
        )

        if candidates is None:
            with open(path, 'r') as f:
                text = f.read()
            parsed = self._parse_candidates(text)
        elif isinstance(candidates, str):
            parsed = self._parse_candidates(input_check(candidates))
        else:
            parsed = []
            for candidate in candidates:
                cleaned = input_check(candidate).strip()
                if cleaned:
                    parsed.append(cleaned)

        if not parsed:
            raise ValueError(f"No {kind} candidates were provided.")

        with open(path, 'w') as f:
            f.write(self._serialize_candidates(kind, parsed))

        setattr(self.research, self._candidate_attr_for_kind(kind), parsed)
        return parsed

    def _load_candidates(self, kind: str) -> list[str]:
        attr = self._candidate_attr_for_kind(kind)
        cached = getattr(self.research, attr)
        if cached:
            return cached

        path = os.path.join(
            self.project_dir, INPUT_FILES, self._candidate_file_for_kind(kind)
        )
        with open(path, 'r') as f:
            parsed = self._parse_candidates(f.read())
        setattr(self.research, attr, parsed)
        return parsed

    def _branch_workspace_root(self, kind: str) -> Path:
        folder = "ideas" if kind == "idea" else "methods"
        return Path(self.project_dir) / BRANCH_WORKSPACES_DIR / folder

    def _prepare_branch_runner(self, branch_dir: Path):
        runner = self.__class__(project_dir=str(branch_dir), clear_project_dir=True)
        runner.set_data_description(self._ensure_data_description_loaded())
        if self.research.researcher_statement:
            runner.set_researcher_statement(self.research.researcher_statement)
        return runner

    def set_data_description(self, data_description: str | None = None) -> None:
        """
        Set the description of the data and tools to be used by the agents.

        Args:
            data_description: String or path to markdown file including the description of the tools and data. If None, assume that a `data_description.md` is present in `project_dir/input_files`.
        """

        self.research.data_description = self.setter(data_description, DESCRIPTION_FILE)

        check_file_paths(self.research.data_description)

    def set_researcher_statement(self, researcher_statement: str | None = None) -> None:
        """Set the user's framing, stance, or non-negotiable perspective for paper writing."""

        self.research.researcher_statement = self.setter(
            researcher_statement, RESEARCHER_STATEMENT_FILE
        )

    def set_idea_candidates(self, idea_candidates: list[str] | str | None = None) -> None:
        """Persist multiple idea candidates for later comparison and selection."""

        self.research.idea_candidates = self._set_candidates("idea", idea_candidates)

    def set_method_candidates(self, method_candidates: list[str] | str | None = None) -> None:
        """Persist multiple methodology candidates for later comparison and selection."""

        self.research.method_candidates = self._set_candidates("method", method_candidates)

    def generate_idea_branches(self, count: int = 3, **kwargs) -> list[str]:
        """Generate multiple idea branches without overwriting the selected idea."""

        if count < 2:
            raise ValueError("Idea branching requires at least 2 candidates.")

        branch_root = self._branch_workspace_root("idea")
        if branch_root.exists():
            shutil.rmtree(branch_root)
        branch_root.mkdir(parents=True, exist_ok=True)

        candidates: list[str] = []
        for index in range(1, count + 1):
            branch_dir = branch_root / f"idea_branch_{index:02d}"
            runner = self._prepare_branch_runner(branch_dir)
            runner.get_idea(**kwargs)
            if not runner.research.idea:
                runner.set_idea()
            candidates.append(runner.research.idea)

        self.set_idea_candidates(candidates)
        self.build_idea_comparison()
        return candidates

    def generate_method_branches(self, count: int = 3, **kwargs) -> list[str]:
        """Generate multiple methodology branches using the currently selected idea."""

        if count < 2:
            raise ValueError("Method branching requires at least 2 candidates.")

        selected_idea = self._ensure_idea_loaded()

        branch_root = self._branch_workspace_root("method")
        if branch_root.exists():
            shutil.rmtree(branch_root)
        branch_root.mkdir(parents=True, exist_ok=True)

        candidates: list[str] = []
        for index in range(1, count + 1):
            branch_dir = branch_root / f"method_branch_{index:02d}"
            runner = self._prepare_branch_runner(branch_dir)
            runner.set_idea(selected_idea)
            runner.get_method(**kwargs)
            if not runner.research.methodology:
                runner.set_method()
            candidates.append(runner.research.methodology)

        self.set_method_candidates(candidates)
        self.build_method_comparison()
        return candidates

    def build_idea_comparison(self, criteria: list[str] | None = None) -> str:
        """Write a human-first comparison template for idea branches."""

        return self._build_comparison("idea", criteria=criteria)

    def build_method_comparison(self, criteria: list[str] | None = None) -> str:
        """Write a human-first comparison template for method branches."""

        return self._build_comparison("method", criteria=criteria)

    def _build_comparison(self, kind: str, criteria: list[str] | None = None) -> str:
        candidates = self._load_candidates(kind)
        kind_title = "Idea" if kind == "idea" else "Method"
        criteria = criteria or [
            "Novelty or differentiation",
            "Feasibility with the available data and tools",
            "Clarity and scientific defensibility",
            "Fit with the intended paper contribution",
        ]

        lines = [
            f"# {kind_title} Comparison",
            "",
            f"Use this file to compare candidate {kind.lower()} branches before selecting one.",
            "",
            "## Criteria",
            "",
        ]
        lines.extend([f"- {criterion}" for criterion in criteria])
        lines.extend(["", "## Decision", "", "- Selected candidate: ", "- Why: ", ""])

        for index, candidate in enumerate(candidates, start=1):
            lines.extend(
                [
                    f"## Candidate {index}",
                    "",
                    "### Strengths",
                    "",
                    "### Risks",
                    "",
                    "### Notes",
                    "",
                    "### Candidate Text",
                    "",
                    candidate.strip(),
                    "",
                ]
            )

        comparison = "\n".join(lines).strip() + "\n"
        path = os.path.join(
            self.project_dir, INPUT_FILES, self._comparison_file_for_kind(kind)
        )
        with open(path, 'w') as f:
            f.write(comparison)
        return comparison

    def select_idea_candidate(self, index: int) -> str:
        """Select one idea candidate as the active idea artifact."""

        return self._select_candidate("idea", index)

    def select_method_candidate(self, index: int) -> str:
        """Select one methodology candidate as the active methods artifact."""

        return self._select_candidate("method", index)

    def _select_candidate(self, kind: str, index: int) -> str:
        candidates = self._load_candidates(kind)
        if index < 1 or index > len(candidates):
            raise IndexError(
                f"{kind.title()} candidate index must be between 1 and {len(candidates)}."
            )

        candidate = candidates[index - 1]
        setter = self._selected_setter_for_kind(kind)
        setter(candidate)
        return candidate

    def set_idea(self, idea: str | None = None) -> None:
        """Manually set an idea, either directly from a string or providing the path of a markdown file with the idea."""

        self.research.idea = self.setter(idea, IDEA_FILE)

    def set_method(self, method: str | None = None) -> None:
        """Manually set methods, either directly from a string or providing the path of a markdown file with the methods."""
        
        self.research.methodology = self.setter(method, METHOD_FILE)

    def set_results(self, results: str | None = None) -> None:
        """Manually set the results, either directly from a string or providing the path of a markdown file with the results."""
        
        self.research.results = self.setter(results, RESULTS_FILE)

    def set_plots(self, plots: list[str] | list[Image.Image] | None = None) -> None:
        """Manually set the plots from their path."""

        provided_plots = plots is not None

        if plots is None:
            plots = [str(p) for p in (Path(self.project_dir) / "input_files" / "Plots").glob("*.png")]

        for i, plot in enumerate(plots):
            if isinstance(plot,str):
                plot_path= Path(plot)
                img = Image.open(plot_path)
                plot_name = str(plot_path.name)
            else:
                img = plot
                plot_name = f"plot_{i}.png"
            
            img.save( os.path.join(self.project_dir, INPUT_FILES, PLOTS_FOLDER, plot_name) )

        if provided_plots:
            self._invalidate_authorship_confirmation()

    def set_all(self) -> None:
        """Set all Research fields if present in the working directory"""

        for setter in (
            self.set_data_description,
            self.set_researcher_statement,
            self.set_idea_candidates,
            self.set_idea,
            self.set_method_candidates,
            self.set_method,
            self.set_results,
            self.set_plots,
        ):
            try:
                setter()
            except FileNotFoundError:
                pass

    #---
    # Printers
    #---

    def printer(self, content: str) -> None:
        """Method to show the content depending on the execution environment, whether Jupyter notebook or Python script."""

        if self.run_in_notebook:
            from IPython.display import display, Markdown
            display(Markdown(content))
        else:
            print(content)

    def show_data_description(self) -> None:
        """Show the data description set by the `set_data_description` method."""

        self.printer(self.research.data_description)

    def show_idea(self) -> None:
        """Show the provided or generated idea by the `set_idea` or `get_idea` methods."""
        
        self.printer(self.research.idea)

    def show_researcher_statement(self) -> None:
        """Show the provided researcher statement."""

        self.printer(self.research.researcher_statement)

    def show_idea_candidates(self) -> None:
        """Show the stored idea candidates."""

        self.printer(self._serialize_candidates("idea", self._load_candidates("idea")))

    def show_method_candidates(self) -> None:
        """Show the stored method candidates."""

        self.printer(self._serialize_candidates("method", self._load_candidates("method")))

    def show_method(self) -> None:
        """Show the provided or generated methods by `set_method` or `get_method`."""

        self.printer(self.research.methodology)

    def show_results(self) -> None:
        """Show the obtained results."""

        self.printer(self.research.results)

    def show_keywords(self) -> None:
        """Show the keywords."""

        print(self.research.keywords)

        if isinstance(self.research.keywords, dict):
            # Handle dict format (AAS keywords with URLs)
            keyword_list = "\n".join(
                                [f"- [{keyword}]({self.research.keywords[keyword]})" for keyword in self.research.keywords]
                            )
        else:
            # Handle list format (UNESCO keywords)
            keyword_list = "\n".join([f"- {keyword}" for keyword in self.research.keywords])
        
        self.printer(keyword_list)

    #---
    # Generative modules
    #---

    def enhance_data_description(self,
                                 summarizer_model: str, 
                                 summarizer_response_formatter_model: str) -> None:
        """
        Enhance the data description using the preprocess_task from cmbagent.

        Args:
            summarizer_model: LLM to be used for summarization.
            summarizer_response_formatter_model: LLM to be used for formatting the summarization response.
        """

        # Check if data description exists
        if not hasattr(self.research, 'data_description') or not self.research.data_description:
            # Try to load from file if it exists
            try:
                with open(os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE), 'r') as f:
                    self.research.data_description = f.read()
            except FileNotFoundError:
                raise ValueError("No data description found. Please set a data description first before enhancing it.")

        # Get the enhanced text from preprocess_task
        enhanced_text = preprocess_task(self.research.data_description,
                                        work_dir = self.project_dir,
                                        summarizer_model = summarizer_model,
                                        summarizer_response_formatter_model = summarizer_response_formatter_model
                                        )
        
        # Debug: Check if the enhanced text is different from original
        print(f"Original text length: {len(self.research.data_description)}")
        print(f"Enhanced text length: {len(enhanced_text)}")
        print(f"Texts are different: {self.research.data_description != enhanced_text}")
        
        # If the enhanced text is the same as original, try reading from enhanced_input.md
        if self.research.data_description == enhanced_text:
            enhanced_input_path = os.path.join(self.project_dir, "enhanced_input.md")
            if os.path.exists(enhanced_input_path):
                print("Reading enhanced content from enhanced_input.md")
                with open(enhanced_input_path, 'r', encoding='utf-8') as f:
                    enhanced_text = f.read()
                print(f"Enhanced text from file length: {len(enhanced_text)}")
        
        # Update the research object with enhanced text
        previous_data_description = self.research.data_description
        self.research.data_description = enhanced_text

        # Create the input_files directory if it doesn't exist
        input_files_dir = os.path.join(self.project_dir, INPUT_FILES)
        if not os.path.exists(input_files_dir):
            os.makedirs(input_files_dir, exist_ok=True)

        # Write the enhanced text to data_description.md
        with open(os.path.join(input_files_dir, DESCRIPTION_FILE), 'w', encoding='utf-8') as f:
            f.write(enhanced_text)

        # set the enhanced text to the research object
        self.research.data_description = enhanced_text

        if previous_data_description != enhanced_text:
            self._invalidate_authorship_confirmation()
            
        print(f"Enhanced text written to: {os.path.join(input_files_dir, DESCRIPTION_FILE)}")

    def get_idea(self,
                 mode = "fast",
                 llm: LLM | str = models["gemini-2.0-flash"],
                 idea_maker_model: LLM | str = models["gpt-4o"],
                 idea_hater_model: LLM | str = models["o3-mini"],
                 planner_model: LLM | str = models["gpt-4o"],
                 plan_reviewer_model: LLM | str = models["o3-mini"],
                 orchestration_model: LLM | str = models["gpt-4.1"],
                 formatter_model: LLM | str = models["o3-mini"],
                ) -> None:
        """Generate an idea making use of the data and tools described in `data_description.md`.

        Args:
            mode: either "fast" or "cmbagent". Fast mode uses langgraph backend and is faster but less reliable. Cmbagent mode uses cmbagent backend and is slower but more reliable.
            llm: the LLM to be used for the fast mode.
            idea_maker_model: the LLM to be used for the idea maker agent.
            idea_hater_model: the LLM to be used for the idea hater agent.
            planner_model: the LLM to be used for the planner agent.
            plan_reviewer_model: the LLM to be used for the plan reviewer agent.
            orchestration_model: the LLM to be used for the orchestration of the agents.
            formatter_model: the LLM to be used for formatting the responses of the agents.
        """

        print(f"Generating idea with {mode} mode")

        if mode == "fast":
            self.get_idea_fast(llm=llm)
        elif mode == "cmbagent":
            self.get_idea_cmagent(idea_maker_model=idea_maker_model,
                                  idea_hater_model=idea_hater_model,
                                  planner_model=planner_model,
                                  plan_reviewer_model=plan_reviewer_model,
                                  orchestration_model=orchestration_model,
                                  formatter_model=formatter_model)
        else:
            raise ValueError("Mode must be either 'fast' or 'cmbagent'")

    def get_idea_cmagent(self,
                    idea_maker_model: LLM | str = models["gpt-4o"],
                    idea_hater_model: LLM | str = models["o3-mini"],
                    planner_model: LLM | str = models["gpt-4o"],
                    plan_reviewer_model: LLM | str = models["o3-mini"],
                    orchestration_model: LLM | str = models["gpt-4.1"],
                    formatter_model: LLM | str = models["o3-mini"],
                ) -> None:
        """Generate an idea making use of the data and tools described in `data_description.md` with the cmbagent backend.
        
        Args:
            idea_maker_model: the LLM to be used for the idea maker agent.
            idea_hater_model: the LLM to be used for the idea hater agent.
            planner_model: the LLM to be used for the planner agent.
            plan_reviewer_model: the LLM to be used for the plan reviewer agent.
            orchestration_model: the LLM to be used for the orchestration of the agents.
            formatter_model: the LLM to be used for formatting the responses of the agents.
        """

        # Get LLM instances
        idea_maker_model = llm_parser(idea_maker_model)
        idea_hater_model = llm_parser(idea_hater_model)
        planner_model = llm_parser(planner_model)
        plan_reviewer_model = llm_parser(plan_reviewer_model)
        orchestration_model = llm_parser(orchestration_model)
        formatter_model = llm_parser(formatter_model)
        
        if self.research.data_description == "":
            with open(os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE), 'r') as f:
                self.research.data_description = f.read()

        idea = Idea(work_dir = self.project_dir,
                    idea_maker_model = idea_maker_model.name,
                    idea_hater_model = idea_hater_model.name,
                    planner_model = planner_model.name,
                    plan_reviewer_model = plan_reviewer_model.name,
                    keys=self.keys,
                    orchestration_model = orchestration_model.name,
                    formatter_model = formatter_model.name)
        
        idea = idea.develop_idea(self.research.data_description)
        self.research.idea = idea
        # Write idea to file
        idea_path = os.path.join(self.project_dir, INPUT_FILES, IDEA_FILE)
        with open(idea_path, 'w') as f:
            f.write(idea)

        self.idea = idea
        self._invalidate_authorship_confirmation()

    def get_idea_fast(self,
                      llm: LLM | str = models["gemini-2.0-flash"],
                      iterations: int = 4,
                      verbose=False,
                      ) -> None:
        """
        Generate an idea using the idea maker - idea hater method.
        
        Args:
            llm: the LLM model to be used
            verbose: whether to stream the LLM response
        """

        # Start timer
        start_time = time.time()
        config = {"configurable": {"thread_id": "1"}, "recursion_limit":100}

        # Get LLM instance
        llm = llm_parser(llm)

        # Build graph
        graph = build_lg_graph(mermaid_diagram=False)

        # get name of data description file
        f_data_description = os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE)

        # Initialize the state
        input_state = {
            "task": "idea_generation",
            "files":{"Folder": self.project_dir,
                     "data_description": f_data_description}, #name of project folder
            "llm": {"model": llm.name,                #name of the LLM model to use
                    "temperature": llm.temperature,
                    "max_output_tokens": llm.max_output_tokens,
                    "stream_verbose": verbose},
            "keys": self.keys,
            "idea": {"total_iterations": iterations},
        }
        
        # Run the graph
        graph.invoke(input_state, config) # type: ignore
        
        # End timer and report duration in minutes and seconds
        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        print(f"Idea generated in {minutes} min {seconds} sec.")
        self._invalidate_authorship_confirmation()

    def check_idea(self,
                   mode : str = 'semantic_scholar',
                   llm: LLM | str = models["gemini-2.5-flash"],
                   max_iterations: int = 7,
                   verbose=False) -> str:
        """
        Use Futurehouse or Semantic Scholar to check the idea against previous literature

        Args:
            mode: either 'futurehouse' or 'semantic_scholar'
            llm: the LLM model to be used
            max_iterations: maximum number of iterations to search for literature
            verbose: whether to stream the LLM response
        """

        print(f"Checking idea in literature with {mode} mode")

        if mode == 'futurehouse':
            return self.check_idea_futurehouse()

        elif mode == 'semantic_scholar':

            return self.check_idea_semantic_scholar(llm=llm, max_iterations=max_iterations, verbose=verbose)
        
        else:
            raise ValueError("Mode must be either 'futurehouse' or 'semantic_scholar'")
    
    def check_idea_futurehouse(self) -> str:
        """
        Check with the literature if an idea is original or not.
        """

        from futurehouse_client import FutureHouseClient, JobNames
        from futurehouse_client.models import (
            TaskRequest,
        )
        import os
        fhkey = os.getenv("FUTURE_HOUSE_API_KEY")

        fh_client = FutureHouseClient(
            api_key=fhkey,
        )

        check_idea_prompt = rf"""
        Has anyone worked on or explored the following idea?

        {self.research.idea}
        
        <DESIRED_RESPONSE_FORMAT>
        Answer: <yes or no>

        Related previous work: <describe previous literature on the topic>
        </DESIRED_RESPONSE_FORMAT>
        """
        task_data = TaskRequest(name=JobNames.from_string("owl"),
                                query=check_idea_prompt)
        
        task_response = fh_client.run_tasks_until_done(task_data)

        answer = task_response[0].formatted_answer # type: ignore

        ## process the answer to remove everything above </DESIRED_RESPONSE_FORMAT> 
        answer = answer.split("</DESIRED_RESPONSE_FORMAT>")[1]

        # prepend " Has anyone worked on or explored the following idea?" to the answer
        answer = "Has anyone worked on or explored the following idea?\n" + answer

        ## save the response into {INPUT_FILES}/{LITERATURE_FILE}
        with open(os.path.join(self.project_dir, INPUT_FILES, LITERATURE_FILE), 'w') as f:
            f.write(answer)

        return answer

    def check_idea_semantic_scholar(self,
                        llm: LLM | str = models["gemini-2.5-flash"],
                        max_iterations: int = 7,
                        verbose=False,
                        ) -> str:
        """
        Check with the literature if an idea is original or not.

        Args:
           llm: the LLM model to be used
           max_iterations: maximum number of iterations to check the idea
           verbose: whether to stream the LLM response 
        """

        # Start timer
        start_time = time.time()
        config = {"configurable": {"thread_id": "1"}, "recursion_limit":100}

        # Get LLM instance
        llm = llm_parser(llm)

        # Build graph
        graph = build_lg_graph(mermaid_diagram=False)

        # get name of data description and idea files
        f_data_description = os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE)
        f_idea             = os.path.join(self.project_dir, INPUT_FILES, IDEA_FILE)

        # Initialize the state
        input_state = {
            "task": "literature",
            "files":{"Folder": self.project_dir, #name of project folder
                     "data_description": f_data_description,
                     "idea": f_idea}, 
            "llm": {"model": llm.name,                #name of the LLM model to use
                    "temperature": llm.temperature,
                    "max_output_tokens": llm.max_output_tokens,
                    "stream_verbose": verbose},
            "keys": self.keys,
            "literature": {"max_iterations": max_iterations},
            "idea": {"total_iterations": 4},
        }
        
        # Run the graph
        try:
            graph.invoke(input_state, config) # type: ignore
            
            # End timer and report duration in minutes and seconds
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            print(f"Literature checked in {minutes} min {seconds} sec.")
            
        except Exception as e:
            print('Denario failed to check literature')
            print(f'Error: {e}')
            return "Error occurred during literature check"

        # Read and return the generated literature content
        try:
            literature_file = os.path.join(self.project_dir, INPUT_FILES, LITERATURE_FILE)
            with open(literature_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "Literature file not found"
        
    def get_method(self,
                   mode = "fast",
                   llm: LLM | str = models["gemini-2.0-flash"],
                   method_generator_model: LLM | str = models["gpt-4o"],
                   planner_model: LLM | str = models["gpt-4o"],
                   plan_reviewer_model: LLM | str = models["o3-mini"],
                   orchestration_model: LLM | str = models["gpt-4.1"],
                   formatter_model: LLM | str = models["o3-mini"],
                   verbose = False,
                   ) -> None:
        """
        Generate the methods to be employed making use of the data and tools described in `data_description.md` and the idea in `idea.md`.
        
        Args:
            mode: either "fast" or "cmbagent". Fast mode uses langgraph backend and is faster but less reliable. Cmbagent mode uses cmbagent backend and is slower but more reliable.
            llm: the LLM to be used for the fast mode.
            method_generator_model: (researcher) the LLM model to be used for the researcher agent.
            planner_model: the LLM model to be used for the planner agent.
            plan_reviewer_model: the LLM model to be used for the plan reviewer agent.
            orchestration_model: the LLM to be used for the orchestration of the agents.
            formatter_model: the LLM to be used for formatting the responses of the agents.
        """

        print(f"Generating methodology with {mode} mode")

        if mode == "fast":
            self.get_method_fast(llm=llm, verbose=verbose)
        elif mode == "cmbagent":
            self.get_method_cmbagent(method_generator_model=method_generator_model,
                                     planner_model=planner_model,
                                     plan_reviewer_model=plan_reviewer_model,
                                     orchestration_model=orchestration_model,
                                     formatter_model=formatter_model)
        else:
            raise ValueError("Mode must be either 'fast' or 'cmbagent'")

    def get_method_cmbagent(self,
                            method_generator_model: LLM | str = models["gpt-4o"],
                            planner_model: LLM | str = models["gpt-4o"],
                            plan_reviewer_model: LLM | str = models["o3-mini"],
                            orchestration_model: LLM | str = models["gpt-4.1"],
                            formatter_model: LLM | str = models["o3-mini"],
                            ) -> None:
        """
        Generate the methods to be employed making use of the data and tools described in `data_description.md` and the idea in `idea.md`.
        
        Args:
            method_generator_model: (researcher) the LLM model to be used for the researcher agent.
            planner_model: the LLM model to be used for the planner agent.
            plan_reviewer_model: the LLM model to be used for the plan reviewer agent.
            orchestration_model: the LLM to be used for the orchestration of the agents.
            formatter_model: the LLM to be used for formatting the responses of the agents.
        """

        if self.research.data_description == "":
            with open(os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE), 'r') as f:
                self.research.data_description = f.read()        

        if self.research.idea == "":
            with open(os.path.join(self.project_dir, INPUT_FILES, IDEA_FILE), 'r') as f:
                self.research.idea = f.read()

        method_generator_model = llm_parser(method_generator_model)
        planner_model = llm_parser(planner_model)
        plan_reviewer_model = llm_parser(plan_reviewer_model)
        orchestration_model = llm_parser(orchestration_model)
        formatter_model = llm_parser(formatter_model)

        method = Method(self.research.idea, keys=self.keys,  
                        work_dir = self.project_dir, 
                        researcher_model=method_generator_model.name, 
                        planner_model=planner_model.name, 
                        plan_reviewer_model=plan_reviewer_model.name,
                        orchestration_model = orchestration_model.name,
                        formatter_model = formatter_model.name)
        
        methododology = method.develop_method(self.research.data_description)
        self.research.methodology = methododology

        # Write idea to file
        method_path = os.path.join(self.project_dir, INPUT_FILES, METHOD_FILE)
        with open(method_path, 'w') as f:
            f.write(methododology)
        self._invalidate_authorship_confirmation()

    def get_method_fast(self,
                        llm: LLM | str = models["gemini-2.0-flash"],
                        verbose=False,
                        ) -> None:
        """
        Generate the methods to be employed making use of the data and tools described in `data_description.md` and the idea in `idea.md`. Faster version get_method.
        
        Args:
           llm: the LLM model to be used
           verbose: whether to stream the LLM response
        """

        # Start timer
        start_time = time.time()
        config = {"configurable": {"thread_id": "1"}, "recursion_limit":100}

        # Get LLM instance
        llm = llm_parser(llm)

        # Build graph
        graph = build_lg_graph(mermaid_diagram=False)

        # get name of data description file and idea
        f_data_description = os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE)
        f_idea = os.path.join(self.project_dir, INPUT_FILES, IDEA_FILE)
        
        # Initialize the state
        input_state = {
            "task": "methods_generation",
            "files":{"Folder": self.project_dir,              #name of project folder
                     "data_description": f_data_description,
                     "idea": f_idea}, 
            "llm": {"model": llm.name,                #name of the LLM model to use
                    "temperature": llm.temperature,
                    "max_output_tokens": llm.max_output_tokens,
                    "stream_verbose": verbose},
            "keys": self.keys,
            "idea": {"total_iterations": 4},
        }
        
        # Run the graph
        graph.invoke(input_state, config) # type: ignore
        
        # End timer and report duration in minutes and seconds
        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        print(f"Methods generated in {minutes} min {seconds} sec.")  
        self._invalidate_authorship_confirmation()

    def get_results(self,
                    involved_agents: List[str] = ['engineer', 'researcher'],
                    engineer_model: LLM | str = models["gpt-4.1"],
                    researcher_model: LLM | str = models["o3-mini"],
                    restart_at_step: int = -1,
                    hardware_constraints: str | None = None,
                    planner_model: LLM | str = models["gpt-4o"],
                    plan_reviewer_model: LLM | str = models["o3-mini"],
                    max_n_attempts: int = 10,
                    max_n_steps: int = 6,   
                    orchestration_model: LLM | str = models["gpt-4.1"],
                    formatter_model: LLM | str = models["o3-mini"],
                    ) -> None:
        """
        Compute the results making use of the methods, idea and data description.

        Args:
            involved_agents: List of agents employed to compute the results.
            engineer_model: the LLM model to be used for the engineer agent.
            researcher_model: the LLM model to be used for the researcher agent.
            restart_at_step: the step to restart the experiment.
            hardware_constraints: the hardware constraints to be used for the experiment.
            planner_model: the LLM model to be used for the planner agent.
            plan_reviewer_model: the LLM model to be used for the plan reviewer agent.
            orchestration_model: the LLM model to be used for the orchestration of the agents.
            formatter_model: the LLM model to be used for the formatting of the responses of the agents.
            max_n_attempts: the maximum number of attempts to execute code within one step if the code execution fails.
            max_n_steps: the maximum number of steps in the workflow.
        """

        # Get LLM instances
        engineer_model = llm_parser(engineer_model)
        researcher_model = llm_parser(researcher_model)
        planner_model = llm_parser(planner_model)
        plan_reviewer_model = llm_parser(plan_reviewer_model)
        orchestration_model = llm_parser(orchestration_model)
        formatter_model = llm_parser(formatter_model)

        if self.research.data_description == "":
            with open(os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE), 'r') as f:
                self.research.data_description = f.read()

        if self.research.idea == "":
            with open(os.path.join(self.project_dir, INPUT_FILES, IDEA_FILE), 'r') as f:
                self.research.idea = f.read()

        if self.research.methodology == "":
            with open(os.path.join(self.project_dir, INPUT_FILES, METHOD_FILE), 'r') as f:
                self.research.methodology = f.read()

        experiment = Experiment(research_idea=self.research.idea,
                                methodology=self.research.methodology,
                                involved_agents=involved_agents,
                                engineer_model=engineer_model.name,
                                researcher_model=researcher_model.name,
                                planner_model=planner_model.name,
                                plan_reviewer_model=plan_reviewer_model.name,
                                work_dir = self.project_dir,
                                keys=self.keys,
                                restart_at_step = restart_at_step,
                                hardware_constraints = hardware_constraints,
                                max_n_attempts=max_n_attempts,
                                max_n_steps=max_n_steps,
                                orchestration_model = orchestration_model.name,
                                formatter_model = formatter_model.name)
        
        experiment.run_experiment(self.research.data_description)
        self.research.results = experiment.results
        self.research.plot_paths = experiment.plot_paths

        # Move plots to the plots folder in input_files/plots.
        # Some cmbagent runs return plot paths but leave the destination missing;
        # guard against that so plots always land in a directory, never a file path.
        if os.path.isfile(self.plots_folder):
            os.remove(self.plots_folder)
        os.makedirs(self.plots_folder, exist_ok=True)

        # Clear any previous plot outputs.
        if os.path.exists(self.plots_folder):
            for file in os.listdir(self.plots_folder):
                file_path = os.path.join(self.plots_folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        for plot_path in self.research.plot_paths:
            if os.path.exists(plot_path):
                destination = os.path.join(self.plots_folder, os.path.basename(plot_path))
                shutil.move(plot_path, destination)

        # Write results to file
        results_path = os.path.join(self.project_dir, INPUT_FILES, RESULTS_FILE)
        with open(results_path, 'w') as f:
            f.write(self.research.results)
        self._invalidate_authorship_confirmation()
    
    def get_keywords(self, input_text: str, n_keywords: int = 5, kw_type: str = 'unesco') -> None:
        """
        Get keywords from input text using cmbagent.

        Args:
            input_text (str): Text to extract keywords from
            n_keywords (int, optional): Number of keywords to extract. Defaults to 5.
            kw_type (str, optional): Type of keywords to extract. Defaults to 'unesco'.

        Returns:
            dict: Dictionary mapping keywords to their URLs
        """
        
        keywords = cmbagent.get_keywords(input_text, n_keywords = n_keywords, kw_type = kw_type, api_keys = self.keys)
        self.research.keywords = keywords # type: ignore
        print('keywords: ', self.research.keywords)

    def get_paper(self,
                  journal: Journal = Journal.NONE,
                  llm: LLM | str = models["gemini-2.5-flash"],
                  writer: str = 'scientist',
                  cmbagent_keywords: bool = False,
                  add_citations=True,
                  require_authorship_confirmation: bool = True,
                  ) -> None:
        """
        Generate a full paper based on the files in input_files:

            - idea.md
            - methods.md
            - results.md
            - plots

        Different journals considered

            - NONE = None : No journal, use standard latex presets with unsrt for bibliography style.
            - AAS  = "AAS" : American Astronomical Society journals, including the Astrophysical Journal.
            - APS = "APS" : Physical Review Journals from the American Physical Society, including Physical Review Letters, PRA, etc.
            - ICML = "ICML" : ICML - International Conference on Machine Learning.
            - JHEP = "JHEP" : Journal of High Energy Physics, including JHEP, JCAP, etc.
            - NeurIPS = "NeurIPS" : NeurIPS - Conference on Neural Information Processing Systems.
            - PASJ = "PASJ" : Publications of the Astronomical Society of Japan.

        Args:
            journal: Journal style. The paper generation will use the presets of the journal considered for the latex writing. Default is no journal (no specific presets).
            llm: The LLM model to be used to write the paper.
            writer: set the style and tone to write. E.g. astrophysicist, biologist, chemist
            cmbagent_keywords: whether to use CMBAgent to select the keywords
            add_citations: whether to add citations to the paper or not
            require_authorship_confirmation: require explicit human review before paper writing
        """

        if require_authorship_confirmation:
            self._require_authorship_confirmation()
        
        # Start timer
        start_time = time.time()
        config = {"configurable": {"thread_id": "1"}, "recursion_limit":100}

        # Get LLM instance
        llm = llm_parser(llm)

        # Build graph
        graph = build_graph(mermaid_diagram=False)

        # Initialize the state
        input_state = {
            "files":{"Folder": self.project_dir}, #name of project folder
            "llm": {"model": llm.name,  #name of the LLM model to use
                    "temperature": llm.temperature,
                    "max_output_tokens": llm.max_output_tokens},
            "paper":{"journal": journal, "add_citations": add_citations,
                     "cmbagent_keywords": cmbagent_keywords},
            "keys": self.keys,
            "writer": writer,
        }

        # Run the graph
        asyncio.run(graph.ainvoke(input_state, config)) # type: ignore
        
        # End timer and report duration in minutes and seconds
        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        print(f"Paper written in {minutes} min {seconds} sec.")    

    def referee(self,
                llm: LLM | str = models["gemini-2.5-flash"],
                verbose=False) -> None:
        """
        Review a paper, producing a report providing feedback on the quality of the articled and aspects to be improved.

        Args:
           llm: the LLM model to be used
           verbose: whether to stream the LLM response 
        """

        # Start timer
        start_time = time.time()
        config = {"configurable": {"thread_id": "1"}, "recursion_limit":100}

        # Get LLM instance
        llm = llm_parser(llm)

        # Build graph
        graph = build_lg_graph(mermaid_diagram=False)

        # get name of data description file and referee
        f_data_description = os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE)

        # Initialize the state
        input_state = {
            "task": "referee",
            "files":{"Folder": self.project_dir,  #name of project folder
                     "data_description": f_data_description}, 
            "llm": {"model": llm.name,                #name of the LLM model to use
                    "temperature": llm.temperature,
                    "max_output_tokens": llm.max_output_tokens,
                    "stream_verbose": verbose},
            "keys": self.keys,
            "referee": {"paper_version": 2},
        }
        
        # Run the graph
        try:
            graph.invoke(input_state, config) # type: ignore
            
            # End timer and report duration in minutes and seconds
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            print(f"Paper reviewed in {minutes} min {seconds} sec.")
            
        except FileNotFoundError as e:
            print('Denario failed to provide a review for the paper. Ensure that a paper in the `paper` folder ex')
            print(f'Error: {e}')
        
    def research_pilot(self, data_description: str | None = None) -> None:
        """Full run of Denario. It calls the following methods sequentially:
        ```
        set_data_description(data_description)
        get_idea()
        get_method()
        get_results()
        get_paper()
        ```
        """

        self.set_data_description(data_description)
        self.get_idea()
        self.get_method()
        self.get_results()
        try:
            self.get_paper()
        except AuthorshipConfirmationError as exc:
            print(exc)
            print(
                "Denario stopped before paper generation. Review the artifacts, call "
                "confirm_authorship(summary=...), then rerun get_paper()."
            )
