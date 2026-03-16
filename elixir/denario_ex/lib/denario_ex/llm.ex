defmodule DenarioEx.LLM do
  @moduledoc """
  Normalizes Denario model inputs through LLMDB/ReqLLM.
  """

  @default_max_output_tokens 16_384

  @default_specs %{
    "gemini-2.0-flash" => {"google:gemini-2.0-flash", 0.7},
    "gemini-2.5-flash" => {"google:gemini-2.5-flash", 0.7},
    "gemini-2.5-pro" => {"google:gemini-2.5-pro", 0.7},
    "o3-mini" => {"openai:o3-mini", nil},
    "gpt-4o" => {"openai:gpt-4o", 0.5},
    "gpt-4.1" => {"openai:gpt-4.1", 0.5},
    "gpt-4.1-mini" => {"openai:gpt-4.1-mini", 0.5},
    "gpt-4o-mini" => {"openai:gpt-4o-mini", 0.5},
    "gpt-4.5" => {"openai:gpt-4.5-preview", 0.5},
    "gpt-5" => {"openai:gpt-5", nil},
    "gpt-5-mini" => {"openai:gpt-5-mini", nil}
  }

  @enforce_keys [:spec, :model, :provider, :max_output_tokens]
  defstruct [:spec, :model, :provider, :max_output_tokens, :temperature]

  @type t :: %__MODULE__{
          spec: String.t(),
          model: LLMDB.Model.t(),
          provider: atom(),
          max_output_tokens: pos_integer(),
          temperature: float() | nil
        }

  @spec parse(String.t() | t()) :: {:ok, t()}
  def parse(%__MODULE__{} = llm), do: {:ok, llm}

  def parse(name) when is_binary(name) do
    {spec, temperature} = normalize_spec(name)

    with {:ok, model} <- resolve_model(spec) do
      {:ok,
       %__MODULE__{
         spec: spec,
         model: model,
         provider: model.provider,
         max_output_tokens: max_output_tokens(model),
         temperature: temperature
       }}
    end
  end

  defp normalize_spec(name) do
    case Map.get(@default_specs, name) do
      {spec, temperature} ->
        {spec, temperature}

      nil ->
        spec =
          if String.contains?(name, [":", "@"]) do
            name
          else
            "openai:#{name}"
          end

        {provider, model_id} = LLMDB.parse!(spec)
        {LLMDB.format({provider, model_id}), default_temperature(provider, model_id)}
    end
  end

  defp resolve_model(spec) do
    case LLMDB.model(spec) do
      {:ok, model} ->
        {:ok, model}

      {:error, _reason} ->
        {provider, model_id} = LLMDB.parse!(spec)
        ReqLLM.model(%{provider: provider, id: model_id})
    end
  end

  defp max_output_tokens(%LLMDB.Model{limits: limits}) do
    case limits do
      %{output: output} when is_integer(output) and output > 0 -> output
      %{"output" => output} when is_integer(output) and output > 0 -> output
      _ -> @default_max_output_tokens
    end
  end

  defp default_temperature(provider, _model_id) when provider in [:google, :google_vertex],
    do: 0.7

  defp default_temperature(:openai, model_id) do
    if reasoning_model?(model_id), do: nil, else: 0.5
  end

  defp default_temperature(_provider, _model_id), do: 0.5

  defp reasoning_model?(model_id) do
    String.starts_with?(model_id, ["gpt-5", "o1", "o3", "o4"])
  end
end
