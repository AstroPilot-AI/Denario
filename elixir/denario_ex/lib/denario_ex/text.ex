defmodule DenarioEx.Text do
  @moduledoc false

  @spec extract_block(String.t(), String.t()) :: {:ok, String.t()} | {:error, term()}
  def extract_block(text, block) when is_binary(text) and is_binary(block) do
    regex =
      Regex.compile!(
        "\\\\begin\\{#{Regex.escape(block)}\\}(.*?)\\\\end\\{#{Regex.escape(block)}\\}",
        [:dotall]
      )

    case Regex.run(regex, text, capture: :all_but_first) do
      [content] -> {:ok, String.trim(content)}
      _ -> {:error, {:missing_block, block}}
    end
  end

  @spec extract_block_or_fallback(String.t(), String.t()) :: {:ok, String.t()} | {:error, term()}
  def extract_block_or_fallback(text, block) when is_binary(text) and is_binary(block) do
    case extract_block(text, block) do
      {:ok, content} ->
        {:ok, clean_section(content, block)}

      {:error, {:missing_block, ^block}} ->
        cleaned = clean_section(text, block)

        if cleaned == "" do
          {:error, {:missing_block, block}}
        else
          {:ok, cleaned}
        end

      {:error, error} ->
        {:error, error}
    end
  end

  @spec clean_section(String.t(), String.t()) :: String.t()
  def clean_section(text, section) do
    [
      "\\documentclass{article}",
      "\\begin{document}",
      "\\end{document}",
      "\\section{#{section}}",
      "\\section*{#{section}}",
      "\\begin{#{section}}",
      "\\end{#{section}}",
      "\\maketitle",
      "<PARAGRAPH>",
      "</PARAGRAPH>",
      "</{section}>",
      "<{section}>",
      "```latex",
      "```",
      "\\usepackage{amsmath}"
    ]
    |> Enum.reduce(text, &String.replace(&2, &1, ""))
    |> String.trim()
  end

  @spec slugify(String.t()) :: String.t()
  def slugify(text) do
    text
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9]+/u, "_")
    |> String.trim("_")
    |> case do
      "" -> "item"
      slug -> slug
    end
  end

  @spec fetch(map(), String.t()) :: term()
  def fetch(map, key) when is_map(map) and is_binary(key) do
    Map.get(map, key) || Map.get(map, String.to_atom(key))
  end
end
