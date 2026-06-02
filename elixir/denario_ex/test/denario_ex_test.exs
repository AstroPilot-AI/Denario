defmodule DenarioExTest do
  use ExUnit.Case, async: true

  alias DenarioEx

  defmodule FakeClient do
    @behaviour DenarioEx.LLMClient

    @impl true
    def complete([%{role: "user", content: prompt}], opts) do
      send(self(), {:llm_call, prompt, opts[:model]})

      cond do
        String.contains?(prompt, "Current idea:") ->
          {:ok, "\\begin{CRITIC}Make the idea more concrete and measurable.\\end{CRITIC}"}

        String.contains?(prompt, "Iteration 1") ->
          {:ok,
           "\\begin{IDEA}A concrete sensor robustness study with measurable outcomes.\\end{IDEA}"}

        String.contains?(prompt, "Iteration 0") ->
          {:ok, "\\begin{IDEA}A broad sensor-analysis idea.\\end{IDEA}"}

        String.contains?(prompt, "\\begin{METHODS}") ->
          {:ok,
           "\\begin{METHODS}1. Load the dataset.\\n2. Compare the proposed signals.\\end{METHODS}"}

        true ->
          {:error, {:unexpected_prompt, prompt}}
      end
    end

    @impl true
    def generate_object(_messages, _schema, _opts) do
      {:error, :not_used_in_this_test}
    end
  end

  setup do
    project_dir = Path.join(System.tmp_dir!(), "denario_ex_#{System.unique_integer([:positive])}")
    on_exit(fn -> File.rm_rf(project_dir) end)
    {:ok, project_dir: project_dir}
  end

  test "new/1 creates the expected project directories and persists markdown fields", %{
    project_dir: project_dir
  } do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert File.dir?(Path.join(project_dir, "input_files"))
    assert File.dir?(Path.join(project_dir, "input_files/plots"))

    assert {:ok, denario} = DenarioEx.set_data_description(denario, "Research description")
    assert {:ok, denario} = DenarioEx.set_idea(denario, "Research idea")
    assert {:ok, denario} = DenarioEx.set_method(denario, "Research method")
    assert {:ok, _denario} = DenarioEx.set_results(denario, "Research results")

    assert File.read!(Path.join(project_dir, "input_files/data_description.md")) ==
             "Research description"

    assert File.read!(Path.join(project_dir, "input_files/idea.md")) == "Research idea"
    assert File.read!(Path.join(project_dir, "input_files/methods.md")) == "Research method"
    assert File.read!(Path.join(project_dir, "input_files/results.md")) == "Research results"

    assert {:ok, reloaded} = DenarioEx.new(project_dir: project_dir)
    assert reloaded.research.data_description == "Research description"
    assert reloaded.research.idea == "Research idea"
    assert reloaded.research.methodology == "Research method"
    assert reloaded.research.results == "Research results"
  end

  test "fast workflows generate idea and methods through a pluggable client", %{
    project_dir: project_dir
  } do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(
               denario,
               "Analyze a small hypothetical lab sensor dataset and propose one paper idea."
             )

    assert {:ok, denario} =
             DenarioEx.get_idea_fast(
               denario,
               client: FakeClient,
               llm: "gpt-4.1-mini",
               iterations: 2
             )

    assert denario.research.idea == "A concrete sensor robustness study with measurable outcomes."
    assert File.read!(Path.join(project_dir, "input_files/idea.md")) == denario.research.idea

    assert_received {:llm_call, prompt, "openai:gpt-4.1-mini"}
    assert String.contains?(prompt, "groundbreaking idea")

    assert {:ok, denario} =
             DenarioEx.get_method_fast(
               denario,
               client: FakeClient,
               llm: "gpt-4.1-mini"
             )

    assert String.contains?(denario.research.methodology, "Load the dataset")

    assert File.read!(Path.join(project_dir, "input_files/methods.md")) ==
             denario.research.methodology
  end
end
