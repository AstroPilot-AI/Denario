defmodule DenarioExWorkflowsTest do
  use ExUnit.Case, async: true

  alias DenarioEx

  defmodule FakeClient do
    @behaviour DenarioEx.LLMClient

    @impl true
    def complete([%{role: "user", content: prompt}], opts) do
      send(self(), {:llm_text, prompt, opts[:model]})

      cond do
        String.contains?(prompt, "[DENARIO_CMB_STEP][idea_maker]") and
            String.contains?(prompt, "Select the strongest idea") ->
          {:ok,
           "\\begin{STEP_OUTPUT}Adaptive urban microclimate anomaly detection using dense low-cost sensor arrays and interpretable time-series models.\\end{STEP_OUTPUT}"}

        String.contains?(prompt, "[DENARIO_CMB_STEP][idea_hater]") ->
          {:ok,
           "\\begin{STEP_OUTPUT}Focus the scope on one measurable anomaly-detection task and make the dataset assumptions explicit.\\end{STEP_OUTPUT}"}

        String.contains?(prompt, "[DENARIO_CMB_STEP][idea_maker]") ->
          {:ok,
           "\\begin{STEP_OUTPUT}Generate several candidate ideas around urban microclimate anomaly detection and pick the one with the clearest measurable outcome.\\end{STEP_OUTPUT}"}

        String.contains?(prompt, "[DENARIO_CMB_FINAL][idea]") ->
          {:ok,
           "\\begin{IDEA}Adaptive urban microclimate anomaly detection using dense low-cost sensor arrays and interpretable time-series models.\\end{IDEA}"}

        String.contains?(prompt, "[DENARIO_CMB_STEP][researcher]") and
            String.contains?(prompt, "[TASK][method]") ->
          {:ok,
           "\\begin{STEP_OUTPUT}Define preprocessing, temporal validation splits, anomaly scoring, ablations, and calibration checks for the selected microclimate dataset.\\end{STEP_OUTPUT}"}

        String.contains?(prompt, "[DENARIO_CMB_FINAL][method]") ->
          {:ok,
           "\\begin{METHODS}1. Clean and align the sensor streams.\\n2. Build temporal train-validation-test splits.\\n3. Train an interpretable anomaly detector and compare against baselines.\\n4. Report quantitative metrics and calibration diagnostics.\\end{METHODS}"}

        String.contains?(prompt, "[DENARIO_RESULTS_STEP_SUMMARY]") ->
          {:ok,
           "\\begin{STEP_OUTPUT}The engineer produced reproducible summary statistics and saved a plot for the anomaly-score distribution.\\end{STEP_OUTPUT}"}

        String.contains?(prompt, "[DENARIO_RESULTS_FINAL]") ->
          {:ok,
           "\\begin{RESULTS}The anomaly detector achieved stable performance across temporal splits and produced a clear anomaly-score distribution plot. Quantitatively, the run shows strong separation between nominal and anomalous regimes, supporting the project idea.\\end{RESULTS}"}

        String.contains?(prompt, "[DENARIO_LITERATURE_SUMMARY]") ->
          {:ok,
           "\\begin{SUMMARY}The searched papers overlap with environmental anomaly monitoring broadly, but none combines dense low-cost urban microclimate sensing with the specific interpretable anomaly-detection framing proposed here. The idea can be considered novel relative to the retrieved work.\\end{SUMMARY}"}

        String.contains?(prompt, "[DENARIO_PAPER_KEYWORDS]") ->
          {:ok,
           "\\begin{KEYWORDS}anomaly detection, urban climate, sensor networks, interpretable models, time-series analysis\\end{KEYWORDS}"}

        String.contains?(prompt, "[DENARIO_PAPER_SECTION][Introduction]") ->
          {:ok,
           "\\begin{INTRODUCTION}Urban microclimate monitoring remains difficult because low-cost sensors drift, dense deployments produce noisy streams, and anomalies are rare. This paper frames the problem as interpretable anomaly detection over temporally aligned sensor networks and motivates why stable detection matters for urban operations.\\end{INTRODUCTION}"}

        String.contains?(prompt, "[DENARIO_PAPER_SECTION][Methods]") ->
          {:ok,
           "\\begin{METHODS}We align, clean, and calibrate the sensor streams before training an interpretable anomaly detector over temporally blocked splits. We compare against simple baselines and evaluate discrimination and calibration metrics.\\end{METHODS}"}

        String.contains?(prompt, "[DENARIO_PAPER_SECTION][Results]") ->
          {:ok,
           "\\begin{RESULTS}The proposed detector provides consistent separation between nominal and anomalous conditions and remains stable across blocked temporal evaluation. The resulting distribution plot highlights the operating region used for interpretation.\\end{RESULTS}"}

        String.contains?(prompt, "[DENARIO_PAPER_SECTION][Conclusions]") ->
          {:ok,
           "\\begin{CONCLUSIONS}Interpretable anomaly detection over dense urban microclimate sensor streams is feasible with careful temporal evaluation and calibration-aware reporting. The generated workflow supports reproducible environmental monitoring studies.\\end{CONCLUSIONS}"}

        String.contains?(prompt, "[DENARIO_PAPER_FIGURE_CAPTION]") ->
          {:ok,
           "\\begin{CAPTION}Distribution of anomaly scores across the evaluation split, highlighting separation between nominal and anomalous conditions.\\end{CAPTION}"}

        String.contains?(prompt, "[DENARIO_PAPER_REFINE_RESULTS]") ->
          {:ok,
           "\\begin{RESULTS}The proposed detector provides consistent separation between nominal and anomalous conditions and remains stable across blocked temporal evaluation. Figure \\ref{fig:anomaly_scores} visualizes the anomaly-score distribution used in the interpretation.\\begin{figure}[t]\\centering\\includegraphics[width=0.48\\textwidth]{anomaly_scores.png}\\caption{Distribution of anomaly scores across the evaluation split, highlighting separation between nominal and anomalous conditions.}\\label{fig:anomaly_scores}\\end{figure}\\end{RESULTS}"}

        true ->
          {:error, {:unexpected_prompt, prompt}}
      end
    end

    @impl true
    def generate_object([%{role: "user", content: prompt}], _schema, opts) do
      send(self(), {:llm_object, prompt, opts[:model]})

      cond do
        String.contains?(prompt, "[DENARIO_PLAN][idea]") ->
          {:ok,
           %{
             "summary" => "Develop, critique, and finalize one research idea.",
             "steps" => [
               %{
                 "id" => "idea_1",
                 "agent" => "idea_maker",
                 "goal" => "Draft candidate ideas",
                 "deliverable" => "Candidate idea set",
                 "needs_code" => false
               },
               %{
                 "id" => "idea_2",
                 "agent" => "idea_hater",
                 "goal" => "Critique the candidate idea",
                 "deliverable" => "Actionable criticism",
                 "needs_code" => false
               },
               %{
                 "id" => "idea_3",
                 "agent" => "idea_maker",
                 "goal" => "Select the strongest idea",
                 "deliverable" => "Final idea draft",
                 "needs_code" => false
               }
             ]
           }}

        String.contains?(prompt, "[DENARIO_PLAN][method]") ->
          {:ok,
           %{
             "summary" => "Turn the idea into an executable methodology.",
             "steps" => [
               %{
                 "id" => "method_1",
                 "agent" => "researcher",
                 "goal" => "Design the methodology",
                 "deliverable" => "Detailed methodological draft",
                 "needs_code" => false
               }
             ]
           }}

        String.contains?(prompt, "[DENARIO_PLAN][results]") ->
          {:ok,
           %{
             "summary" => "Run one engineering step and then synthesize the findings.",
             "steps" => [
               %{
                 "id" => "results_1",
                 "agent" => "engineer",
                 "goal" => "Run the core analysis and generate a diagnostic plot",
                 "deliverable" => "Reproducible code, console output, and one plot",
                 "needs_code" => true
               },
               %{
                 "id" => "results_2",
                 "agent" => "researcher",
                 "goal" => "Summarize the quantitative findings",
                 "deliverable" => "Narrative summary of the evidence",
                 "needs_code" => false
               }
             ]
           }}

        String.contains?(prompt, "[DENARIO_PLAN_REVIEW]") ->
          {:ok, %{"approved" => true, "feedback" => "The plan is focused and feasible."}}

        String.contains?(prompt, "[DENARIO_RESULTS_ENGINEER]") and
            String.contains?(prompt, "Previous execution error: none") ->
          {:ok,
           %{
             "summary" => "Generate a first analysis script.",
             "notes" => "First attempt.",
             "code" => "# FAIL_ONCE\nprint('first attempt')\n"
           }}

        String.contains?(prompt, "[DENARIO_RESULTS_ENGINEER]") ->
          {:ok,
           %{
             "summary" => "Generate the corrected analysis script.",
             "notes" => "Second attempt with plotting.",
             "code" => "# SUCCESS\nprint('mean_score=0.91')\n"
           }}

        String.contains?(prompt, "[DENARIO_LITERATURE_DECISION]") and
            String.contains?(prompt, "Round: 0") ->
          {:ok,
           %{
             "reason" =>
               "The first round should broaden into a focused literature search before making a novelty claim.",
             "decision" => "query",
             "query" => "urban microclimate anomaly detection low-cost sensor network"
           }}

        String.contains?(prompt, "[DENARIO_LITERATURE_DECISION]") ->
          {:ok,
           %{
             "reason" =>
               "The retrieved papers discuss environmental anomaly monitoring and urban sensing, but none matches the exact interpretable anomaly-detection framing or evaluation setup proposed here.",
             "decision" => "novel",
             "query" => ""
           }}

        String.contains?(prompt, "[DENARIO_LITERATURE_SELECT]") and
            String.contains?(prompt, "Paper ID: openalex-123") ->
          {:ok,
           %{
             "selected_paper_ids" => ["openalex-123"],
             "rationale" => "This is the closest prior work in task and domain."
           }}

        String.contains?(prompt, "[DENARIO_LITERATURE_SELECT]") ->
          {:ok,
           %{
             "selected_paper_ids" => ["paper-123"],
             "rationale" => "This paper is the closest prior work to the proposed idea."
           }}

        String.contains?(prompt, "[DENARIO_PAPER_ABSTRACT]") ->
          {:ok,
           %{
             "title" => "Interpretable Anomaly Detection for Urban Microclimate Sensor Networks",
             "abstract" =>
               "We study interpretable anomaly detection over dense urban microclimate sensor networks. Using temporally blocked evaluation and calibration-aware reporting, we show that the proposed workflow separates anomalous from nominal conditions while remaining operationally interpretable."
           }}

        true ->
          {:error, {:unexpected_object_prompt, prompt}}
      end
    end
  end

  defmodule FakeExecutor do
    @behaviour DenarioEx.CodeExecutor

    @impl true
    def execute(code, opts) do
      step_id = Keyword.fetch!(opts, :step_id)
      work_dir = Keyword.fetch!(opts, :work_dir)
      File.mkdir_p!(work_dir)

      failure_key = {:executor_failed_once, step_id}

      cond do
        String.contains?(code, "FAIL_ONCE") and Process.get(failure_key) != true ->
          Process.put(failure_key, true)

          {:error,
           %{
             "status" => 1,
             "output" => "Traceback: simulated failure"
           }}

        true ->
          plot_path = Path.join(work_dir, "anomaly_scores.png")
          File.write!(plot_path, "fake png bytes")

          {:ok,
           %{
             "status" => 0,
             "output" => "mean_score=0.91\nsaved_plot=anomaly_scores.png",
             "generated_files" => [plot_path]
           }}
      end
    end
  end

  defmodule FakeSemanticScholarClient do
    @behaviour DenarioEx.SemanticScholarClient

    @impl true
    def search(query, _keys, _opts) do
      send(self(), {:semantic_scholar_query, query})

      {:ok,
       %{
         "total" => 1,
         "data" => [
           %{
             "paperId" => "paper-123",
             "title" => "Urban sensing for anomaly monitoring",
             "year" => 2024,
             "citationCount" => 37,
             "abstract" =>
               "A broad study of anomaly monitoring in urban environmental sensor systems.",
             "url" => "https://example.com/paper-123",
             "authors" => [%{"name" => "A. Researcher"}, %{"name" => "B. Scientist"}],
             "externalIds" => %{"ArXiv" => "2401.12345"},
             "openAccessPdf" => %{"url" => "https://example.com/paper-123.pdf"}
           }
         ]
       }}
    end
  end

  defmodule RateLimitedSemanticScholarClient do
    @behaviour DenarioEx.SemanticScholarClient

    @impl true
    def search(query, _keys, _opts) do
      send(self(), {:semantic_scholar_query, query})
      {:error, {:semantic_scholar_http_error, 429, %{"message" => "Too Many Requests"}}}
    end
  end

  defmodule FakeOpenAlexClient do
    @behaviour DenarioEx.SemanticScholarClient

    @impl true
    def search(query, _keys, _opts) do
      send(self(), {:openalex_query, query})

      {:ok,
       %{
         "total" => 1,
         "data" => [
           %{
             "paperId" => "openalex-123",
             "title" => "OpenAlex urban sensing anomaly paper",
             "year" => 2024,
             "citationCount" => 18,
             "relevanceScore" => 12.4,
             "abstract" =>
               "A public-index paper about anomaly monitoring in urban environmental sensing.",
             "url" => "https://openalex.org/W123",
             "authors" => [%{"name" => "C. Author"}],
             "externalIds" => %{"DOI" => "https://doi.org/10.1234/example"},
             "openAccessPdf" => %{"url" => "https://example.com/openalex-123.pdf"}
           }
         ]
       }}
    end
  end

  setup do
    project_dir =
      Path.join(System.tmp_dir!(), "denario_ex_workflows_#{System.unique_integer([:positive])}")

    on_exit(fn -> File.rm_rf(project_dir) end)
    {:ok, project_dir: project_dir}
  end

  test "cmbagent loop ports idea and method generation", %{project_dir: project_dir} do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(
               denario,
               "Analyze dense low-cost urban microclimate sensor data and build one concise research direction."
             )

    assert {:ok, denario} =
             DenarioEx.get_idea_cmbagent(
               denario,
               client: FakeClient,
               planner_model: "openai:gpt-4.1-mini",
               plan_reviewer_model: "openai:gpt-4.1-mini",
               idea_maker_model: "openai:gpt-4.1-mini",
               idea_hater_model: "openai:gpt-4.1-mini"
             )

    assert String.contains?(denario.research.idea, "urban microclimate anomaly detection")
    assert File.read!(Path.join(project_dir, "input_files/idea.md")) == denario.research.idea

    assert {:ok, denario} =
             DenarioEx.get_method_cmbagent(
               denario,
               client: FakeClient,
               planner_model: "openai:gpt-4.1-mini",
               plan_reviewer_model: "openai:gpt-4.1-mini",
               method_generator_model: "openai:gpt-4.1-mini"
             )

    assert String.contains?(denario.research.methodology, "temporal train-validation-test splits")

    assert File.read!(Path.join(project_dir, "input_files/methods.md")) ==
             denario.research.methodology
  end

  test "get_results runs the planning loop, retries code execution, and persists plots", %{
    project_dir: project_dir
  } do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(denario, "Small synthetic sensor dataset.")

    assert {:ok, denario} = DenarioEx.set_idea(denario, "Detect anomalies in sensor readings.")

    assert {:ok, denario} =
             DenarioEx.set_method(
               denario,
               "Train an interpretable anomaly detector and produce one diagnostic figure."
             )

    assert {:ok, denario} =
             DenarioEx.get_results(
               denario,
               client: FakeClient,
               executor: FakeExecutor,
               planner_model: "openai:gpt-4.1-mini",
               plan_reviewer_model: "openai:gpt-4.1-mini",
               engineer_model: "openai:gpt-4.1-mini",
               researcher_model: "openai:gpt-4.1-mini",
               formatter_model: "openai:gpt-4.1-mini",
               max_n_attempts: 2
             )

    assert String.contains?(denario.research.results, "stable performance")

    assert File.read!(Path.join(project_dir, "input_files/results.md")) ==
             denario.research.results

    assert Enum.any?(denario.research.plot_paths, &String.ends_with?(&1, "anomaly_scores.png"))
    assert File.exists?(Path.join(project_dir, "input_files/plots/anomaly_scores.png"))
  end

  test "literature checking queries semantic scholar and writes literature.md", %{
    project_dir: project_dir
  } do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(denario, "Urban sensor anomaly project.")

    assert {:ok, denario} =
             DenarioEx.set_idea(
               denario,
               "Interpretable anomaly detection for urban microclimate sensor networks."
             )

    assert {:ok, denario} =
             DenarioEx.check_idea(
               denario,
               client: FakeClient,
               semantic_scholar_client: FakeSemanticScholarClient,
               llm: "openai:gpt-4.1-mini",
               max_iterations: 3
             )

    assert String.contains?(denario.research.literature, "can be considered novel")

    assert File.read!(Path.join(project_dir, "input_files/literature.md")) ==
             denario.research.literature

    assert length(denario.research.literature_sources) == 1
    assert hd(denario.research.literature_sources)["paperId"] == "paper-123"

    assert_received {:semantic_scholar_query,
                     "urban microclimate anomaly detection low-cost sensor network"}
  end

  test "literature checking falls back to OpenAlex when Semantic Scholar is rate-limited", %{
    project_dir: project_dir
  } do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(denario, "Urban sensor anomaly project.")

    assert {:ok, denario} =
             DenarioEx.set_idea(
               denario,
               "Interpretable anomaly detection for urban microclimate sensor networks."
             )

    assert {:ok, denario} =
             DenarioEx.check_idea(
               denario,
               client: FakeClient,
               semantic_scholar_client: RateLimitedSemanticScholarClient,
               fallback_literature_client: FakeOpenAlexClient,
               llm: "openai:gpt-4.1-mini",
               max_iterations: 3
             )

    assert String.contains?(denario.research.literature, "can be considered novel")
    assert length(denario.research.literature_sources) == 1

    assert_received {:semantic_scholar_query,
                     "urban microclimate anomaly detection low-cost sensor network"}

    assert_received {:openalex_query,
                     "urban microclimate anomaly detection low-cost sensor network"}
  end

  test "paper generation writes a journal-aware LaTeX draft from project artifacts", %{
    project_dir: project_dir
  } do
    plots_dir = Path.join(project_dir, "input_files/plots")

    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(denario, "Urban sensor anomaly project.")

    assert {:ok, denario} =
             DenarioEx.set_idea(
               denario,
               "Interpretable anomaly detection for urban microclimate sensor networks."
             )

    assert {:ok, denario} =
             DenarioEx.set_method(
               denario,
               "Align the sensor streams, train the anomaly detector, and evaluate on blocked temporal splits."
             )

    assert {:ok, denario} =
             DenarioEx.set_results(
               denario,
               "The detector separates anomalous from nominal periods and yields a diagnostic score distribution."
             )

    File.mkdir_p!(plots_dir)
    File.write!(Path.join(plots_dir, "anomaly_scores.png"), "fake png bytes")

    assert {:ok, denario} =
             DenarioEx.check_idea(
               denario,
               client: FakeClient,
               semantic_scholar_client: FakeSemanticScholarClient,
               llm: "openai:gpt-4.1-mini",
               max_iterations: 3
             )

    assert {:ok, denario} =
             DenarioEx.get_paper(
               denario,
               client: FakeClient,
               llm: "openai:gpt-4.1-mini",
               writer: "climate scientist",
               journal: :neurips,
               add_citations: true,
               compile: false
             )

    assert denario.research.paper_tex_path
    assert File.exists?(denario.research.paper_tex_path)

    tex = File.read!(denario.research.paper_tex_path)

    assert String.contains?(
             tex,
             "\\title{Interpretable Anomaly Detection for Urban Microclimate Sensor Networks}"
           )

    assert String.contains?(tex, "\\section{Introduction}")
    assert String.contains?(tex, "\\label{fig:anomaly_scores}")
    assert String.contains?(tex, "../input_files/plots/anomaly_scores.png")
    assert File.exists?(Path.join(project_dir, "paper/neurips_2025.sty"))
    assert File.exists?(Path.join(project_dir, "paper/bibliography.bib"))
  end
end
