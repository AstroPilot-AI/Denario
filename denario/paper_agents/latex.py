import subprocess
import os
import re
import shutil
from pathlib import Path

from .parameters import GraphState
from .prompts import fix_latex_bug_prompt
from .tools import LLM_call, extract_latex_block, temp_file
from .journal import LatexPresets
from .latex_presets import journal_dict


# Characters that should be escaped in BibTeX (outside math mode)
special_chars = {
    "_": r"\_",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "$": r"\$",
    "{": r"\{",
    "}": r"\}",
    "~": r"\~{}",
    "^": r"\^{}",
}


def extract_latex_errors(state):
    """
    This function takes a LaTeX compilation file and extracts the compilation errors.
    """

    with open(state['files']['LaTeX_log'], 'r') as f:
        lines = f.readlines()

    errors = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("! "):  # Start of error
            error_block = [line]
            i += 1

            # Keep capturing lines until a new section or file is loaded
            while i < len(lines):
                next_line = lines[i].strip()

                if (
                    next_line.startswith("! ") or
                    next_line.startswith("(/") or
                    next_line.startswith(")") or
                    next_line.startswith("Package ") or
                    next_line.startswith("Document Class") or
                    next_line.startswith("(/usr") or
                    re.match(r'^\([^\)]+\.sty', next_line) or
                    re.match(r'^\(/', next_line) or
                    re.match(r'^.*\.tex$', next_line)  # new .tex file
                ):
                    break

                # Always include potentially helpful lines
                error_block.append(next_line)
                i += 1

            errors.append("\n".join(error_block))
        else:
            i += 1

    # Write the errors to the output file
    with open(state['files']['LaTeX_err'], 'w') as f:
        if errors:
            f.write("LaTeX Compilation Errors Found:\n\n")
            for error in errors:
                f.write(error + "\n\n")
        else:
            f.write("✅ No LaTeX errors found.\n")


def clean_files(doc_name, doc_folder):

    file_path = Path(doc_name)
    doc_stem = file_path.stem
    for suffix in ['aux', 'log', 'pdf', 'out']:
        if os.path.exists(f'{doc_folder}/{doc_stem}.{suffix}'):
            os.system(f'rm {doc_folder}/{doc_stem}.{suffix}')


def compile_tex_document(state: dict, doc_name: str, doc_folder: str) -> None:

    file_path = Path(doc_name)
    doc_name = file_path.name
    doc_stem = file_path.stem
    bib_path = os.path.join(state['files']['Temp'], "bibliography.bib")

    def get_latex_command(name, is_final=False):
        if shutil.which("xelatex"):
            cmd = ["xelatex"]
            if is_final:
                cmd.extend(["-interaction=nonstopmode", "-file-line-error"])
            cmd.append(name)
            return cmd, "xelatex"
        elif shutil.which("tectonic"):
            return ["tectonic", name], "tectonic"
        else:
            raise FileNotFoundError("Neither xelatex nor tectonic found in PATH.")

    def run_xelatex(pass_num=None):
        try:
            cmd, engine = get_latex_command(doc_name)
            result = subprocess.run(cmd, cwd=doc_folder,
                                    input="\n", capture_output=True, text=True)
            if result.returncode != 0:
                print("❌", end="", flush=True)
                clean_files(doc_name, doc_folder)
                log_output(result)
                extract_latex_errors(state)
                return False
            return True
        except FileNotFoundError:
            print("⚠️", end="", flush=True)
            with open(state['files']['LaTeX_log'], 'a') as f:
                f.write(f"\n[WARNING] LaTeX engine (xelatex/tectonic) not found. Skipping compilation check.\n")
            return True # Pretend it succeeded to let the flow continue

    def run_bibtex():
        try:
            # Tectonic handles bibliography automatically
            cmd, engine = get_latex_command(doc_name)
            if engine == "tectonic":
                return
            
            result = subprocess.run(["bibtex", doc_stem], cwd=doc_folder,
                                    capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"BibTeX failed:\n{result.stderr}")
        except FileNotFoundError:
            print(" (No bibtex) ", end="", flush=True)

    def log_output(result):
        with open(state['files']['LaTeX_log'], 'a') as f:
            f.write("---- STDOUT ----\n")
            f.write(result.stdout)
            f.write("---- STDERR ----\n")
            f.write(result.stderr)

    # Determine engine
    try:
        _, engine = get_latex_command(doc_name)
    except FileNotFoundError:
        engine = None

    # Pass 1
    if not(run_xelatex(pass_num=1)):
        return False

    if engine == "tectonic":
        # Tectonic is a one-pass compiler
        print("✅", end="", flush=True)
        clean_files(doc_name, doc_folder)
        return True

    # Bibliography step if needed
    if os.path.exists(bib_path):
        run_bibtex()
        total_passes = 3
    else:
        total_passes = 2

    # Additional passes
    for i in range(2, total_passes + 1):
        run_xelatex(pass_num=i)

    print("✅", end="", flush=True)
    clean_files(doc_name, doc_folder)
    return True
    

