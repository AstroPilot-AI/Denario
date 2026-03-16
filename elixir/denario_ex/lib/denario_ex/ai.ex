defmodule DenarioEx.AI do
  @moduledoc false

  alias DenarioEx.{KeyManager, LLM}

  @spec complete(module(), String.t(), LLM.t(), KeyManager.t()) ::
          {:ok, String.t()} | {:error, term()}
  def complete(client, prompt, %LLM{} = llm, %KeyManager{} = keys) do
    messages = [%{role: "user", content: prompt}]

    client.complete(messages,
      api_key: KeyManager.api_key_for_provider(keys, llm.provider),
      model: llm.spec,
      model_metadata: llm.model,
      temperature: llm.temperature,
      max_output_tokens: llm.max_output_tokens
    )
  end

  @spec generate_object(module(), String.t(), map(), LLM.t(), KeyManager.t()) ::
          {:ok, map()} | {:error, term()}
  def generate_object(client, prompt, schema, %LLM{} = llm, %KeyManager{} = keys) do
    messages = [%{role: "user", content: prompt}]

    client.generate_object(messages, schema,
      api_key: KeyManager.api_key_for_provider(keys, llm.provider),
      model: llm.spec,
      model_metadata: llm.model,
      temperature: llm.temperature,
      max_output_tokens: llm.max_output_tokens
    )
  end
end
