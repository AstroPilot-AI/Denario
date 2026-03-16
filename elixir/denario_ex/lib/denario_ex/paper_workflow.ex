defmodule DenarioEx.PaperWorkflow do
  @moduledoc false

  alias DenarioEx.{AI, LLM, ReqLLMClient, Text, WorkflowPrompts}

  @asset_dir Path.expand("../../../../denario/paper_agents/LaTeX", __DIR__)

  @abstract_schema %{
    "type" => "object",
    "additionalProperties" => false,
    "properties" => %{
      "title" => %{"type" => "string"},
      "abstract" => %{"type" => "string"}
    },
    "required" => ["title", "abstract"]
  }

  @spec run(DenarioEx.t(), keyword()) :: {:ok, map()} | {:error, term()}
  def run(session, opts \\ []) do
    client = Keyword.get(opts, :client, ReqLLMClient)
    writer = Keyword.get(opts, :writer, "scientist")
    journal = normalize_journal(Keyword.get(opts, :journal, :none))
    add_citations = Keyword.get(opts, :add_citations, true)
    compile? = Keyword.get(opts, :compile, true)
    paper_dir = Path.join(session.project_dir, "paper")
    tex_name = "paper_v4_final.tex"
    tex_path = Path.join(paper_dir, tex_name)
    pdf_path = Path.join(paper_dir, "paper_v4_final.pdf")
    preset = journal_preset(journal)
    plot_paths = available_plot_paths(session)

    with {:ok, llm} <- LLM.parse(Keyword.get(opts, :llm, "gemini-2.5-flash")),
         :ok <- File.mkdir_p(paper_dir),
         :ok <- copy_assets(preset.files, paper_dir),
         citation_context = citation_context(session.research.literature_sources),
         keywords <- existing_keywords(session.research.keywords),
         keywords <-
           maybe_generate_keywords(keywords, client, llm, session.keys, writer, session.research),
         {:ok, abstract_object} <-
           AI.generate_object(
             client,
             WorkflowPrompts.paper_abstract_prompt(
               writer,
               paper_context(session.research),
               citation_context
             ),
             @abstract_schema,
             llm,
             session.keys
           ),
         title = Text.fetch(abstract_object, "title") || "Untitled Paper",
         abstract = Text.fetch(abstract_object, "abstract") || "",
         {:ok, introduction} <-
           generate_section(
             client,
             llm,
             session.keys,
             "Introduction",
             writer,
             section_context(session.research, title, abstract),
             citation_context
           ),
         {:ok, methods} <-
           generate_section(
             client,
             llm,
             session.keys,
             "Methods",
             writer,
             section_context(session.research, title, abstract),
             citation_context
           ),
         {:ok, results} <-
           generate_section(
             client,
             llm,
             session.keys,
             "Results",
             writer,
             section_context(session.research, title, abstract),
             citation_context
           ),
         {:ok, results} <-
           maybe_add_figures(
             plot_paths,
             client,
             llm,
             session.keys,
             writer,
             section_context(session.research, title, abstract)
             |> Map.put(:paper_results, results)
           ),
         {:ok, conclusions} <-
           generate_section(
             client,
             llm,
             session.keys,
             "Conclusions",
             writer,
             section_context(%{session.research | results: results}, title, abstract),
             citation_context
           ),
         :ok <-
           maybe_write_bibliography(paper_dir, add_citations, session.research.literature_sources),
         tex <-
           render_latex(
             preset,
             title,
             abstract,
             keywords,
             introduction,
             methods,
             results,
             conclusions,
             add_citations
           ),
         :ok <- File.write(tex_path, tex),
         {:ok, compiled_pdf_path} <-
           maybe_compile(compile?, tex_name, pdf_path, paper_dir, add_citations) do
      {:ok, %{tex_path: tex_path, pdf_path: compiled_pdf_path, keywords: keywords}}
    end
  end

  defp paper_context(research) do
    %{
      idea: research.idea,
      methodology: research.methodology,
      results: research.results
    }
  end

  defp section_context(research, title, abstract) do
    %{
      title: title,
      abstract: abstract,
      idea: research.idea,
      methodology: research.methodology,
      results: research.results
    }
  end

  defp existing_keywords(keywords) when is_list(keywords), do: Enum.join(keywords, ", ")

  defp existing_keywords(keywords) when is_map(keywords),
    do: Map.keys(keywords) |> Enum.join(", ")

  defp existing_keywords(_keywords), do: ""

  defp maybe_generate_keywords("", client, llm, keys, writer, research) do
    prompt = WorkflowPrompts.paper_keywords_prompt(writer, paper_context(research))

    with {:ok, response} <- AI.complete(client, prompt, llm, keys),
         {:ok, block} <- Text.extract_block_or_fallback(response, "KEYWORDS") do
      block
    else
      _ -> ""
    end
  end

  defp maybe_generate_keywords(keywords, _client, _llm, _keys, _writer, _research), do: keywords

  defp available_plot_paths(session) do
    if session.research.plot_paths == [] do
      Path.wildcard(Path.join(session.project_dir, "input_files/plots/*.png"))
    else
      session.research.plot_paths
    end
  end

  defp generate_section(client, llm, keys, section, writer, context, citation_context) do
    prompt = WorkflowPrompts.paper_section_prompt(section, writer, context, citation_context)
    block_name = String.upcase(section)

    with {:ok, response} <- AI.complete(client, prompt, llm, keys),
         {:ok, block} <- Text.extract_block_or_fallback(response, block_name) do
      {:ok, block}
    end
  end

  defp maybe_add_figures([], _client, _llm, _keys, _writer, context),
    do: {:ok, Map.get(context, :paper_results, "")}

  defp maybe_add_figures(plot_paths, client, llm, keys, writer, context) do
    figure_specs =
      Enum.map_join(plot_paths, "\n\n", fn plot_path ->
        plot_name = Path.basename(plot_path)
        label = "fig:#{Text.slugify(Path.rootname(plot_name))}"

        prompt = WorkflowPrompts.paper_figure_caption_prompt(writer, context, plot_name)

        caption =
          case AI.complete(client, prompt, llm, keys) do
            {:ok, response} ->
              case Text.extract_block_or_fallback(response, "CAPTION") do
                {:ok, block} -> block
                _ -> "Figure generated during the analysis."
              end

            _ ->
              "Figure generated during the analysis."
          end

        """
        File: #{plot_name}
        Label: #{label}
        Caption: #{caption}
        """
      end)

    prompt = WorkflowPrompts.paper_refine_results_prompt(writer, context, figure_specs)

    with {:ok, response} <- AI.complete(client, prompt, llm, keys),
         {:ok, block} <- Text.extract_block_or_fallback(response, "RESULTS") do
      {:ok, normalize_figure_paths(block, plot_paths)}
    end
  end

  defp maybe_write_bibliography(_paper_dir, false, _sources), do: :ok

  defp maybe_write_bibliography(paper_dir, true, sources) do
    bib_path = Path.join(paper_dir, "bibliography.bib")
    entries = Enum.map_join(sources, "\n\n", &bib_entry/1)
    File.write!(bib_path, entries)
    :ok
  end

  defp bib_entry(source) do
    id = Text.fetch(source, "paperId") || Text.slugify(Text.fetch(source, "title") || "paper")

    authors =
      source
      |> Text.fetch("authors")
      |> List.wrap()
      |> Enum.map_join(" and ", fn author ->
        escape_bib(Text.fetch(author, "name") || "Unknown")
      end)

    title = escape_bib(Text.fetch(source, "title") || "Untitled")
    year = Text.fetch(source, "year") || "2025"
    url = escape_bib(Text.fetch(source, "url") || "")

    """
    @article{#{id},
      title = {#{title}},
      author = {#{authors}},
      year = {#{year}},
      url = {#{url}}
    }
    """
  end

  defp citation_context([]), do: ""

  defp citation_context(sources) do
    Enum.map_join(sources, "\n", fn source ->
      id = Text.fetch(source, "paperId") || Text.slugify(Text.fetch(source, "title") || "paper")

      authors =
        source
        |> Text.fetch("authors")
        |> List.wrap()
        |> Enum.map_join(", ", fn author -> Text.fetch(author, "name") || "Unknown" end)

      "#{id}: #{Text.fetch(source, "title")} (#{Text.fetch(source, "year")}) by #{authors}"
    end)
  end

  defp render_latex(
         preset,
         title,
         abstract,
         keywords,
         introduction,
         methods,
         results,
         conclusions,
         add_citations
       ) do
    bibliography_block =
      if add_citations do
        "\\bibliography{bibliography}\n#{preset.bibliography_style}"
      else
        ""
      end

    """
    \\documentclass[#{preset.layout}]{#{preset.article}}
    \\usepackage{amsmath}
    \\usepackage{graphicx}
    \\usepackage{natbib}
    #{preset.usepackage}

    \\begin{document}
    #{preset.title.(title)}
    #{preset.author.("Denario")}
    #{preset.affiliation.("Anthropic, Gemini \\& OpenAI servers. Planet Earth.")}
    #{preset.abstract.(abstract)}
    #{preset.keywords.(keywords)}

    \\section{Introduction}
    #{introduction}

    \\section{Methods}
    #{methods}

    \\section{Results}
    #{results}

    \\section{Conclusions}
    #{conclusions}

    #{bibliography_block}
    \\end{document}
    """
  end

  defp maybe_compile(false, _tex_name, _pdf_path, _paper_dir, _add_citations), do: {:ok, nil}

  defp maybe_compile(true, tex_name, pdf_path, paper_dir, add_citations) do
    if System.find_executable("xelatex") do
      compile_tex(tex_name, pdf_path, paper_dir, add_citations)
    else
      {:ok, nil}
    end
  end

  defp compile_tex(tex_name, pdf_path, paper_dir, add_citations) do
    {output_1, status_1} =
      System.cmd("xelatex", ["-interaction=nonstopmode", tex_name],
        cd: paper_dir,
        stderr_to_stdout: true
      )

    if status_1 != 0 do
      {:error, {:latex_compile_failed, output_1}}
    else
      if add_citations and File.exists?(Path.join(paper_dir, "bibliography.bib")) and
           System.find_executable("bibtex") do
        base = Path.rootname(tex_name)
        System.cmd("bibtex", [base], cd: paper_dir, stderr_to_stdout: true)
      end

      System.cmd("xelatex", ["-interaction=nonstopmode", tex_name],
        cd: paper_dir,
        stderr_to_stdout: true
      )

      System.cmd("xelatex", ["-interaction=nonstopmode", tex_name],
        cd: paper_dir,
        stderr_to_stdout: true
      )

      {:ok, if(File.exists?(pdf_path), do: pdf_path, else: nil)}
    end
  end

  defp copy_assets(files, paper_dir) do
    Enum.each(files, fn file ->
      source = Path.join(@asset_dir, file)
      destination = Path.join(paper_dir, file)

      if File.exists?(source) do
        File.cp!(source, destination)
      end
    end)

    :ok
  end

  defp normalize_figure_paths(text, plot_paths) do
    Enum.reduce(plot_paths, text, fn plot_path, acc ->
      basename = Path.basename(plot_path)
      normalized = "../input_files/plots/#{basename}"

      Regex.replace(
        ~r/(\\includegraphics(?:\[[^\]]*\])?\{)([^}]*#{Regex.escape(basename)})\}/,
        acc,
        fn _match, prefix, _old_path -> "#{prefix}#{normalized}}" end
      )
    end)
  end

  defp normalize_journal(nil), do: :none
  defp normalize_journal(:none), do: :none
  defp normalize_journal("none"), do: :none
  defp normalize_journal(:aas), do: :aas
  defp normalize_journal("AAS"), do: :aas
  defp normalize_journal(:aps), do: :aps
  defp normalize_journal("APS"), do: :aps
  defp normalize_journal(:icml), do: :icml
  defp normalize_journal("ICML"), do: :icml
  defp normalize_journal(:jhep), do: :jhep
  defp normalize_journal("JHEP"), do: :jhep
  defp normalize_journal(:neurips), do: :neurips
  defp normalize_journal("NeurIPS"), do: :neurips
  defp normalize_journal(:pasj), do: :pasj
  defp normalize_journal("PASJ"), do: :pasj
  defp normalize_journal(_journal), do: :none

  defp journal_preset(:aas) do
    %{
      article: "aastex631",
      layout: "twocolumn",
      usepackage: "\\usepackage{aas_macros}",
      title: &"\\title{#{&1}}",
      author: &"\\author{#{&1}}",
      affiliation: &"\\affiliation{#{&1}}",
      abstract: &"\\begin{abstract}\n#{&1}\n\\end{abstract}",
      keywords: &"\\keywords{#{&1}}",
      bibliography_style: "\\bibliographystyle{aasjournal}",
      files: ["aasjournal.bst", "aastex631.cls", "aas_macros.sty"]
    }
  end

  defp journal_preset(:aps) do
    %{
      article: "revtex4-2",
      layout: "aps",
      usepackage: "",
      title: &"\\title{#{&1}}",
      author: &"\\author{#{&1}}",
      affiliation: &"\\affiliation{#{&1}}",
      abstract: &"\\begin{abstract}\n#{&1}\n\\end{abstract}\n\\maketitle",
      keywords: fn _ -> "" end,
      bibliography_style: "\\bibliographystyle{unsrt}",
      files: []
    }
  end

  defp journal_preset(:icml) do
    %{
      article: "article",
      layout: "",
      usepackage: "\\usepackage[accepted]{icml2025}",
      title: &"\\twocolumn[\n\\icmltitle{#{&1}}",
      author: &"\\begin{icmlauthorlist}\n\\icmlauthor{#{&1}}{aff}\n\\end{icmlauthorlist}",
      affiliation: &"\\icmlaffiliation{aff}{#{&1}}\n",
      abstract: &"]\n\\printAffiliationsAndNotice{}\n\\begin{abstract}\n#{&1}\n\\end{abstract}",
      keywords: &"\\icmlkeywords{#{&1}}",
      bibliography_style: "\\bibliographystyle{icml2025}",
      files: ["icml2025.sty", "icml2025.bst", "fancyhdr.sty"]
    }
  end

  defp journal_preset(:jhep) do
    %{
      article: "article",
      layout: "",
      usepackage: "\\usepackage{jcappub}",
      title: &"\\title{#{&1}}",
      author: &"\\author{#{&1}}",
      affiliation: &"\\affiliation{#{&1}}",
      abstract: &"\\abstract{\n#{&1}\n}\n\\maketitle",
      keywords: fn _ -> "" end,
      bibliography_style: "\\bibliographystyle{JHEP}",
      files: ["JHEP.bst", "jcappub.sty"]
    }
  end

  defp journal_preset(:neurips) do
    %{
      article: "article",
      layout: "",
      usepackage: "\\usepackage[final]{neurips_2025}",
      title: &"\\title{#{&1}}",
      author: &"\\author{\n#{&1}\\\\",
      affiliation: &"#{&1}\n}",
      abstract: &"\\maketitle\n\\begin{abstract}\n#{&1}\n\\end{abstract}",
      keywords: fn _ -> "" end,
      bibliography_style: "\\bibliographystyle{unsrt}",
      files: ["neurips_2025.sty"]
    }
  end

  defp journal_preset(:pasj) do
    %{
      article: "pasj01",
      layout: "twocolumn",
      usepackage: "\\usepackage{aas_macros}",
      title: &"\\title{#{&1}}",
      author: &"\\author{#{&1}}",
      affiliation: &"\\altaffiltext{1}{#{&1}}",
      abstract: &"\\maketitle\n\\begin{abstract}\n#{&1}\n\\end{abstract}",
      keywords: fn _ -> "" end,
      bibliography_style: "\\bibliographystyle{aasjournal}",
      files: ["aasjournal.bst", "pasj01.cls", "aas_macros.sty"]
    }
  end

  defp journal_preset(:none) do
    %{
      article: "article",
      layout: "",
      usepackage: "",
      title: &"\\title{#{&1}}",
      author: &"\\author{#{&1}}",
      affiliation: &"\\date{#{&1}}",
      abstract: &"\\maketitle\n\\begin{abstract}\n#{&1}\n\\end{abstract}",
      keywords: fn _ -> "" end,
      bibliography_style: "\\bibliographystyle{unsrt}",
      files: []
    }
  end

  defp escape_bib(text) do
    text
    |> String.replace("\\", "\\\\")
    |> String.replace("{", "\\{")
    |> String.replace("}", "\\}")
    |> String.replace("&", "\\&")
    |> String.replace("%", "\\%")
    |> String.replace("_", "\\_")
  end
end