def compile_latex(state: GraphState, paper_name: str) -> None:
    """Compile the generated latex file

    Args:
        state (GraphState): input state
        paper_name (str): name of the paper
    """

    # get the paper stem
    paper_stem = Path(paper_name).stem

    def get_latex_command(name, is_final=False):
        if shutil.which("xelatex"):
            cmd = ["xelatex"]
            if is_final:
                cmd.extend(["-interaction=nonstopmode", "-file-line-error"])
            cmd.append(name)
            return cmd, "xelatex"
        elif shutil.which("tectonic"):
            return ["tectonic", name], "tectonic"
        else:
            raise FileNotFoundError("Neither xelatex nor tectonic found in PATH.")

    def run_xelatex():
        try:
            cmd, engine = get_latex_command(paper_name, is_final=True)
            return subprocess.run(cmd,
                                  cwd=state['files']['Paper_folder'],
                                  input="\n", capture_output=True,
                                  text=True, check=True)
        except FileNotFoundError:
            print("⚠️ (LaTeX engine missing, PDF not generated)", end="", flush=True)
            return None

    def run_bibtex():
        try:
            cmd, engine = get_latex_command(paper_name)
            if engine == "tectonic":
                return
            subprocess.run(["bibtex", paper_stem],
                           cwd=state['files']['Paper_folder'],
                           capture_output=True, text=True)
        except FileNotFoundError:
            pass

    def log_output(i, result_or_error, is_error=False):
        with open(state['files']['LaTeX_log'], 'a') as f:
            f.write(f"\n==== {'ERROR' if is_error else 'PASS'} on iteration {i} ====\n")
            f.write("---- STDOUT ----\n")
            f.write(result_or_error.stdout or "")
            f.write("---- STDERR ----\n")
            f.write(result_or_error.stderr or "")

    # Determine engine
    try:
        _, engine = get_latex_command(paper_name)
    except FileNotFoundError:
        engine = None

    # Try to compile it the first time
    print(f'Compiling {paper_stem}'.ljust(33,'.'), end="", flush=True)
    try:
        run_xelatex()
        print("✅", end="", flush=True)
    except subprocess.CalledProcessError as e:
        log_output("Pass 1", e, is_error=True)
        print("❌", end="", flush=True)

    if engine == "tectonic":
        # Tectonic is one-pass
        print("")
        return

    # if there is bibliography, compile it
    further_iterations = 1
    if os.path.exists(f"{state['files']['Paper_folder']}/bibliography.bib"):
        run_bibtex()
        further_iterations =2

    # Compile it two more times to put references and citations
    for i in range(further_iterations):        
        try:
            run_xelatex()
            print("✅", end="", flush=True)
        except subprocess.CalledProcessError as e:
            log_output(f"Final Pass {i+1}", e, is_error=True)
            print("❌", end="", flush=True)

    # remove auxiliary files
    for fin in [f'{paper_stem}.aux', f'{paper_stem}.log', f'{paper_stem}.out',
                f'{paper_stem}.bbl', f'{paper_stem}.blg', f'{paper_stem}.synctex.gz',
                f'{paper_stem}.synctex(busy)']:
        if os.path.exists(f"{state['files']['Paper_folder']}/{fin}"):
            os.remove(f"{state['files']['Paper_folder']}/{fin}")

    print("")



