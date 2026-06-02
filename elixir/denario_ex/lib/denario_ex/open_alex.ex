defmodule DenarioEx.OpenAlex do
  @moduledoc """
  OpenAlex search adapter used as a public fallback when Semantic Scholar is
  unavailable or rate-limited.
  """

  @behaviour DenarioEx.SemanticScholarClient

  @base_url "https://api.openalex.org/works"
  @select_fields [
    "id",
    "title",
    "doi",
    "publication_year",
    "cited_by_count",
    "relevance_score",
    "type",
    "authorships",
    "primary_location",
    "ids",
    "open_access",
    "abstract_inverted_index"
  ]

  @impl true
  def search(query, _keys, opts \\ []) do
    limit = Keyword.get(opts, :limit, 20)

    params = [
      {"search", query},
      {"per-page", Integer.to_string(limit)},
      {"select", Enum.join(@select_fields, ",")},
      {"filter", "has_abstract:true,from_publication_date:2010-01-01"}
    ]

    request =
      Req.new(
        url: @base_url,
        connect_options: [timeout: 15_000],
        receive_timeout: 30_000
      )

    case Req.get(request, params: params) do
      {:ok, %{status: 200, body: %{"results" => results}}} when is_list(results) ->
        {:ok, %{"data" => Enum.map(results, &normalize_work/1), "source" => "openalex"}}

      {:ok, %{status: status, body: body}} ->
        {:error, {:openalex_http_error, status, body}}

      {:error, error} ->
        {:error, {:openalex_request_error, Exception.message(error)}}
    end
  end

  defp normalize_work(work) do
    %{
      "paperId" => openalex_id(work),
      "title" => Map.get(work, "title"),
      "year" => Map.get(work, "publication_year"),
      "citationCount" => Map.get(work, "cited_by_count"),
      "relevanceScore" => Map.get(work, "relevance_score"),
      "publicationType" => Map.get(work, "type"),
      "abstract" => reconstruct_abstract(Map.get(work, "abstract_inverted_index")),
      "url" => landing_page_url(work),
      "authors" => normalize_authors(Map.get(work, "authorships", [])),
      "externalIds" => normalize_external_ids(work),
      "openAccessPdf" => %{"url" => pdf_url(work)},
      "retrievalSource" => "OpenAlex"
    }
  end

  defp openalex_id(work) do
    work
    |> Map.get("id", "")
    |> String.replace_prefix("https://openalex.org/", "")
  end

  defp landing_page_url(work) do
    get_in(work, ["primary_location", "landing_page_url"]) ||
      get_in(work, ["ids", "doi"]) ||
      Map.get(work, "id")
  end

  defp pdf_url(work) do
    get_in(work, ["primary_location", "pdf_url"]) ||
      get_in(work, ["open_access", "oa_url"])
  end

  defp normalize_authors(authorships) when is_list(authorships) do
    Enum.map(authorships, fn authorship ->
      %{"name" => get_in(authorship, ["author", "display_name"]) || "Unknown"}
    end)
  end

  defp normalize_authors(_), do: []

  defp normalize_external_ids(work) do
    ids = Map.get(work, "ids", %{})

    ids
    |> Enum.reduce(%{}, fn
      {"doi", value}, acc when is_binary(value) -> Map.put(acc, "DOI", value)
      {"pmid", value}, acc when is_binary(value) -> Map.put(acc, "PubMed", value)
      {"pmcid", value}, acc when is_binary(value) -> Map.put(acc, "PMCID", value)
      {_key, _value}, acc -> acc
    end)
  end

  defp reconstruct_abstract(nil), do: nil

  defp reconstruct_abstract(index) when is_map(index) do
    index
    |> Enum.flat_map(fn {word, positions} ->
      Enum.map(positions, fn position -> {position, word} end)
    end)
    |> Enum.sort_by(fn {position, _word} -> position end)
    |> Enum.map_join(" ", fn {_position, word} -> word end)
  end

  defp reconstruct_abstract(_), do: nil
end
