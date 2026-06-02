defmodule DenarioEx.PythonExecutor do
  @moduledoc """
  Executes generated Python scripts inside a workflow workspace.
  """

  @behaviour DenarioEx.CodeExecutor

  @impl true
  def execute(code, opts) do
    work_dir = Keyword.fetch!(opts, :work_dir)
    step_id = Keyword.get(opts, :step_id, "step")
    attempt = Keyword.get(opts, :attempt, 1)
    python_command = Keyword.get(opts, :python_command, default_python_command())
    script_name = "#{step_id}_attempt_#{attempt}.py"
    script_path = Path.join(work_dir, script_name)

    File.mkdir_p!(work_dir)
    File.write!(script_path, code)

    try do
      case System.cmd(python_command, [script_path], cd: work_dir, stderr_to_stdout: true) do
        {output, 0} ->
          {:ok,
           %{
             "status" => 0,
             "output" => output,
             "script_path" => script_path,
             "generated_files" => collect_generated_files(work_dir)
           }}

        {output, status} ->
          {:error,
           %{
             "status" => status,
             "output" => output,
             "script_path" => script_path
           }}
      end
    rescue
      error ->
        {:error,
         %{
           "status" => 127,
           "output" => Exception.message(error),
           "script_path" => script_path
         }}
    end
  end

  defp default_python_command do
    repo_python = Path.expand("../../../../.venv/bin/python", __DIR__)

    cond do
      File.exists?(repo_python) -> repo_python
      System.find_executable("python3") -> "python3"
      true -> "python"
    end
  end

  defp collect_generated_files(work_dir) do
    extensions = ["png", "jpg", "jpeg", "pdf", "svg"]

    extensions
    |> Enum.flat_map(fn ext -> Path.wildcard(Path.join(work_dir, "**/*.#{ext}")) end)
    |> Enum.uniq()
  end
end
