defmodule DenarioEx.KeyManagerTest do
  use ExUnit.Case, async: false

  alias DenarioEx.KeyManager

  setup do
    original =
      for name <- [
            "OPENAI_API_KEY",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY",
            "PERPLEXITY_API_KEY",
            "SEMANTIC_SCHOLAR_KEY",
            "SEMANTIC_SCHOLAR_API_KEY",
            "S2_API_KEY"
          ],
          into: %{} do
        {name, System.get_env(name)}
      end

    on_exit(fn ->
      Enum.each(original, fn
        {name, nil} -> System.delete_env(name)
        {name, value} -> System.put_env(name, value)
      end)
    end)

    Enum.each(Map.keys(original), &System.delete_env/1)
    :ok
  end

  test "from_env reads common provider env vars and semantic scholar aliases" do
    System.put_env("OPENAI_API_KEY", "openai-key")
    System.put_env("GEMINI_API_KEY", "gemini-key")
    System.put_env("SEMANTIC_SCHOLAR_API_KEY", "s2-key")

    keys = KeyManager.from_env()

    assert keys.openai == "openai-key"
    assert keys.gemini == "gemini-key"
    assert keys.semantic_scholar == "s2-key"
  end

  test "from_env prefers SEMANTIC_SCHOLAR_KEY over fallback aliases" do
    System.put_env("SEMANTIC_SCHOLAR_KEY", "primary-key")
    System.put_env("SEMANTIC_SCHOLAR_API_KEY", "secondary-key")
    System.put_env("S2_API_KEY", "tertiary-key")

    keys = KeyManager.from_env()

    assert keys.semantic_scholar == "primary-key"
  end
end
