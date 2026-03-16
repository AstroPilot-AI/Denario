defmodule DenarioEx.LiteratureWorkflow do
  @moduledoc false

  alias DenarioEx.{AI, LLM, OpenAlex, ReqLLMClient, SemanticScholar, Text, WorkflowPrompts}

  @decision_schema %{
    "type" => "object",
    "additionalProperties" => false,
    "properties" => %{
      "reason" => %{"type" => "string"},
      "decision" => %{"type" => "string", "enum" => ["novel", "not novel", "query"]},
      "query" => %{"type" => "string"}
    },
    "required" => ["reason", "decision", "query"]
  }

  @selection_schema %{
    "type" => "object",
    "additionalProperties" => false,
    "properties" => %{
      "selected_paper_ids" => %{"type" => "array", "items" => %{"type" => "string"}},
      "rationale" => %{"type" => "string"}
    },
    "required" => ["selected_paper_ids", "rationale"]
  }

  @spec run(DenarioEx.t(), keyword()) :: {:ok, map()} | {:error, term()}
  def run(session, opts \\ []) do
    client = Keyword.get(opts, :client, ReqLLMClient)
    semantic_scholar_client = Keyword.get(opts, :semantic_scholar_client, SemanticScholar)
    fallback_literature_client = Keyword.get(opts, :fallback_literature_client, OpenAlex)
    max_iterations = Keyword.get(opts, :max_iterations, 7)
    literature_dir = Path.join(session.project_dir, "literature_output")
    literature_log = Path.join(literature_dir, "literature.log")

    context = %{
      data_description: session.research.data_description,
      idea: session.research.idea
    }

    with {:ok, llm} <- LLM.parse(Keyword.get(opts, :llm, "gemini-2.5-flash")),
         {:ok, state} <-
           iterate(
             0,
             max_iterations,
             %{messages: "", papers_text: "", decision: "query", sources: []},
             context,
             client,
             semantic_scholar_client,
             fallback_literature_client,
             llm,
             session.keys,
             literature_log
           ),
         summary_prompt <-
           WorkflowPrompts.literature_summary_prompt(context, state.decision, state.messages),
         {:ok, summary_text} <- AI.complete(client, summary_prompt, llm, session.keys),
         {:ok, block} <- Text.extract_block_or_fallback(summary_text, "SUMMARY") do
      File.mkdir_p!(literature_dir)

      {:ok,
       %{
         literature: "Idea #{state.decision}\n\n" <> block,
         sources: state.sources,
         decision: state.decision,
         log_path: literature_log
       }}
    end
  end

  defp iterate(
         iteration,
         max_iterations,
         state,
         context,
         client,
         semantic_scholar_client,
         fallback_literature_client,
         llm,
         keys,
         literature_log
       ) do
    prompt =
      WorkflowPrompts.literature_decision_prompt(
        context,
        iteration,
        max_iterations,
        state.messages,
        state.papers_text
      )

    with {:ok, object} <- AI.generate_object(client, prompt, @decision_schema, llm, keys),
         decision <- normalize_decision(Text.fetch(object, "decision")),
         reason <- Text.fetch(object, "reason") || "",
         query <- Text.fetch(object, "query") || "" do
      messages =
        state.messages <>
          "\nRound #{iteration}\nDecision: #{decision}\nReason: #{reason}\nQuery: #{query}\n"

      cond do
        decision in ["novel", "not novel"] ->
          {:ok, %{state | messages: messages, decision: decision}}

        iteration + 1 >= max_iterations ->
          {:ok, %{state | messages: messages, decision: "novel"}}

        true ->
          case semantic_scholar_client.search(query, keys, limit: 20) do
            {:ok, result} ->
              {papers_text, new_sources} =
                normalize_papers(result, context, query, client, llm, keys)

              File.mkdir_p!(Path.dirname(literature_log))
              File.write!(literature_log, papers_text, [:append])

              iterate(
                iteration + 1,
                max_iterations,
                %{
                  state
                  | messages: messages,
                    papers_text: papers_text,
                    sources: merge_sources(state.sources, new_sources),
                    decision: "query"
                },
                context,
                client,
                semantic_scholar_client,
                fallback_literature_client,
                llm,
                keys,
                literature_log
              )

            {:error, error} ->
              handle_primary_search_error(
                error,
                query,
                state,
                messages,
                context,
                iteration,
                max_iterations,
                client,
                semantic_scholar_client,
                fallback_literature_client,
                llm,
                keys,
                literature_log
              )
          end
      end
    end
  end

  defp normalize_papers(result, context, query, client, llm, keys) do
    papers = Text.fetch(result, "data") || []

    normalized =
      Enum.filter(papers, fn paper ->
        abstract = Text.fetch(paper, "abstract")
        is_binary(abstract) and abstract != ""
      end)

    {selected_papers, selection_note} =
      select_relevant_papers(normalized, context, query, client, llm, keys)

    papers_text =
      if selected_papers == [] do
        selection_note <>
          "\nNo directly relevant papers were selected from the retrieved candidates.\n"
      else
        selection_note <> "\n" <> render_papers_text(selected_papers)
      end

    {papers_text, selected_papers}
  end

  defp merge_sources(existing, incoming) do
    {_, merged} =
      Enum.reduce(existing ++ incoming, {MapSet.new(), []}, fn source, {seen, acc} ->
        key =
          Text.fetch(source, "paperId") ||
            Text.slugify(Text.fetch(source, "title") || "paper")

        if MapSet.member?(seen, key) do
          {seen, acc}
        else
          {MapSet.put(seen, key), acc ++ [source]}
        end
      end)

    merged
  end

  defp normalize_decision(decision) when is_binary(decision) do
    decision
    |> String.downcase()
    |> String.trim()
  end

  defp normalize_decision(_decision), do: "query"

  defp select_relevant_papers([], _context, _query, _client, _llm, _keys), do: {[], ""}

  defp select_relevant_papers(papers, context, query, client, llm, keys) do
    ranked = rank_papers(papers, context, query)
    candidates = Enum.take(ranked, 10)
    focus = focus_terms(context, query)

    prompt =
      WorkflowPrompts.literature_selection_prompt(
        context,
        query,
        render_papers_text(candidates, include_ids?: true, include_scores?: true)
      )

    case AI.generate_object(client, prompt, @selection_schema, llm, keys) do
      {:ok, selection} ->
        selected_ids = normalize_string_list(Text.fetch(selection, "selected_paper_ids"))
        rationale = Text.fetch(selection, "rationale") || ""
        selected = filter_selected_papers(candidates, selected_ids, focus)
        {selected, "Selection rationale: #{rationale}\n"}

      {:error, _error} ->
        fallback =
          candidates
          |> Enum.take(5)
          |> Enum.filter(&paper_matches_focus?(&1, focus))

        {fallback, "Selection rationale: heuristic ranking fallback.\n"}
    end
  end

  defp rank_papers(papers, context, query) do
    query_terms =
      tokenize(
        "#{Map.get(context, :data_description, "")} #{Map.get(context, :idea, "")} #{query}"
      )
      |> MapSet.new()

    Enum.sort_by(
      papers,
      fn paper ->
        title = Text.fetch(paper, "title") || ""
        abstract = Text.fetch(paper, "abstract") || ""
        title_terms = tokenize(title) |> MapSet.new()
        abstract_terms = tokenize(abstract) |> MapSet.new()
        title_overlap = MapSet.intersection(query_terms, title_terms) |> MapSet.size()
        abstract_overlap = MapSet.intersection(query_terms, abstract_terms) |> MapSet.size()
        year = safe_integer(Text.fetch(paper, "year"))
        citation_count = safe_integer(Text.fetch(paper, "citationCount"))
        relevance_score = safe_float(Text.fetch(paper, "relevanceScore"))

        generic_penalty =
          if generic_paper?(paper) and title_overlap < 2 do
            4.0
          else
            0.0
          end

        title_overlap * 3.0 + abstract_overlap + year_bonus(year) +
          :math.log10(citation_count + 1) + relevance_score - generic_penalty
      end,
      :desc
    )
  end

  defp render_papers_text(papers, opts \\ []) do
    include_ids? = Keyword.get(opts, :include_ids?, false)
    include_scores? = Keyword.get(opts, :include_scores?, false)

    Enum.map_join(papers, "\n\n", fn paper ->
      authors =
        paper
        |> Text.fetch("authors")
        |> List.wrap()
        |> Enum.map_join(", ", fn author -> Text.fetch(author, "name") || "Unknown" end)

      id_line =
        if include_ids? do
          "Paper ID: #{Text.fetch(paper, "paperId")}\n"
        else
          ""
        end

      score_line =
        if include_scores? do
          "Citation count: #{safe_integer(Text.fetch(paper, "citationCount"))}\n"
        else
          ""
        end

      """
      #{id_line}Title: #{Text.fetch(paper, "title")}
      Year: #{Text.fetch(paper, "year")}
      #{score_line}Authors: #{authors}
      Abstract: #{Text.fetch(paper, "abstract")}
      URL: #{Text.fetch(paper, "url")}
      """
    end) <> "\n"
  end

  defp filter_selected_papers(papers, selected_ids, focus_terms) do
    Enum.filter(papers, fn paper ->
      id = Text.fetch(paper, "paperId")
      id in selected_ids and paper_matches_focus?(paper, focus_terms)
    end)
  end

  defp normalize_string_list(values) when is_list(values) do
    values
    |> Enum.filter(&is_binary/1)
    |> Enum.map(&String.trim/1)
    |> Enum.reject(&(&1 == ""))
  end

  defp normalize_string_list(_), do: []

  defp tokenize(text) do
    stopwords =
      MapSet.new(~w(
          a an and are as at be by for from in into is it of on or that the this to using with over within
          data analysis workflow workflows using python plotting visualization visualisation tutorial tutorials
          pipeline pipelines study studies method methods system systems approach approaches result results
          generate generated small minimal hands handson journey building external required
          experiment experiments tiny list directly print save keep self contained concise propose paper
          simple scientific mean png
        ))

    text
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9\s]+/u, " ")
    |> String.split(~r/\s+/, trim: true)
    |> Enum.reject(&(String.length(&1) < 3 or MapSet.member?(stopwords, &1)))
  end

  defp generic_paper?(paper) do
    haystack =
      "#{Text.fetch(paper, "title") || ""} #{Text.fetch(paper, "abstract") || ""}"
      |> String.downcase()

    Enum.any?(["survey", "review", "overview", "tutorial"], &String.contains?(haystack, &1))
  end

  defp focus_terms(context, query) do
    "#{Map.get(context, :idea, "")} #{query}"
    |> tokenize()
    |> MapSet.new()
  end

  defp paper_matches_focus?(_paper, focus_terms) when map_size(focus_terms) == 0, do: true

  defp paper_matches_focus?(paper, focus_terms) do
    paper_terms =
      "#{Text.fetch(paper, "title") || ""} #{Text.fetch(paper, "abstract") || ""}"
      |> tokenize()
      |> MapSet.new()

    overlap = MapSet.intersection(focus_terms, paper_terms) |> MapSet.size()
    overlap >= min(2, map_size(focus_terms))
  end

  defp year_bonus(year) when year >= 2020, do: 2.0
  defp year_bonus(year) when year >= 2015, do: 1.0
  defp year_bonus(_year), do: 0.0

  defp safe_integer(value) when is_integer(value), do: value
  defp safe_integer(value) when is_float(value), do: round(value)
  defp safe_integer(_value), do: 0

  defp safe_float(value) when is_float(value), do: value
  defp safe_float(value) when is_integer(value), do: value * 1.0
  defp safe_float(_value), do: 0.0

  defp handle_primary_search_error(
         error,
         query,
         state,
         messages,
         context,
         iteration,
         max_iterations,
         client,
         semantic_scholar_client,
         fallback_literature_client,
         llm,
         keys,
         literature_log
       ) do
    primary_failure_note = search_failure_note(error)

    case fallback_literature_client.search(query, keys, limit: 20) do
      {:ok, result} ->
        {papers_text, new_sources} =
          normalize_papers(result, context, query, client, llm, keys)

        File.mkdir_p!(Path.dirname(literature_log))

        File.write!(
          literature_log,
          primary_failure_note <> "\nFalling back to OpenAlex.\n" <> papers_text,
          [:append]
        )

        iterate(
          iteration + 1,
          max_iterations,
          %{
            state
            | messages:
                messages <>
                  "Search status: #{primary_failure_note} Falling back to OpenAlex.\n",
              papers_text: papers_text,
              sources: merge_sources(state.sources, new_sources),
              decision: "query"
          },
          context,
          client,
          semantic_scholar_client,
          fallback_literature_client,
          llm,
          keys,
          literature_log
        )

      {:error, fallback_error} ->
        failure_note =
          primary_failure_note <>
            " OpenAlex fallback also failed: #{search_failure_note(fallback_error)}"

        File.mkdir_p!(Path.dirname(literature_log))
        File.write!(literature_log, failure_note <> "\n", [:append])

        {:ok,
         %{
           state
           | messages: messages <> "Search status: #{failure_note}\n",
             decision: "literature search unavailable"
         }}
    end
  end

  defp search_failure_note({:semantic_scholar_http_error, 429, _body}) do
    "Semantic Scholar rate-limited the request (HTTP 429). The literature check could not be completed from the public API."
  end

  defp search_failure_note({:semantic_scholar_http_error, status, _body}) do
    "Semantic Scholar returned HTTP #{status}. The literature check could not be completed."
  end

  defp search_failure_note({:semantic_scholar_request_error, message}) do
    "Semantic Scholar request failed: #{message}"
  end

  defp search_failure_note({:openalex_http_error, status, _body}) do
    "OpenAlex returned HTTP #{status}."
  end

  defp search_failure_note({:openalex_request_error, message}) do
    "OpenAlex request failed: #{message}"
  end

  defp search_failure_note(error) do
    "Semantic Scholar request failed: #{inspect(error)}"
  end
end
