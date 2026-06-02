defmodule DenarioEx.ReqLLMClient do
  @moduledoc """
  ReqLLM-backed client adapter for Denario text generation.
  """

  @behaviour DenarioEx.LLMClient

  alias ReqLLM.Response
  alias ReqLLM.ToolCall

  @impl true
  def complete(messages, opts) do
    model = Keyword.get(opts, :model_metadata, Keyword.fetch!(opts, :model))

    case ReqLLM.generate_text(model, messages, build_generation_opts(opts)) do
      {:ok, response} ->
        case Response.text(response) do
          text when is_binary(text) and text != "" -> {:ok, text}
          _ -> {:error, {:empty_response, response}}
        end

      {:error, error} ->
        {:error, error}
    end
  end

  @impl true
  def generate_object(messages, schema, opts) do
    model = Keyword.get(opts, :model_metadata, Keyword.fetch!(opts, :model))

    case ReqLLM.generate_object(model, messages, schema, build_generation_opts(opts)) do
      {:ok, response} ->
        case extract_object_from_response(response) do
          {:ok, object} when is_map(object) -> {:ok, object}
          {:ok, _other} -> {:error, {:non_map_object_response, response}}
          {:error, error} -> {:error, {:empty_object_response, error, response}}
        end

      {:error, error} ->
        {:error, error}
    end
  end

  @doc false
  def build_generation_opts(opts) do
    output_key = if openai_model?(opts), do: :max_completion_tokens, else: :max_tokens

    opts
    |> Keyword.take([:api_key, :temperature, :provider_options])
    |> Keyword.put(output_key, Keyword.fetch!(opts, :max_output_tokens))
    |> maybe_put_openai_json_schema(opts)
  end

  @doc false
  def extract_object_from_response(response) do
    case Response.unwrap_object(response) do
      {:ok, object} ->
        {:ok, object}

      {:error, _reason} ->
        response
        |> Response.tool_calls()
        |> Enum.find_value(fn
          %ToolCall{} = tool_call ->
            case ToolCall.to_map(tool_call) do
              %{name: "structured_output", arguments: arguments} when is_map(arguments) ->
                {:ok, arguments}

              _other ->
                nil
            end

          %{name: "structured_output", arguments: arguments} when is_map(arguments) ->
            {:ok, arguments}

          %{"name" => "structured_output", "arguments" => arguments} when is_map(arguments) ->
            {:ok, arguments}

          _other ->
            nil
        end)
        |> case do
          nil -> {:error, :no_structured_output_tool_call}
          result -> result
        end
    end
  end

  defp maybe_put_openai_json_schema(generation_opts, opts) do
    if openai_model?(opts) do
      Keyword.put(generation_opts, :provider_options, openai_provider_options(generation_opts))
    else
      generation_opts
    end
  end

  defp openai_provider_options(generation_opts) do
    generation_opts
    |> Keyword.get(:provider_options, [])
    |> Keyword.put(:openai_structured_output_mode, :json_schema)
  end

  defp openai_model?(opts) do
    case Keyword.get(opts, :model_metadata) do
      %{provider: :openai} ->
        true

      _ ->
        case Keyword.get(opts, :model) do
          "openai:" <> _rest -> true
          _ -> false
        end
    end
  end
end
