import re
from pathlib import Path
import cmbagent

from .key_manager import KeyManager
from .prompts.experiment import experiment_planner_prompt, experiment_engineer_prompt, experiment_researcher_prompt
from .utils import create_work_dir, get_task_result
from .openrouter_config import build_cmbagent_api_keys

class Experiment:
    """
    This class is used to perform the experiment.
    TODO: improve docstring
    """

    def __init__(self,
                 research_idea: str,
                 methodology: str,
                 keys: KeyManager,
                 work_dir: str | Path,
                 involved_agents: list[str] = ['engineer', 'researcher'],
                 engineer_model: str = "gpt-4.1",
                 researcher_model: str = "o3-mini-2025-01-31",
                 planner_model: str = "gpt-4o",
                 plan_reviewer_model: str = "o3-mini",
                 restart_at_step: int = -1,
                 hardware_constraints: str | None = None,
                 max_n_attempts: int = 10,
                 max_n_steps: int = 6,
                 orchestration_model = "gpt-4.1",
                 formatter_model = "o3-mini",
                ):
        
        self.engineer_model = engineer_model
        self.researcher_model = researcher_model
        self.planner_model = planner_model
        self.plan_reviewer_model = plan_reviewer_model
        self.restart_at_step = restart_at_step
        if hardware_constraints is None:
            hardware_constraints = ""
        self.hardware_constraints = hardware_constraints
        self.max_n_attempts = max_n_attempts
        self.max_n_steps = max_n_steps
        self.orchestration_model = orchestration_model
        self.formatter_model = formatter_model

        self.api_keys = keys

        self.experiment_dir = create_work_dir(work_dir, "experiment")

        involved_agents_str = ', '.join(involved_agents)

        # Set prompts
        self.planner_append_instructions = experiment_planner_prompt.format(
            research_idea = research_idea,
            methodology = methodology,
            involved_agents_str = involved_agents_str
        )
        self.engineer_append_instructions = experiment_engineer_prompt.format(
            research_idea = research_idea,
            methodology = methodology,
        )
        self.researcher_append_instructions = experiment_researcher_prompt.format(
            research_idea = research_idea,
            methodology = methodology,
        )

    def run_experiment(self, data_description: str, **kwargs):
        """
        Run the experiment.
        TODO: improve docstring
        """

        print(f"Engineer model: {self.engineer_model}")
        print(f"Researcher model: {self.researcher_model}")
        print(f"Planner model: {self.planner_model}")
        print(f"Plan reviewer model: {self.plan_reviewer_model}")
        print(f"Max n attempts: {self.max_n_attempts}")
        print(f"Max n steps: {self.max_n_steps}")
        print(f"Restart at step: {self.restart_at_step}")
        print(f"Hardware constraints: {self.hardware_constraints}")

        # Check if using OpenRouter (OPENROUTER_API_KEY is set)
        import os
        import cmbagent.utils as cmbagent_utils
        
        use_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
        original_get_model_config = None
        
        if use_openrouter:
            print("Using OpenRouter for all LLM calls...")
            
            # Monkey-patch cmbagent's get_model_config to use OpenRouter
            original_get_model_config = cmbagent_utils.get_model_config
            
            def openrouter_get_model_config(model, api_keys):
                """Patched get_model_config that routes through OpenRouter."""
                from denario.openrouter_config import build_openrouter_config
                return build_openrouter_config(model)
            
            cmbagent_utils.get_model_config = openrouter_get_model_config
            
            # Also patch the module-level reference in cmbagent.cmbagent
            import cmbagent.cmbagent as cmbagent_mod
            cmbagent_mod.get_model_config = openrouter_get_model_config
            
            api_keys = build_cmbagent_api_keys()
        else:
            api_keys = self.api_keys

        try:
            results = cmbagent.planning_and_control_context_carryover(data_description,
                                n_plan_reviews = 1,
                                max_n_attempts = self.max_n_attempts,
                                max_plan_steps = self.max_n_steps,
                                max_rounds_control = 500,
                                engineer_model = self.engineer_model,
                                researcher_model = self.researcher_model,
                                planner_model = self.planner_model,
                                plan_reviewer_model = self.plan_reviewer_model,
                                plan_instructions=self.planner_append_instructions,
                                researcher_instructions=self.researcher_append_instructions,
                                engineer_instructions=self.engineer_append_instructions,
                                work_dir = self.experiment_dir,
                                api_keys = api_keys,
                                restart_at_step = self.restart_at_step,
                                hardware_constraints = self.hardware_constraints,
                                default_llm_model = self.orchestration_model,
                                default_formatter_model = self.formatter_model,
                                )
        finally:
            # Restore original function after call
            if original_get_model_config is not None:
                cmbagent_utils.get_model_config = original_get_model_config
                import cmbagent.cmbagent as cmbagent_mod
                cmbagent_mod.get_model_config = original_get_model_config
        chat_history = results['chat_history']
        final_context = results['final_context']
        
        try:
            # Try to get the result from the researcher formatter first
            task_result = get_task_result(chat_history, 'researcher_response_formatter')
            
            # Fallback to executor formatter if researcher result is missing
            if task_result is None:
                print("Researcher result not found, falling back to executor_response_formatter...")
                task_result = get_task_result(chat_history, 'executor_response_formatter')
            
            if task_result is None:
                raise ValueError("Could not find result in chat history from any formatter (researcher or executor).")
                
        except Exception as e:
            # If we reached this point, we really don't have the task result
            raise e
            
        MD_CODE_BLOCK_PATTERN = r"```[ \t]*(?:markdown)[ \t]*\r?\n(.*)\r?\n[ \t]*```"
        matches = re.findall(MD_CODE_BLOCK_PATTERN, task_result, flags=re.DOTALL)
        if not matches:
             # If no markdown block found in task_result, maybe the whole string is the result or it's formatted differently
             # Try a simpler extraction or use the whole string
             if "##" in task_result:
                 clean_results = re.sub(r'^<!--.*?-->\s*\n', '', task_result)
             else:
                 raise ValueError("Could not find markdown content in the task result.")
        else:
            extracted_results = matches[0]
            clean_results = re.sub(r'^<!--.*?-->\s*\n', '', extracted_results)
        
        self.results = clean_results
        self.plot_paths = final_context['displayed_images']

        return None


