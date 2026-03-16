defmodule DenarioEx.CMBAgentLoop do
  @moduledoc """
  Elixir-native replacement for the planning/control pattern used by the Python cmbagent flows.
  """

  alias DenarioEx.{AI, LLM, Text, WorkflowPrompts}

  @review_schema %{
    "type" => "object",
    "additionalProperties" => false,
    "properties" => %{
      "approved" => %{"type" => "boolean"},
      "feedback" => %{"type" => "string"}
    },
    "required" => ["approved", "feedback"]
  }

  @spec plan_and_review(String.t(), map(), keyword()) ::
          {:ok, %{summary: String.t(), steps: [map()], feedback: String.t()}} | {:error, term()}
  def plan_and_review(task, context, opts) do
    client = Keyword.fetch!(opts, :client)
    keys = Keyword.fetch!(opts, :keys)
    allowed_agents = Keyword.fetch!(opts, :allowed_agents)
    max_steps = Keyword.get(opts, :max_steps, 6)
    max_reviews = Keyword.get(opts, :max_reviews, 1)

    with {:ok, planner_llm} <- LLM.parse(Keyword.fetch!(opts, :planner_model)),
         {:ok, reviewer_llm} <- LLM.parse(Keyword.fetch!(opts, :plan_reviewer_model)) do
      do_plan_and_review(
        task,
        context,
        client,
        keys,
        planner_llm,
        reviewer_llm,
        allowed_agents,
        max_steps,
        max_reviews,
        nil
      )
    end
  end

  @spec run_text_task(String.t(), map(), keyword()) ::
          {:ok, %{output: String.t(), plan: map(), step_outputs: [map()]}} | {:error, term()}
  def run_text_task(task, context, opts) do
    client = Keyword.fetch!(opts, :client)
    keys = Keyword.fetch!(opts, :keys)
    agent_models = Keyword.fetch!(opts, :agent_models)
    final_model = Keyword.fetch!(opts, :final_model)

    with {:ok, plan} <- plan_and_review(task, context, opts),
         {:ok, step_outputs} <-
           run_text_steps(task, context, plan.steps, client, keys, agent_models),
         final_prompt <- WorkflowPrompts.cmbagent_final_prompt(task, context, step_outputs),
         {:ok, final_text} <- AI.complete(client, final_prompt, final_model, keys),
         {:ok, output} <- extract_final_output(task, final_text) do
      {:ok, %{output: output, plan: plan, step_outputs: step_outputs}}
    end
  end

  defp do_plan_and_review(
         task,
         context,
         client,
         keys,
         planner_llm,
         reviewer_llm,
         allowed_agents,
         max_steps,
         remaining_reviews,
         feedback
       ) do
    plan_prompt =
      WorkflowPrompts.cmbagent_plan_prompt(task, context, allowed_agents, max_steps, feedback)

    with {:ok, plan_object} <-
           AI.generate_object(client, plan_prompt, plan_schema(allowed_agents), planner_llm, keys),
         {:ok, plan} <- normalize_plan(plan_object, allowed_agents, max_steps),
         review_prompt <- WorkflowPrompts.cmbagent_plan_review_prompt(task, context, plan),
         {:ok, review_object} <-
           AI.generate_object(client, review_prompt, @review_schema, reviewer_llm, keys) do
      if approved?(review_object) or remaining_reviews <= 0 do
        {:ok,
         %{summary: plan.summary, steps: plan.steps, feedback: review_feedback(review_object)}}
      else
        do_plan_and_review(
          task,
          context,
          client,
          keys,
          planner_llm,
          reviewer_llm,
          allowed_agents,
          max_steps,
          remaining_reviews - 1,
          review_feedback(review_object)
        )
      end
    end
  end

  defp run_text_steps(task, context, steps, client, keys, agent_models) do
    Enum.reduce_while(steps, {:ok, []}, fn step, {:ok, outputs} ->
      agent = Text.fetch(step, "agent")

      with {:ok, llm} <- fetch_agent_model(agent_models, agent),
           prompt <- WorkflowPrompts.cmbagent_step_prompt(task, agent, step, context, outputs),
           {:ok, step_text} <- AI.complete(client, prompt, llm, keys),
           {:ok, output} <- Text.extract_block(step_text, "STEP_OUTPUT") do
        step_output = %{
          id: Text.fetch(step, "id"),
          agent: agent,
          goal: Text.fetch(step, "goal"),
          output: Text.clean_section(output, "STEP_OUTPUT")
        }

        {:cont, {:ok, outputs ++ [step_output]}}
      else
        {:error, reason} -> {:halt, {:error, reason}}
      end
    end)
  end

  defp extract_final_output("idea", text) do
    with {:ok, block} <- Text.extract_block(text, "IDEA") do
      {:ok, Text.clean_section(block, "IDEA")}
    end
  end

  defp extract_final_output("method", text) do
    with {:ok, block} <- Text.extract_block(text, "METHODS") do
      {:ok, Text.clean_section(block, "METHODS")}
    end
  end

  defp fetch_agent_model(agent_models, agent) do
    case Map.fetch(agent_models, agent) do
      {:ok, %LLM{} = llm} -> {:ok, llm}
      :error -> {:error, {:missing_agent_model, agent}}
    end
  end

  defp plan_schema(allowed_agents) do
    %{
      "type" => "object",
      "additionalProperties" => false,
      "properties" => %{
        "summary" => %{"type" => "string"},
        "steps" => %{
          "type" => "array",
          "items" => %{
            "type" => "object",
            "additionalProperties" => false,
            "properties" => %{
              "id" => %{"type" => "string"},
              "agent" => %{"type" => "string", "enum" => allowed_agents},
              "goal" => %{"type" => "string"},
              "deliverable" => %{"type" => "string"},
              "needs_code" => %{"type" => "boolean"}
            },
            "required" => ["id", "agent", "goal", "deliverable", "needs_code"]
          }
        }
      },
      "required" => ["summary", "steps"]
    }
  end

  defp normalize_plan(plan_object, allowed_agents, max_steps) do
    steps =
      plan_object
      |> Text.fetch("steps")
      |> List.wrap()
      |> Enum.take(max_steps)
      |> Enum.map(fn step ->
        %{
          "id" => Text.fetch(step, "id"),
          "agent" => Text.fetch(step, "agent"),
          "goal" => Text.fetch(step, "goal"),
          "deliverable" => Text.fetch(step, "deliverable"),
          "needs_code" => truthy?(Text.fetch(step, "needs_code"))
        }
      end)

    valid? =
      steps != [] and
        Enum.all?(steps, fn step ->
          step["id"] not in [nil, ""] and step["goal"] not in [nil, ""] and
            step["deliverable"] not in [nil, ""] and step["agent"] in allowed_agents
        end)

    if valid? do
      {:ok, %{summary: Text.fetch(plan_object, "summary") || "", steps: steps}}
    else
      {:error, {:invalid_plan, plan_object}}
    end
  end

  defp approved?(review_object), do: truthy?(Text.fetch(review_object, "approved"))
  defp review_feedback(review_object), do: Text.fetch(review_object, "feedback") || ""

  defp truthy?(value) when value in [true, "true", "TRUE", 1], do: true
  defp truthy?(_value), do: false
end
