defmodule DenarioEx.ReqLLMClientTest do
  use ExUnit.Case, async: true

  import ExUnit.CaptureLog

  alias DenarioEx.ReqLLMClient
  alias ReqLLM.Message
  alias ReqLLM.Provider.Options
  alias ReqLLM.Providers.OpenAI
  alias ReqLLM.Response
  alias ReqLLM.ToolCall

  test "extract_object_from_response returns structured output from ReqLLM tool calls" do
    response = %Response{
      id: "resp_test",
      model: "gpt-4.1-mini-2025-04-14",
      context: %ReqLLM.Context{messages: []},
      message: %Message{
        role: :assistant,
        content: [],
        tool_calls: [
          ToolCall.new("call_test", "structured_output", ~s({"approved":true,"feedback":"ok"}))
        ],
        metadata: %{}
      },
      object: nil,
      stream?: false,
      stream: nil,
      usage: nil,
      finish_reason: :tool_calls,
      provider_meta: %{},
      error: nil
    }

    assert {:ok, %{"approved" => true, "feedback" => "ok"}} =
             ReqLLMClient.extract_object_from_response(response)
  end

  test "build_generation_opts uses max_completion_tokens for openai models" do
    opts =
      ReqLLMClient.build_generation_opts(
        model: "openai:gpt-4.1-mini",
        max_output_tokens: 321,
        temperature: 0.2
      )

    assert opts[:max_completion_tokens] == 321
    refute Keyword.has_key?(opts, :max_tokens)
    assert opts[:provider_options][:openai_structured_output_mode] == :json_schema
  end

  test "build_generation_opts keeps max_tokens for non-openai models" do
    opts =
      ReqLLMClient.build_generation_opts(
        model: "anthropic:claude-sonnet-4-5",
        max_output_tokens: 321,
        temperature: 0.2
      )

    assert opts[:max_tokens] == 321
    refute Keyword.has_key?(opts, :max_completion_tokens)
  end

  test "options processing does not synthesize max_tokens when max_completion_tokens is present" do
    {:ok, model} = ReqLLM.model("openai:gpt-4.1-mini")

    log =
      capture_log(fn ->
        assert {:ok, processed} =
                 Options.process(OpenAI, :object, model,
                   max_completion_tokens: 123,
                   operation: :object
                 )

        assert processed[:max_completion_tokens] == 123
        refute Keyword.has_key?(processed, :max_tokens)
      end)

    refute log =~ "Renamed :max_tokens to :max_completion_tokens"
  end
end
