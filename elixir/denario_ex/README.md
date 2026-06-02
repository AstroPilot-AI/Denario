# DenarioEx

Elixir port of the Denario workflow.

Implemented:

- project/session lifecycle
- `input_files` persistence
- provider key loading
- `LLMDB` model resolution
- `ReqLLM`-backed fast idea and method generation
- `cmbagent`-style planning/control loop for idea and method generation
- `get_results/2` with code generation, execution, retries, and plot harvesting
- literature checking via Semantic Scholar with OpenAlex fallback
- paper generation to LaTeX with optional bibliography and compile step

## Setup

```bash
cd elixir/denario_ex
mix deps.get
mix test
```

## Temporary `req_llm` pin

`DenarioEx` is temporarily pinned to a Git commit of `req_llm` instead of the Hex release.

- Current pin: `jmanhype/req_llm@ee00b4553cd6823b48c1045b825565855a77a93b`
- Upstream PR: <https://github.com/agentjido/req_llm/pull/506>

Why this exists:

- `req_llm` `1.7.1` still injects `:max_tokens` for some OpenAI reasoning/object requests
- that triggers noisy `Renamed :max_tokens to :max_completion_tokens` warnings
- the pinned commit removes that library-side warning path

When the upstream PR is merged and a new Hex release includes the fix, switch
`mix.exs` back to the published `{:req_llm, "~> ..."}` dependency and refresh `mix.lock`.

## Credentials

The Elixir port reads these environment variables:

- OpenAI: `OPENAI_API_KEY`
- Gemini: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Perplexity: `PERPLEXITY_API_KEY`
- Semantic Scholar: `SEMANTIC_SCHOLAR_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, or `S2_API_KEY`

For citation-backed literature checking, export a Semantic Scholar key before running:

```bash
export OPENAI_API_KEY=...
export SEMANTIC_SCHOLAR_API_KEY=...
```

Without a Semantic Scholar key, `check_idea/2` first falls back to OpenAlex. It only degrades to
`Idea literature search unavailable` if both providers fail.

## Minimal usage

```elixir
alias DenarioEx

{:ok, denario} =
  DenarioEx.new(project_dir: "/tmp/denario_elixir_demo", clear_project_dir: true)

{:ok, denario} =
  DenarioEx.set_data_description(
    denario,
    """
    Analyze a small hypothetical lab sensor dataset and propose one simple paper idea.
    """
  )

{:ok, denario} = DenarioEx.get_idea_fast(denario, llm: "openai:gpt-4.1-mini")
{:ok, denario} = DenarioEx.get_method_fast(denario, llm: "openai:gpt-4.1-mini")
```

## Full workflow

```elixir
alias DenarioEx

{:ok, denario} =
  DenarioEx.new(project_dir: "/tmp/denario_ex_full", clear_project_dir: true)

{:ok, denario} =
  DenarioEx.set_data_description(
    denario,
    "Generate a tiny synthetic anomaly-score dataset, summarize it, and write a short paper."
  )

{:ok, denario} = DenarioEx.get_idea(denario, mode: :cmbagent, planner_model: "openai:gpt-4.1-mini")
{:ok, denario} = DenarioEx.get_method(denario, mode: :cmbagent, planner_model: "openai:gpt-4.1-mini")
{:ok, denario} = DenarioEx.get_results(denario, planner_model: "openai:gpt-4.1-mini", engineer_model: "openai:gpt-4.1-mini")
{:ok, denario} = DenarioEx.check_idea(denario, llm: "openai:gpt-4.1-mini")
{:ok, denario} = DenarioEx.get_paper(denario, llm: "openai:gpt-4.1-mini", compile: false)
```