def save_paper(state: GraphState, paper_name: str):
    """
    This function just saves the current state of the paper

    Args:
       state: state of the graph
       name: name of the file to save the paper
    """

    journaldict: LatexPresets = journal_dict[state['paper']['journal']]

    author = "Denario"
    affiliation = r"Anthropic, Gemini \& OpenAI servers. Planet Earth."

    paper = rf"""\documentclass[{journaldict.layout}]{{{journaldict.article}}}

\usepackage{{amsmath}}
\usepackage{{multirow}}
\usepackage{{natbib}}
\usepackage{{graphicx}} 
\usepackage{{tabularx}}
{journaldict.usepackage}


\begin{{document}}

{journaldict.title}{{{state['paper'].get('Title','')}}}

{journaldict.author(author)}
{journaldict.affiliation(affiliation)}

{journaldict.abstract(state['paper'].get('Abstract',''))}
{journaldict.keywords(state['paper']['Keywords'])}


\section{{Introduction}}
\label{{sec:intro}}
{state['paper'].get('Introduction','')}

\section{{Methods}}
\label{{sec:methods}}
{state['paper'].get('Methods','')}

\section{{Results}}
\label{{sec:results}}
{state['paper'].get('Results','')}

\section{{Conclusions}}
\label{{sec:conclusions}}
{state['paper'].get('Conclusions','')}

\bibliography{{bibliography}}{{}}
{journaldict.bibliographystyle}

\end{{document}}
"""
    
    # save paper to file
    f_in = f"{state['files']['Paper_folder']}/{paper_name}"
    with open(f_in, 'w', encoding='utf-8') as f:
        f.write(paper)


def save_bib(state: GraphState):
    with open(f"{state['files']['Paper_folder']}/bibliography_temp.bib", 'a', encoding='utf-8') as f:
        f.write(state['paper']['References'].strip() + "\n")    



def escape_special_chars(text):
    # Split into math and non-math parts
    parts = re.split(r'(\$.*?\$)', text)  # keep $...$ parts intact
    sanitized = []

    for part in parts:
        if part.startswith('$') and part.endswith('$'):
            # Don't touch math parts
            sanitized.append(part)
        else:
            # Escape special characters
            for char, escaped in special_chars.items():
                part = part.replace(char, escaped)
            sanitized.append(part)

    return ''.join(sanitized)


def process_bib_file(input_file, output_file):
    with open(input_file, 'r') as fin:
        lines = fin.readlines()

    processed_lines = []
    for line in lines:
        if line.strip().startswith('title') or line.strip().startswith('journal'):
            key, value = line.split('=', 1)
            # quote_char = '"' if '"' in value else '{'
            content = re.search(r'[{\"](.+)[}\"]', value).group(1)
            escaped_content = escape_special_chars(content)

            # Optional: preserve acronyms (wrap them in braces)
            escaped_content = re.sub(r'\b([A-Z]{2,})\b', r'{\1}', escaped_content)

            processed_lines.append(f'  {key.strip()} = {{{escaped_content}}},\n')
        else:
            processed_lines.append(line)

    with open(output_file, 'w') as fout:
        fout.writelines(processed_lines)

    print(f"Sanitized BibTeX saved to: {output_file}")

    
def fix_latex(state, f_temp):
    """
    This function is designed to attemp to fix LaTeX errors
    The function returns the state and whether it has fixed the problem or not
    """

    file_path = Path(f_temp)
    f_stem    = file_path.with_suffix('')
    suffix    = file_path.suffix
    
    # You have three attemps to fix the problem
    for i in range(3):

        # make a LLM call with the problematic text and the LaTeX errors
        # uses state['files']['LaTeX_err'] and state['latex']['sction'] for the prompt
        PROMPT = fix_latex_bug_prompt(state)  
        state, result = LLM_call(PROMPT, state)
        fixed_text = extract_latex_block(state, result, "Text")
        state['paper'][state['latex']['section_to_fix']] = fixed_text

        # save text to file
        f_name = f"{f_stem}_v{i+1}{suffix}"
        temp_file(state, f_name, 'write', fixed_text)

        # compile again; if successful change file names and exit
        if compile_tex_document(state, f_name, state['files']['Temp']):
            os.system(f'mv {f_temp} {f_stem}_orig{suffix}')
            os.system(f"mv {f_name} {f_temp}")
            return state, True
    
    return state, False
        

def fix_percent(text):
    """
    This function replaces any % (that is not \\%) by \\%. This is useful as in the abstract many times percentiles are quoted and if not \\%, LaTeX will interpret it as a comment.
    """
    
    # Replace any % that is not preceded by a backslash
    return re.sub(r'(?<!\\)%', r'\\%', text)
