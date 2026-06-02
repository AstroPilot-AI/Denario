defmodule DenarioEx.WorkflowPrompts do
  @moduledoc false

  alias DenarioEx.Text

  @spec cmbagent_plan_prompt(String.t(), map(), [String.t()], pos_integer(), String.t() | nil) ::
          String.t()
  def cmbagent_plan_prompt(task, context, allowed_agents, max_steps, feedback \\ nil) do
    """
    [DENARIO_PLAN][#{task}]
    Build a concise execution plan for this Denario task.

    Allowed agents: #{Enum.join(allowed_agents, ", ")}
    Maximum number of steps: #{max_steps}

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methodology:
    #{Map.get(context, :methodology, "")}

    Existing results:
    #{Map.get(context, :results, "")}

    Planner feedback from a previous review:
    #{feedback || "none"}

    Return a focused plan that uses only the allowed agents. Keep it linear and concrete.
    """
  end

  @spec cmbagent_plan_review_prompt(String.t(), map(), map()) :: String.t()
  def cmbagent_plan_review_prompt(task, context, plan) do
    """
    [DENARIO_PLAN_REVIEW][#{task}]
    Review the proposed execution plan for feasibility and focus.

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methodology:
    #{Map.get(context, :methodology, "")}

    Proposed plan summary:
    #{Map.get(plan, :summary, "")}

    Proposed steps:
    #{render_steps(Map.get(plan, :steps, []))}

    Approve only if the plan is concrete, bounded, and aligned with the task artifacts.
    """
  end

  @spec cmbagent_step_prompt(String.t(), String.t(), map(), map(), [map()]) :: String.t()
  def cmbagent_step_prompt(task, agent, step, context, step_outputs) do
    """
    [DENARIO_CMB_STEP][#{agent}]
    [TASK][#{task}]
    Execute the current Denario workflow step.

    Step id: #{Text.fetch(step, "id")}
    Goal: #{Text.fetch(step, "goal")}
    Deliverable: #{Text.fetch(step, "deliverable")}

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methodology:
    #{Map.get(context, :methodology, "")}

    Existing step outputs:
    #{render_step_outputs(step_outputs)}

    Respond exactly in this format:

    \\begin{STEP_OUTPUT}
    <STEP_OUTPUT>
    \\end{STEP_OUTPUT}
    """
  end

  @spec cmbagent_final_prompt(String.t(), map(), [map()]) :: String.t()
  def cmbagent_final_prompt("idea", context, step_outputs) do
    """
    [DENARIO_CMB_FINAL][idea]
    Turn the step outputs into one final research idea.

    Data description:
    #{Map.get(context, :data_description, "")}

    Step outputs:
    #{render_step_outputs(step_outputs)}

    Respond exactly in this format:

    \\begin{IDEA}
    <IDEA>
    \\end{IDEA}
    """
  end

  def cmbagent_final_prompt("method", context, step_outputs) do
    """
    [DENARIO_CMB_FINAL][method]
    Turn the step outputs into one final project methodology.

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Step outputs:
    #{render_step_outputs(step_outputs)}

    Respond exactly in this format:

    \\begin{METHODS}
    <METHODS>
    \\end{METHODS}
    """
  end

  @spec results_engineer_prompt(map(), map(), [map()], String.t(), String.t()) :: String.t()
  def results_engineer_prompt(step, context, step_outputs, previous_error, hardware_constraints) do
    """
    [DENARIO_RESULTS_ENGINEER]
    Generate Python code for the current experimental step.

    Step id: #{Text.fetch(step, "id")}
    Goal: #{Text.fetch(step, "goal")}
    Deliverable: #{Text.fetch(step, "deliverable")}

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methodology:
    #{Map.get(context, :methodology, "")}

    Previous completed step outputs:
    #{render_step_outputs(step_outputs)}

    Hardware constraints:
    #{if hardware_constraints == "", do: "none", else: hardware_constraints}

    Previous execution error: #{if previous_error == "", do: "none", else: previous_error}

    Return code that prints all quantitative information needed for a scientific results section.
    """
  end

  @spec results_step_summary_prompt(map(), map(), [map()], String.t(), String.t()) :: String.t()
  def results_step_summary_prompt(step, context, step_outputs, engineer_summary, execution_output) do
    """
    [DENARIO_RESULTS_STEP_SUMMARY]
    Summarize the completed experimental step for downstream scientific writing.

    Step id: #{Text.fetch(step, "id")}
    Goal: #{Text.fetch(step, "goal")}
    Deliverable: #{Text.fetch(step, "deliverable")}

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methodology:
    #{Map.get(context, :methodology, "")}

    Previous completed step outputs:
    #{render_step_outputs(step_outputs)}

    Engineer summary:
    #{engineer_summary}

    Execution output:
    #{execution_output}

    Respond exactly in this format:

    \\begin{STEP_OUTPUT}
    <STEP_OUTPUT>
    \\end{STEP_OUTPUT}
    """
  end

  @spec results_final_prompt(map(), [map()]) :: String.t()
  def results_final_prompt(context, step_outputs) do
    """
    [DENARIO_RESULTS_FINAL]
    Write the final results section in markdown using the completed experiment outputs.

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methodology:
    #{Map.get(context, :methodology, "")}

    Step outputs:
    #{render_step_outputs(step_outputs)}

    Respond exactly in this format:

    \\begin{RESULTS}
    <RESULTS>
    \\end{RESULTS}
    """
  end

  @spec literature_decision_prompt(
          map(),
          non_neg_integer(),
          pos_integer(),
          String.t(),
          String.t()
        ) ::
          String.t()
  def literature_decision_prompt(context, iteration, max_iterations, messages, papers_text) do
    """
    [DENARIO_LITERATURE_DECISION]
    Decide whether the idea appears novel, not novel, or whether another search query is needed.

    Round: #{iteration}/#{max_iterations}

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Previous literature reasoning:
    #{if messages == "", do: "none", else: messages}

    Papers found this round:
    #{if papers_text == "", do: "none", else: papers_text}

    When proposing a query, focus on the scientific problem, modality, domain, and evaluation setup.
    Avoid implementation-only terms such as Python, plotting, tutorials, or generic workflow language.

    The first round must always return decision=query.
    """
  end

  @spec literature_summary_prompt(map(), String.t(), String.t()) :: String.t()
  def literature_summary_prompt(context, decision, messages) do
    """
    [DENARIO_LITERATURE_SUMMARY]
    Summarize the literature check and explain why the idea is #{decision}.

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Literature search history:
    #{messages}

    Respond exactly in this format:

    \\begin{SUMMARY}
    <SUMMARY>
    \\end{SUMMARY}
    """
  end

  @spec literature_selection_prompt(map(), String.t(), String.t()) :: String.t()
  def literature_selection_prompt(context, query, candidates_text) do
    """
    [DENARIO_LITERATURE_SELECT]
    Select the papers that are genuinely relevant prior work for the proposed idea.

    Prefer papers that are close in:
    - task
    - data modality
    - domain
    - evaluation setup

    Avoid generic surveys or broad background papers unless they are directly relevant.
    Select at most 6 papers.
    If none are clearly relevant, return an empty list instead of weak matches.

    Data description:
    #{Map.get(context, :data_description, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Search query:
    #{query}

    Candidate papers:
    #{candidates_text}
    """
  end

  @spec paper_keywords_prompt(String.t(), map()) :: String.t()
  def paper_keywords_prompt(writer, context) do
    """
    [DENARIO_PAPER_KEYWORDS]
    You are a #{writer}. Generate five concise paper keywords.

    Idea:
    #{Map.get(context, :idea, "")}

    Methods:
    #{Map.get(context, :methodology, "")}

    Results:
    #{Map.get(context, :results, "")}

    Respond exactly in this format:

    \\begin{KEYWORDS}
    <KEYWORDS>
    \\end{KEYWORDS}
    """
  end

  @spec paper_abstract_prompt(String.t(), map(), String.t()) :: String.t()
  def paper_abstract_prompt(writer, context, citation_context) do
    """
    [DENARIO_PAPER_ABSTRACT]
    You are a #{writer}. Write a title and abstract for the paper.

    Idea:
    #{Map.get(context, :idea, "")}

    Methods:
    #{Map.get(context, :methodology, "")}

    Results:
    #{Map.get(context, :results, "")}

    Available citations:
    #{if citation_context == "", do: "none", else: citation_context}
    """
  end

  @spec paper_section_prompt(String.t(), String.t(), map(), String.t()) :: String.t()
  def paper_section_prompt(section, writer, context, citation_context) do
    """
    [DENARIO_PAPER_SECTION][#{section}]
    You are a #{writer}. Write the #{section} section of the paper in LaTeX.

    Paper title:
    #{Map.get(context, :title, "")}

    Paper abstract:
    #{Map.get(context, :abstract, "")}

    Idea:
    #{Map.get(context, :idea, "")}

    Methods:
    #{Map.get(context, :methodology, "")}

    Results:
    #{Map.get(context, :results, "")}

    Available citations:
    #{if citation_context == "", do: "none", else: citation_context}

    Only use \\cite{...} entries from the available citations above when relevant.
    Respond exactly in this format:

    \\begin{#{String.upcase(section)}}
    <#{String.upcase(section)}>
    \\end{#{String.upcase(section)}}
    """
  end

  @spec paper_figure_caption_prompt(String.t(), map(), String.t()) :: String.t()
  def paper_figure_caption_prompt(writer, context, plot_name) do
    """
    [DENARIO_PAPER_FIGURE_CAPTION]
    You are a #{writer}. Write one short LaTeX figure caption.

    Plot name:
    #{plot_name}

    Results:
    #{Map.get(context, :results, "")}

    Respond exactly in this format:

    \\begin{CAPTION}
    <CAPTION>
    \\end{CAPTION}
    """
  end

  @spec paper_refine_results_prompt(String.t(), map(), String.t()) :: String.t()
  def paper_refine_results_prompt(writer, context, figure_specs) do
    """
    [DENARIO_PAPER_REFINE_RESULTS]
    You are a #{writer}. Integrate the provided figure environments into the results section and reference them naturally.

    Current results section:
    #{Map.get(context, :paper_results, "")}

    Figure specifications:
    #{figure_specs}

    Respond exactly in this format:

    \\begin{RESULTS}
    <RESULTS>
    \\end{RESULTS}
    """
  end

  defp render_steps(steps) do
    steps
    |> Enum.map_join("\n", fn step ->
      "- #{Text.fetch(step, "id")}: agent=#{Text.fetch(step, "agent")} goal=#{Text.fetch(step, "goal")} deliverable=#{Text.fetch(step, "deliverable")} needs_code=#{Text.fetch(step, "needs_code")}"
    end)
  end

  defp render_step_outputs(step_outputs) do
    if step_outputs == [] do
      "none"
    else
      Enum.map_join(step_outputs, "\n\n", fn step_output ->
        """
        Step #{Map.get(step_output, :id, "")}
        Agent: #{Map.get(step_output, :agent, "")}
        Goal: #{Map.get(step_output, :goal, "")}
        Output:
        #{Map.get(step_output, :output, "")}
        """
      end)
    end
  end
end
