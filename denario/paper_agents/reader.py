import os
import time
import hashlib
import shutil
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .parameters import GraphState
from .latex_presets import journal_dict
from ..config import INPUT_FILES, IDEA_FILE, METHOD_FILE, RESULTS_FILE, PAPER_FOLDER, PLOTS_FOLDER, LaTeX_DIR
from ..llm import models


def preprocess_node(state: GraphState, config: RunnableConfig):
    """
    This agent reads the input files, clean up files, and set the name of some files
    """

    # set the LLM
    if state["keys"].OPENROUTER:
        model_name = state['llm']['model']
        openrouter_model = model_name
        if model_name in models:
             if models[model_name].openrouter_name:
                 openrouter_model = models[model_name].openrouter_name
        
        state['llm']['llm'] = ChatOpenAI(model=openrouter_model,
                                         temperature=state['llm']['temperature'],
                                         openai_api_key=state["keys"].OPENROUTER,
                                         base_url="https://openrouter.ai/api/v1")

    elif 'gemini' in state['llm']['model']:
        state['llm']['llm'] = ChatGoogleGenerativeAI(model=state['llm']['model'],
                                                temperature=state['llm']['temperature'],
                                                google_api_key=state["keys"].GEMINI)

    elif any(key in state['llm']['model'] for key in ['gpt', 'o3']):
        state['llm']['llm'] = ChatOpenAI(model=state['llm']['model'],
                                         temperature=state['llm']['temperature'],
                                         openai_api_key=state["keys"].OPENAI)
                    
    elif 'claude' in state['llm']['model']  or 'anthropic' in state['llm']['model'] :
        state['llm']['llm'] = ChatAnthropic(model=state['llm']['model'],
                                            temperature=state['llm']['temperature'],
                                            anthropic_api_key=state["keys"].ANTHROPIC)
    
    # set the tokens usage
    state['tokens'] = {'ti': 0, 'to': 0, 'i': 0, 'o': 0}

    # set time
    state['time'] = {'start': time.time()}

    # set value of the parameters
    state['params'] = {'num_keywords': 5}
    
    # get Paper folder
    state['files'] = {**state['files'],
                      "Paper_folder": f"{state['files']['Folder']}/{PAPER_FOLDER}"}
    os.makedirs(state['files']['Paper_folder'], exist_ok=True)

    # set the name of the other files
    state['files'] = {**state['files'],
                      "Idea":      f"{IDEA_FILE}",    #name of file containing idea description
                      "Methods":   f"{METHOD_FILE}",  #name of file with methods description
                      "Results":   f"{RESULTS_FILE}", #name of file with results description
                      "Plots":     f"{PLOTS_FOLDER}", #name of folder containing plots
                      "Paper_v1":  "paper_v1_preliminary.tex",
                      "Paper_v2":  "paper_v2_no_citations.tex",
                      "Paper_v3":  "paper_v3_citations.tex",
                      "Paper_v4":  "paper_v4_final.tex",
                      "Error":     f"{state['files']['Paper_folder']}/Error.txt",
                      "LaTeX_log": f"{state['files']['Paper_folder']}/LaTeX_compilation.log",
                      "LaTeX_err": f"{state['files']['Paper_folder']}/LaTeX_err.log",                  
                      "Temp":      f"{state['files']['Paper_folder']}/temp",
                      "LLM_calls": f"{state['files']['Paper_folder']}/LLM_calls.txt",
                      "AAS_keywords": str( LaTeX_DIR / "AAS_keywords.txt" )}

    # set the Latex class
    state['latex'] = {'section': ''}
    
    # read input files
    idea = {}
    for key in ["Idea", "Methods", "Results"]:
        path = Path(f"{state['files']['Folder']}/{INPUT_FILES}/{state['files'][key]}")
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                idea[key] = f.read()
        else:
            idea[key] = None

    # remove these files if they already exist
    for f in ['Paper_v1', 'Paper_v2', 'Paper_v3', 'Paper_v4']:
        f_in = f"{state['files']['Paper_folder']}/{state['files'][f]}"
        if os.path.exists(f_in):
            os.remove(f"{f_in}")

        # get the root of the paper file (if paper.tex, root=paper)
        root = Path(state['files'][f]).stem
        
        for f_in in [f'{root}.pdf', f'{root}.aux', f'{root}.log', f'{root}.out',
                     f'{root}.bbl', f'{root}.blg', f'{root}.synctex.gz',
                     f'{root}.synctex(busy)', 'bibliography.bib',
                     'bibliography_temp.bib',]:
            fin = f"{state['files']['Paper_folder']}/{f_in}"
            if os.path.exists(fin):
                os.remove(f"{fin}")

    # remove these files if they already exist
    for f_in in [state['files']['Error'], state['files']['LLM_calls'],
                 state['files']['LaTeX_log'], state['files']['LaTeX_err']]:
        if os.path.exists(f_in):
            os.remove(f"{f_in}")

    # create a folder to save LaTeX progress
    os.makedirs(state['files']['Temp'], exist_ok=True)

    # create symbolic link to input_files in Temp to compile files in Temp
    link_src = Path(f"{state['files']['Folder']}/{INPUT_FILES}").resolve()
    link_dst = Path(f"{state['files']['Paper_folder']}/{INPUT_FILES}").resolve()
    # Only create symlink if it doesn't already exist
    if not link_dst.exists() and not link_dst.is_symlink():
        link_dst.symlink_to(link_src, target_is_directory=True)
    
    # copy LaTeX files to project folder
    journal_files = journal_dict[state["paper"]["journal"]].files

    # copy LaTeX journal files to project folder
    for f in journal_files:
        f_in = f"{state['files']['Paper_folder']}/{f}"
        if not(os.path.exists(f_in)):
            os.system(f"cp {LaTeX_DIR}/{f} {state['files']['Paper_folder']}")
        f_in = f"{state['files']['Temp']}/{f}"
        if not(os.path.exists(f_in)):
            os.system(f"cp {LaTeX_DIR}/{f} {state['files']['Temp']}")

    # deal with repeated plots
    plots_dir    = Path(f"{state['files']['Folder']}/{INPUT_FILES}/{state['files']['Plots']}")
    repeated_dir = Path(f"{plots_dir}_repeated")

    # Walk through all plot files
    hash_dict = {}  # create hash dictionary
    for file in plots_dir.iterdir():
        if file.is_file():

            # Compute hash
            with open(file, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
    
            if file_hash in hash_dict:
                repeated_dir.mkdir(exist_ok=True)
                # This is a repeated file: copy it to repeated_plots
                print(f"Repeated: {file.name} (same as {hash_dict[file_hash].name})")
                shutil.move(file, repeated_dir / file.name)
            else:
                hash_dict[file_hash] = file

    # get the number of plots in the project
    folder_path = Path(f"{state['files']['Folder']}/{INPUT_FILES}/{state['files']['Plots']}")
    files = [f for f in folder_path.iterdir()
         if f.is_file() and f.name != '.DS_Store']
    state['files']['num_plots'] = len(files)

    return {**state,
            "llm": state['llm'],
            "tokens": state['tokens'],
            "params": state['params'],
            "files": state['files'],
            "latex": state['latex'],
            "idea": idea,
            "paper": {**state['paper'], "summary": ""},
            "time": state['time'],
    }

