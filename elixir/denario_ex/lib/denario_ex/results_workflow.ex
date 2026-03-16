defmodule DenarioEx.ResultsWorkflow do
  @moduledoc false

  alias DenarioEx.{
    AI,
    CMBAgentLoop,
    LLM,
    PythonExecutor,
    ReqLLMClient,
    Text,
    WorkflowPrompts
  }

  @engineer_schema %{
    "type" => "object",
    "additionalProperties" => false,
    "properties" => %{
      "summary" => %{"type" => "string"},
      "notes" => %{"type" => "string"},
      "code" => %{"type" => "string"}
    },
    "required" => ["summary", "notes", "code"]
  }

  @spec run(DenarioEx.t(), keyword()) :: {:ok, map()} | {:error, term()}
  def run(session, opts \\ []) do
    client = Keyword.get(opts, :client, ReqLLMClient)
    executor = Keyword.get(opts, :executor, PythonExecutor)
    involved_agents = Keyword.get(opts, :involved_agents, ["engineer", "researcher"])
    max_n_steps = Keyword.get(opts, :max_n_steps, 6)
    max_n_attempts = Keyword.get(opts, :max_n_attempts, 10)
    restart_at_step = Keyword.get(opts, :restart_at_step, -1)
    hardware_constraints = Keyword.get(opts, :hardware_constraints, "")
    experiment_dir = Path.join(session.project_dir, "experiment")

    context = %{
      data_description: session.research.data_description,
      idea: session.research.idea,
      methodology: session.research.methodology,
      experiment_dir: experiment_dir
    }

    with {:ok, planner_llm} <- LLM.parse(Keyword.get(opts, :planner_model, "gpt-4o")),
         {:ok, reviewer_llm} <- LLM.parse(Keyword.get(opts, :plan_reviewer_model, "o3-mini")),
         {:ok, engineer_llm} <- LLM.parse(Keyword.get(opts, :engineer_model, "gpt-4.1")),
         {:ok, researcher_llm} <- LLM.parse(Keyword.get(opts, :researcher_model, "o3-mini")),
         {:ok, formatter_llm} <- LLM.parse(Keyword.get(opts, :formatter_model, "o3-mini")),
         {:ok, plan} <-
           CMBAgentLoop.plan_and_review("results", context,
             client: client,
             keys: session.keys,
             planner_model: planner_llm,
             plan_reviewer_model: reviewer_llm,
             allowed_agents: involved_agents,
             max_steps: max_n_steps
           ),
         {:ok, step_outputs} <-
           run_steps(
             plan.steps,
             context,
             client,
             executor,
             session.keys,
             engineer_llm,
             researcher_llm,
             max_n_attempts,
             restart_at_step,
             hardware_constraints,
             experiment_dir
           ),
         final_prompt <- WorkflowPrompts.results_final_prompt(context, step_outputs),
         {:ok, final_text} <- AI.complete(client, final_prompt, formatter_llm, session.keys),
         {:ok, results_block} <- Text.extract_block(final_text, "RESULTS") do
      log_path = Path.join(experiment_dir, "step_logs.md")
      File.mkdir_p!(experiment_dir)
      File.write!(log_path, render_step_log(plan.steps, step_outputs))

      {:ok,
       %{
         results: Text.clean_section(results_block, "RESULTS"),
         plot_paths: collect_plot_paths(experiment_dir),
         plan: plan,
         step_outputs: step_outputs,
         log_path: log_path
       }}
    end
  end

  defp run_steps(
         steps,
         context,
         client,
         executor,
         keys,
         engineer_llm,
         researcher_llm,
         max_n_attempts,
         restart_at_step,
         hardware_constraints,
         experiment_dir
       ) do
    start_index = if restart_at_step < 0, do: 0, else: restart_at_step

    steps
    |> Enum.with_index()
    |> Enum.reduce_while({:ok, []}, fn {step, index}, {:ok, outputs} ->
      if index < start_index do
        {:cont, {:ok, outputs}}
      else
        case run_single_step(
               step,
               context,
               outputs,
               client,
               executor,
               keys,
               engineer_llm,
               researcher_llm,
               max_n_attempts,
               hardware_constraints,
               experiment_dir
             ) do
          {:ok, step_output} ->
            {:cont, {:ok, outputs ++ [step_output]}}

          {:error, reason} ->
            {:halt, {:error, reason}}
        end
      end
    end)
  end

  defp run_single_step(
         step,
         context,
         outputs,
         client,
         executor,
         keys,
         engineer_llm,
         researcher_llm,
         max_n_attempts,
         hardware_constraints,
         experiment_dir
       ) do
    needs_code = truthy?(Text.fetch(step, "needs_code"))
    agent = Text.fetch(step, "agent")

    cond do
      needs_code or agent == "engineer" ->
        run_engineer_step(
          step,
          context,
          outputs,
          client,
          executor,
          keys,
          engineer_llm,
          researcher_llm,
          max_n_attempts,
          hardware_constraints,
          experiment_dir,
          ""
        )

      true ->
        prompt = WorkflowPrompts.results_step_summary_prompt(step, context, outputs, "", "")

        with {:ok, response} <- AI.complete(client, prompt, researcher_llm, keys),
             {:ok, block} <- Text.extract_block(response, "STEP_OUTPUT") do
          {:ok,
           %{
             id: Text.fetch(step, "id"),
             agent: agent,
             goal: Text.fetch(step, "goal"),
             output: Text.clean_section(block, "STEP_OUTPUT"),
             execution_output: ""
           }}
        end
    end
  end

  defp run_engineer_step(
         step,
         context,
         outputs,
         client,
         executor,
         keys,
         engineer_llm,
         researcher_llm,
         max_n_attempts,
         hardware_constraints,
         experiment_dir,
         previous_error,
         attempt \\ 1
       ) do
    prompt =
      WorkflowPrompts.results_engineer_prompt(
        step,
        context,
        outputs,
        previous_error,
        hardware_constraints
      )

    with {:ok, object} <-
           AI.generate_object(client, prompt, @engineer_schema, engineer_llm, keys),
         code when is_binary(code) and code != "" <- Text.fetch(object, "code") do
      case executor.execute(code,
             work_dir: experiment_dir,
             step_id: Text.fetch(step, "id"),
             attempt: attempt
           ) do
        {:ok, execution} ->
          execution_output = Text.fetch(execution, "output") || ""
          engineer_summary = Text.fetch(object, "summary") || ""

          summary_prompt =
            WorkflowPrompts.results_step_summary_prompt(
              step,
              context,
              outputs,
              engineer_summary,
              execution_output
            )

          with {:ok, response} <- AI.complete(client, summary_prompt, researcher_llm, keys),
               {:ok, block} <- Text.extract_block(response, "STEP_OUTPUT") do
            {:ok,
             %{
               id: Text.fetch(step, "id"),
               agent: Text.fetch(step, "agent"),
               goal: Text.fetch(step, "goal"),
               output: Text.clean_section(block, "STEP_OUTPUT"),
               execution_output: execution_output
             }}
          end

        {:error, execution} when attempt < max_n_attempts ->
          run_engineer_step(
            step,
            context,
            outputs,
            client,
            executor,
            keys,
            engineer_llm,
            researcher_llm,
            max_n_attempts,
            hardware_constraints,
            experiment_dir,
            Text.fetch(execution, "output") || inspect(execution),
            attempt + 1
          )

        {:error, execution} ->
          {:error, {:results_step_failed, Text.fetch(step, "id"), execution}}
      end
    else
      {:error, reason} ->
        {:error, reason}

      _ ->
        {:error, {:invalid_engineer_response, step}}
    end
  end

  defp collect_plot_paths(experiment_dir) do
    ["png", "jpg", "jpeg", "pdf", "svg"]
    |> Enum.flat_map(fn ext -> Path.wildcard(Path.join(experiment_dir, "**/*.#{ext}")) end)
    |> Enum.uniq()
  end

  defp render_step_log(steps, outputs) do
    """
    # Results Workflow

    ## Planned Steps
    #{Enum.map_join(steps, "\n", fn step -> "- #{Text.fetch(step, "id")}: #{Text.fetch(step, "goal")}" end)}

    ## Step Outputs
    #{Enum.map_join(outputs, "\n\n", fn output -> """
      ### #{output.id}
      Agent: #{output.agent}
      Goal: #{output.goal}

      #{output.output}

      Execution output:
      ```
      #{output.execution_output}
      ```
      """ end)}
    """
  end

  defp truthy?(value) when value in [true, "true", "TRUE", 1], do: true
  defp truthy?(_value), do: false
end
