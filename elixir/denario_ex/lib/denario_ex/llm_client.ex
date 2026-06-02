defmodule DenarioEx.LLMClient do
  @moduledoc """
  Behaviour for pluggable LLM clients.
  """

  @callback complete([map()], keyword()) :: {:ok, String.t()} | {:error, term()}
  @callback generate_object([map()], map(), keyword()) :: {:ok, map()} | {:error, term()}
end
