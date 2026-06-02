defmodule DenarioEx.PromptTemplates do
  @moduledoc false

  @spec idea_maker_prompt(String.t(), String.t(), String.t(), non_neg_integer()) :: String.t()
  def idea_maker_prompt(data_description, previous_ideas, criticism, iteration) do
    """
    Your goal is to generate a groundbreaking idea for a scientific paper. Generate a original idea given the data description. If available, take into account the criticism provided by another agent about the idea. Please stick to the guidelines mentioned in the data description.

    Iteration #{iteration}

    Data description:
    #{data_description}

    Previous ideas:
    #{previous_ideas}

    Critisms:
    #{criticism}

    Respond in the following format:

    \\begin{IDEA}
    <IDEA>
    \\end{IDEA}

    In <IDEA>, put the idea together with its description. Try to be brief in the description. Do not explain how you have addressed any criticism.
    """
  end

  @spec idea_hater_prompt(String.t(), String.t(), String.t()) :: String.t()
  def idea_hater_prompt(data_description, previous_ideas, current_idea) do
    """
    Your goal is to critic an idea. You will be provided with the idea together with the initial data description used to make the idea. Be a harsh critic of the idea. Take into account feasibility, impact and any other factor you think. The goal of your criticisms is to improve the idea. If the idea is not feasible, suggest to generate a new idea. When providing your feedback, take into account the guidelines in the data description. For instance, if a detailed idea is provided there, try to stick with it.

    Data description:
    #{data_description}

    Previous ideas:
    #{previous_ideas}

    Current idea:
    #{current_idea}

    Respond in the following format:

    \\begin{CRITIC}
    <CRITIC>
    \\end{CRITIC}

    In <CRITIC>, put your criticism to the idea. Try to be brief in the description.
    """
  end

  @spec methods_fast_prompt(String.t(), String.t()) :: String.t()
  def methods_fast_prompt(data_description, idea) do
    """
    You are provided with a data description and an idea for a scientific paper. Your task is to think about the methods to use in order to carry it out.

    Follow these instructions:
    - generate a detailed description of the methodology that will be used to perform the research project.
    - The description should clearly outline the steps, techniques, and rationale derived from the exploratory data analysis (EDA).
    - The focus should be strictly on the methods and workflow for this specific project to be performed. do not include any discussion of future directions, future work, project extensions, or limitations.
    - The description should be written as if it were a senior researcher explaining to her research assistant how to perform the research necessary for this project.
    - Just provide the methods, do not add a sentence at the beginning saying showing your thinking process.

    Data description:
    #{data_description}

    Idea:
    #{idea}

    Respond in this format:

    \\begin{METHODS}
    <METHODS>
    \\end{METHODS}

    In <METHODS> put the methods you have generated.
    """
  end
end
