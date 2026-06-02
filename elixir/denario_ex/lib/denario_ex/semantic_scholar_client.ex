defmodule DenarioEx.SemanticScholarClient do
  @moduledoc """
  Behaviour for Semantic Scholar search adapters.
  """

  alias DenarioEx.KeyManager

  @callback search(String.t(), KeyManager.t(), keyword()) :: {:ok, map()} | {:error, term()}
end
