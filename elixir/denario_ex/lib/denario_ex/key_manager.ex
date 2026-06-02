defmodule DenarioEx.KeyManager do
  @moduledoc """
  Loads provider credentials from the environment.
  """

  @enforce_keys []
  defstruct anthropic: nil,
            gemini: nil,
            openai: nil,
            perplexity: nil,
            semantic_scholar: nil

  @type t :: %__MODULE__{
          anthropic: String.t() | nil,
          gemini: String.t() | nil,
          openai: String.t() | nil,
          perplexity: String.t() | nil,
          semantic_scholar: String.t() | nil
        }

  @spec from_env() :: t()
  def from_env do
    %__MODULE__{
      openai: first_env(["OPENAI_API_KEY"]),
      gemini: first_env(["GOOGLE_API_KEY", "GEMINI_API_KEY"]),
      anthropic: first_env(["ANTHROPIC_API_KEY"]),
      perplexity: first_env(["PERPLEXITY_API_KEY"]),
      semantic_scholar:
        first_env(["SEMANTIC_SCHOLAR_KEY", "SEMANTIC_SCHOLAR_API_KEY", "S2_API_KEY"])
    }
  end

  @spec api_key_for_provider(t(), atom()) :: String.t() | nil
  def api_key_for_provider(%__MODULE__{} = keys, provider) do
    case provider do
      :openai -> keys.openai
      :anthropic -> keys.anthropic
      :google -> keys.gemini
      :google_vertex -> keys.gemini
      :gemini -> keys.gemini
      :perplexity -> keys.perplexity
      _ -> nil
    end
  end

  defp first_env(names) do
    Enum.find_value(names, fn name ->
      case System.get_env(name) do
        value when is_binary(value) and value != "" -> value
        _ -> nil
      end
    end)
  end
end
