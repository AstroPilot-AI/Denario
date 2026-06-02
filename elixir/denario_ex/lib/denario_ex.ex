defmodule DenarioEx do
  @moduledoc """
  Initial Elixir port of the core Denario session model.

  This module mirrors the Python project's project-directory lifecycle and the
  ReqLLM/LLMDB-backed "fast" idea/method generation path.
  """

  alias DenarioEx.{
    AI,
    CMBAgentLoop,
    KeyManager,
    LLM,
    LiteratureWorkflow,
    PaperWorkflow,
    PromptTemplates,
    ReqLLMClient,
    Research,
    ResultsWorkflow,
    Text
  }

  @default_project_name "project"
  @input_files "input_files"
  @plots_folder "plots"
  @paper_folder "paper"
  @description_file "data_description.md"
  @idea_file "idea.md"
  @method_file "methods.md"
  @results_file "results.md"
  @literature_file "literature.md"
  @paper_tex_file "paper_v4_final.tex"
  @paper_pdf_file "paper_v4_final.pdf"

  @enforce_keys [:project_dir, :input_files_dir, :plots_dir, :keys, :research]
  defstruct [:project_dir, :input_files_dir, :plots_dir, :keys, :research]

  @type t :: %__MODULE__{
          project_dir: String.t(),
          input_files_dir: String.t(),
          plots_dir: String.t(),
          keys: KeyManager.t(),
          research: Research.t()
        }

  @type option ::
          {:project_dir, String.t()}
          | {:clear_project_dir, boolean()}
          | {:keys, KeyManager.t()}
          | {:research, Research.t()}

  @type generation_option ::
          {:llm, String.t() | LLM.t()}
          | {:iterations, pos_integer()}
          | {:client, module()}

  @spec new([option()]) :: {:ok, t()}
  def new(opts \\ []) do
    project_dir =
      opts
      |> Keyword.get(:project_dir, Path.join(File.cwd!(), @default_project_name))
      |> Path.expand()

    clear_project_dir? = Keyword.get(opts, :clear_project_dir, false)

    if clear_project_dir? and File.exists?(project_dir) do
      File.rm_rf!(project_dir)
    end

    input_files_dir = Path.join(project_dir, @input_files)
    plots_dir = Path.join(input_files_dir, @plots_folder)

    File.mkdir_p!(plots_dir)

    session = %__MODULE__{
      project_dir: project_dir,
      input_files_dir: input_files_dir,
      plots_dir: plots_dir,
      keys: Keyword.get(opts, :keys, KeyManager.from_env()),
      research: Keyword.get(opts, :research, %Research{})
    }

    {:ok, load_existing_content(session)}
  end

  @spec set_data_description(t(), String.t()) :: {:ok, t()}
  def set_data_description(%__MODULE__{} = session, data_description) do
    write_field(session, @description_file, data_description, :data_description)
  end

  @spec set_idea(t(), String.t()) :: {:ok, t()}
  def set_idea(%__MODULE__{} = session, idea) do
    write_field(session, @idea_file, idea, :idea)
  end

  @spec set_method(t(), String.t()) :: {:ok, t()}
  def set_method(%__MODULE__{} = session, method) do
    write_field(session, @method_file, method, :methodology)
  end

  @spec set_results(t(), String.t()) :: {:ok, t()}
  def set_results(%__MODULE__{} = session, results) do
    write_field(session, @results_file, results, :results)
  end

  @spec set_literature(t(), String.t()) :: {:ok, t()}
  def set_literature(%__MODULE__{} = session, literature) do
    write_field(session, @literature_file, literature, :literature)
  end

  @spec set_plots(t(), [String.t()] | nil) :: {:ok, t()}
  def set_plots(%__MODULE__{} = session, plots \\ nil) do
    plot_paths =
      case plots do
        nil -> Path.wildcard(Path.join(session.plots_dir, "*.png"))
        values -> values
      end

    copied_paths =
      Enum.map(plot_paths, fn plot_path ->
        destination = Path.join(session.plots_dir, Path.basename(plot_path))
        File.cp!(plot_path, destination)
        destination
      end)

    {:ok, %{session | research: %{session.research | plot_paths: copied_paths}}}
  end

  @spec show_data_description(t()) :: String.t()
  def show_data_description(%__MODULE__{} = session), do: session.research.data_description

  @spec show_idea(t()) :: String.t()
  def show_idea(%__MODULE__{} = session), do: session.research.idea

  @spec show_method(t()) :: String.t()
  def show_method(%__MODULE__{} = session), do: session.research.methodology

  @spec show_results(t()) :: String.t()
  def show_results(%__MODULE__{} = session), do: session.research.results

  @spec show_literature(t()) :: String.t()
  def show_literature(%__MODULE__{} = session), do: session.research.literature

  @spec get_idea(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def get_idea(%__MODULE__{} = session, opts \\ []) do
    case Keyword.get(opts, :mode, "fast") do
      mode when mode in ["fast", :fast] -> get_idea_fast(session, opts)
      mode when mode in ["cmbagent", :cmbagent] -> get_idea_cmbagent(session, opts)
      other -> {:error, {:invalid_mode, other}}
    end
  end

  @spec get_method(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def get_method(%__MODULE__{} = session, opts \\ []) do
    case Keyword.get(opts, :mode, "fast") do
      mode when mode in ["fast", :fast] -> get_method_fast(session, opts)
      mode when mode in ["cmbagent", :cmbagent] -> get_method_cmbagent(session, opts)
      other -> {:error, {:invalid_mode, other}}
    end
  end

  @spec get_idea_fast(t(), [generation_option()]) :: {:ok, t()} | {:error, term()}
  def get_idea_fast(%__MODULE__{} = session, opts \\ []) do
    iterations = Keyword.get(opts, :iterations, 4)
    client = Keyword.get(opts, :client, ReqLLMClient)

    with {:ok, llm} <- LLM.parse(Keyword.get(opts, :llm, "gpt-4.1-mini")),
         {:ok, final_idea} <- iterate_idea(session, client, llm, iterations, 0, "", ""),
         {:ok, updated} <- set_idea(session, final_idea) do
      {:ok, updated}
    end
  end

  @spec get_idea_cmbagent(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def get_idea_cmbagent(%__MODULE__{} = session, opts \\ []) do
    client = Keyword.get(opts, :client, ReqLLMClient)

    with :ok <- ensure_present(session.research.data_description, :data_description),
         {:ok, idea_maker_llm} <- LLM.parse(Keyword.get(opts, :idea_maker_model, "gpt-4o")),
         {:ok, idea_hater_llm} <- LLM.parse(Keyword.get(opts, :idea_hater_model, "o3-mini")),
         {:ok, final_llm} <- LLM.parse(Keyword.get(opts, :formatter_model, idea_maker_llm)),
         {:ok, run} <-
           CMBAgentLoop.run_text_task(
             "idea",
             %{data_description: session.research.data_description},
             client: client,
             keys: session.keys,
             planner_model: Keyword.get(opts, :planner_model, "gpt-4o"),
             plan_reviewer_model: Keyword.get(opts, :plan_reviewer_model, "o3-mini"),
             allowed_agents: ["idea_maker", "idea_hater"],
             max_steps: Keyword.get(opts, :max_n_steps, 6),
             agent_models: %{
               "idea_maker" => idea_maker_llm,
               "idea_hater" => idea_hater_llm
             },
             final_model: final_llm
           ),
         {:ok, updated} <- set_idea(session, run.output) do
      {:ok, updated}
    end
  end

  @spec get_method_fast(t(), [generation_option()]) :: {:ok, t()} | {:error, term()}
  def get_method_fast(%__MODULE__{} = session, opts \\ []) do
    client = Keyword.get(opts, :client, ReqLLMClient)

    with {:ok, llm} <- LLM.parse(Keyword.get(opts, :llm, "gpt-4.1-mini")),
         :ok <- ensure_present(session.research.data_description, :data_description),
         :ok <- ensure_present(session.research.idea, :idea),
         prompt <-
           PromptTemplates.methods_fast_prompt(
             session.research.data_description,
             session.research.idea
           ),
         {:ok, raw_text} <- complete(client, prompt, llm, session.keys),
         {:ok, methods} <- Text.extract_block(raw_text, "METHODS"),
         cleaned <- Text.clean_section(methods, "METHODS"),
         {:ok, updated} <- set_method(session, cleaned) do
      {:ok, updated}
    end
  end

  @spec get_method_cmbagent(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def get_method_cmbagent(%__MODULE__{} = session, opts \\ []) do
    client = Keyword.get(opts, :client, ReqLLMClient)

    with :ok <- ensure_present(session.research.data_description, :data_description),
         :ok <- ensure_present(session.research.idea, :idea),
         {:ok, method_llm} <- LLM.parse(Keyword.get(opts, :method_generator_model, "gpt-4o")),
         {:ok, final_llm} <- LLM.parse(Keyword.get(opts, :formatter_model, method_llm)),
         {:ok, run} <-
           CMBAgentLoop.run_text_task(
             "method",
             %{
               data_description: session.research.data_description,
               idea: session.research.idea
             },
             client: client,
             keys: session.keys,
             planner_model: Keyword.get(opts, :planner_model, "gpt-4o"),
             plan_reviewer_model: Keyword.get(opts, :plan_reviewer_model, "o3-mini"),
             allowed_agents: ["researcher"],
             max_steps: Keyword.get(opts, :max_n_steps, 4),
             agent_models: %{"researcher" => method_llm},
             final_model: final_llm
           ),
         {:ok, updated} <- set_method(session, run.output) do
      {:ok, updated}
    end
  end

  @spec check_idea(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def check_idea(%__MODULE__{} = session, opts \\ []) do
    case Keyword.get(opts, :mode, :semantic_scholar) do
      mode when mode in [:semantic_scholar, "semantic_scholar"] ->
        with :ok <- ensure_present(session.research.data_description, :data_description),
             :ok <- ensure_present(session.research.idea, :idea),
             {:ok, result} <- LiteratureWorkflow.run(session, opts),
             {:ok, updated} <- set_literature(session, result.literature) do
          {:ok,
           %{
             updated
             | research: %{
                 updated.research
                 | literature_sources: result.sources
               }
           }}
        end

      other ->
        {:error, {:unsupported_literature_mode, other}}
    end
  end

  @spec get_results(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def get_results(%__MODULE__{} = session, opts \\ []) do
    with :ok <- ensure_present(session.research.data_description, :data_description),
         :ok <- ensure_present(session.research.idea, :idea),
         :ok <- ensure_present(session.research.methodology, :methodology),
         {:ok, result} <- ResultsWorkflow.run(session, opts),
         {:ok, updated} <- set_results(session, result.results),
         {:ok, updated} <- set_plots(updated, result.plot_paths) do
      {:ok, updated}
    end
  end

  @spec get_paper(t(), keyword()) :: {:ok, t()} | {:error, term()}
  def get_paper(%__MODULE__{} = session, opts \\ []) do
    with :ok <- ensure_present(session.research.idea, :idea),
         :ok <- ensure_present(session.research.methodology, :methodology),
         :ok <- ensure_present(session.research.results, :results),
         {:ok, result} <- PaperWorkflow.run(session, opts) do
      {:ok,
       %{
         session
         | research: %{
             session.research
             | keywords: result.keywords,
               paper_tex_path: result.tex_path,
               paper_pdf_path: result.pdf_path
           }
       }}
    end
  end

  defp iterate_idea(
         _session,
         _client,
         _llm,
         total_iterations,
         current_iteration,
         previous_ideas,
         _criticism
       )
       when current_iteration >= total_iterations do
    last_idea =
      previous_ideas
      |> String.split("Idea:", trim: true)
      |> List.last()
      |> case do
        nil -> ""
        value -> String.trim(value)
      end

    {:ok, last_idea}
  end

  defp iterate_idea(
         session,
         client,
         llm,
         total_iterations,
         current_iteration,
         previous_ideas,
         criticism
       ) do
    prompt =
      PromptTemplates.idea_maker_prompt(
        session.research.data_description,
        previous_ideas,
        criticism,
        current_iteration
      )

    with {:ok, maker_text} <- complete(client, prompt, llm, session.keys),
         {:ok, idea} <- Text.extract_block(maker_text, "IDEA") do
      cleaned_idea = Text.clean_section(idea, "IDEA")

      updated_previous_ideas =
        previous_ideas <>
          "\n\nIteration #{current_iteration}:\nIdea: #{cleaned_idea}\n"

      if current_iteration + 1 >= total_iterations do
        {:ok, cleaned_idea}
      else
        critic_prompt =
          PromptTemplates.idea_hater_prompt(
            session.research.data_description,
            updated_previous_ideas,
            cleaned_idea
          )

        with {:ok, critic_text} <- complete(client, critic_prompt, llm, session.keys),
             {:ok, criticism} <- Text.extract_block(critic_text, "CRITIC") do
          iterate_idea(
            session,
            client,
            llm,
            total_iterations,
            current_iteration + 1,
            updated_previous_ideas,
            Text.clean_section(criticism, "CRITIC")
          )
        end
      end
    end
  end

  defp complete(client, prompt, %LLM{} = llm, %KeyManager{} = keys) do
    AI.complete(client, prompt, llm, keys)
  end

  defp ensure_present("", field), do: {:error, {:missing_field, field}}
  defp ensure_present(nil, field), do: {:error, {:missing_field, field}}
  defp ensure_present(_, _field), do: :ok

  defp write_field(%__MODULE__{} = session, filename, value, field) do
    content = read_content!(value)
    destination = Path.join(session.input_files_dir, filename)
    File.write!(destination, content)
    updated_research = Map.put(session.research, field, content)
    {:ok, %{session | research: updated_research}}
  end

  defp read_content!(value) when is_binary(value) do
    if String.ends_with?(value, ".md") and File.regular?(value) do
      File.read!(value)
    else
      value
    end
  end

  defp load_existing_content(%__MODULE__{} = session) do
    research =
      session.research
      |> maybe_load_field(session.input_files_dir, @description_file, :data_description)
      |> maybe_load_field(session.input_files_dir, @idea_file, :idea)
      |> maybe_load_field(session.input_files_dir, @method_file, :methodology)
      |> maybe_load_field(session.input_files_dir, @results_file, :results)
      |> maybe_load_field(session.input_files_dir, @literature_file, :literature)
      |> Map.put(:plot_paths, Path.wildcard(Path.join(session.plots_dir, "*.png")))
      |> maybe_set_path(
        Path.join(session.project_dir, @paper_folder),
        @paper_tex_file,
        :paper_tex_path
      )
      |> maybe_set_path(
        Path.join(session.project_dir, @paper_folder),
        @paper_pdf_file,
        :paper_pdf_path
      )

    %{session | research: research}
  end

  defp maybe_load_field(research, input_files_dir, filename, field) do
    path = Path.join(input_files_dir, filename)

    if File.regular?(path) do
      Map.put(research, field, File.read!(path))
    else
      research
    end
  end

  defp maybe_set_path(research, folder, filename, field) do
    path = Path.join(folder, filename)

    if File.regular?(path) do
      Map.put(research, field, path)
    else
      research
    end
  end
end
