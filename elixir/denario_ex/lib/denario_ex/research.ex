defmodule DenarioEx.Research do
  @moduledoc """
  Research state persisted inside a Denario session.
  """

  @enforce_keys []
  defstruct data_description: "",
            idea: "",
            methodology: "",
            results: "",
            literature: "",
            plot_paths: [],
            keywords: %{},
            literature_sources: [],
            paper_tex_path: nil,
            paper_pdf_path: nil

  @type t :: %__MODULE__{
          data_description: String.t(),
          idea: String.t(),
          methodology: String.t(),
          results: String.t(),
          literature: String.t(),
          plot_paths: [String.t()],
          keywords: map() | list(),
          literature_sources: [map()],
          paper_tex_path: String.t() | nil,
          paper_pdf_path: String.t() | nil
        }
end
