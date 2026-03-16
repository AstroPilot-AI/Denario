defmodule DenarioEx.LiteratureWorkflowResilienceTest do
  use ExUnit.Case, async: true

  alias DenarioEx
  alias DenarioExWorkflowsTest.FakeClient

  defmodule RateLimitedSemanticScholarClient do
    @behaviour DenarioEx.SemanticScholarClient

    @impl true
    def search(_query, _keys, _opts) do
      {:error, {:semantic_scholar_http_error, 429, %{"message" => "Too Many Requests"}}}
    end
  end

  defmodule FailingFallbackClient do
    @behaviour DenarioEx.SemanticScholarClient

    @impl true
    def search(_query, _keys, _opts) do
      {:error, {:openalex_http_error, 503, %{"message" => "Unavailable"}}}
    end
  end

  setup do
    project_dir =
      Path.join(
        System.tmp_dir!(),
        "denario_ex_lit_resilience_#{System.unique_integer([:positive])}"
      )

    on_exit(fn -> File.rm_rf(project_dir) end)
    {:ok, project_dir: project_dir}
  end

  test "check_idea degrades cleanly when Semantic Scholar rate limits the request", %{
    project_dir: project_dir
  } do
    assert {:ok, denario} = DenarioEx.new(project_dir: project_dir, clear_project_dir: true)

    assert {:ok, denario} =
             DenarioEx.set_data_description(denario, "Synthetic anomaly-score study.")

    assert {:ok, denario} = DenarioEx.set_idea(denario, "Interpret synthetic anomaly scores.")

    assert {:ok, denario} =
             DenarioEx.check_idea(
               denario,
               client: FakeClient,
               semantic_scholar_client: RateLimitedSemanticScholarClient,
               fallback_literature_client: FailingFallbackClient,
               llm: "openai:gpt-4.1-mini",
               max_iterations: 2
             )

    assert String.contains?(denario.research.literature, "Idea literature search unavailable")
    assert denario.research.literature_sources == []
  end
end
