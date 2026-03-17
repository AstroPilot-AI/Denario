from typing_extensions import TypedDict, Any
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from .journal import Journal
from ..key_manager import KeyManager

# Paper class
class PAPER(TypedDict):
    Title: str
    Abstract: str
    Keywords: str
    Introduction: str
    Methods: str
    Results: str
    Conclusions: str
    References: str
    summary: str
    journal: Journal
    add_citations: bool
    cmbagent_keywords: bool

# Class for Input/Output files
class FILES(TypedDict):
    Folder: str       #name of the project file
    ResearcherStatement: str #name of the file containing the user's research framing
    Idea: str         #name of the file containing the project idea
    Methods: str      #name of the file containing the methods 
    Results: str      #name of the file containing the results
    Plots: str        #name of the folder containing the plots
    Paper_v1: str     #name of the file containing the version 1 of the paper 
    Paper_v2: str     #name of the file containing the version 2 of the paper 
    Paper_v3: str     #name of the file containing the version 3 of the paper
    Paper_v4: str     #name of the file containing the version 4 of the paper
    Error: str        #name of the error file
    LaTeX_log: str    #name of the file with the LaTeX log (when compiling it)
    LaTeX_err: str    #name of the file with just the LaTeX errors
    Temp: str         #name of the folder with the temporary LaTeX files
    LLM_calls: str    #name of the file with the calls to the LLM
    Paper_folder: str #name of the folder containing all paper files
    AAS_keywords: str #name of the file with the AAS keywords
    num_plots: int    #number of plots

# Idea class
class IDEA(TypedDict):
    ResearcherStatement: str | None
    Idea: str
    Methods: str
    Results: str

# Token class
class TOKENS(TypedDict):
    ti: int #total input tokens
    to: int #total output tokens 
    i:  int #input tokens (just for individual calls or functions)
    o:  int #output tokens (just for individual calls or functions)

# LaTeX class
class LATEX(TypedDict):
    section_to_fix: str
    
# LLM class
class LLM(TypedDict):
    model: str
    max_output_tokens: int
    llm: Any
    temperature: float

# TIME class
class TIME(TypedDict):
    start: float

# parameters class
class PARAMS(TypedDict):
    num_keywords: int
    
    
# Graph state class
class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    files: FILES
    idea: IDEA
    paper: PAPER
    tokens: TOKENS
    llm: LLM
    latex: LATEX
    keys: KeyManager
    time: TIME
    writer: str  #determines who is writing the paper. E.g. astrophysicists, biologist
    params: PARAMS #parameters of model
