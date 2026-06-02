defmodule DenarioEx.MixProject do
  use Mix.Project

  def project do
    [
      app: :denario_ex,
      version: "0.1.0",
      elixir: "~> 1.18",
      start_permanent: Mix.env() == :prod,
      description: "Initial Elixir port of the Denario research workflow using ReqLLM and LLMDB",
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger, :ssl, :inets],
      mod: {DenarioEx.Application, []}
    ]
  end

  defp deps do
    [
      {:req, "~> 0.5.17"},
      {:llm_db, "~> 2026.3"},
      {:req_llm,
       git: "https://github.com/jmanhype/req_llm.git",
       ref: "ee00b4553cd6823b48c1045b825565855a77a93b",
       override: true}
    ]
  end
end
