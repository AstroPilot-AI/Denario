defmodule DenarioEx.CodeExecutor do
  @moduledoc """
  Behaviour for executing generated analysis code.
  """

  @callback execute(String.t(), keyword()) :: {:ok, map()} | {:error, map()}
end
