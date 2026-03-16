defmodule DenarioEx.SemanticScholar do
  @moduledoc """
  Semantic Scholar search adapter.
  """

  @behaviour DenarioEx.SemanticScholarClient

  alias DenarioEx.KeyManager

  @base_url "https://api.semanticscholar.org/graph/v1/paper/search"

  @impl true
  def search(query, %KeyManager{} = keys, opts \\ []) do
    limit = Keyword.get(opts, :limit, 20)

    request =
      Req.new(
        url: @base_url,
        headers: maybe_headers(keys),
        connect_options: [timeout: 15_000],
        receive_timeout: 30_000
      )

    params = [
      query: query,
      limit: limit,
      fields: "title,authors,year,abstract,url,paperId,externalIds,openAccessPdf,citationCount"
    ]

    case Req.get(request, params: params) do
      {:ok, %{status: 200, body: body}} when is_map(body) ->
        {:ok, body}

      {:ok, %{status: status, body: body}} ->
        {:error, {:semantic_scholar_http_error, status, body}}

      {:error, error} ->
        {:error, {:semantic_scholar_request_error, Exception.message(error)}}
    end
  end

  defp maybe_headers(%KeyManager{semantic_scholar: nil}), do: []
  defp maybe_headers(%KeyManager{semantic_scholar: ""}), do: []

  defp maybe_headers(%KeyManager{semantic_scholar: key}) do
    [{"x-api-key", key}]
  end
end
