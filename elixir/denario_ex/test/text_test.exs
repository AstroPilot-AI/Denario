defmodule DenarioEx.TextTest do
  use ExUnit.Case, async: true

  alias DenarioEx.Text

  test "extract_block_or_fallback returns wrapped content when block markers exist" do
    assert {:ok, "hello"} =
             Text.extract_block_or_fallback("\\begin{SUMMARY}hello\\end{SUMMARY}", "SUMMARY")
  end

  test "extract_block_or_fallback returns cleaned raw text when block markers are missing" do
    assert {:ok, "plain summary text"} =
             Text.extract_block_or_fallback("plain summary text", "SUMMARY")
  end
end
