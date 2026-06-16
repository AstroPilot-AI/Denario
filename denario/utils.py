import os
import re
from pathlib import Path
import warnings

from .llm import LLM, models

def input_check(str_input: str) -> str:
    """Check if the input is a string with the desired content or the path markdown file, in which case reads it to get the content."""

    if str_input.endswith(".md"):
        with open(str_input, 'r') as f:
            content = f.read()
    elif isinstance(str_input, str):
        content = str_input
    else:
        raise ValueError("Input must be a string or a path to a markdown file.")
    return content

def llm_parser(llm: LLM | str) -> LLM:
    """Get the LLM instance from a string."""

    if isinstance(llm, str):
        try:
            llm = models[llm]
        except KeyError:
            raise KeyError(f"LLM '{llm}' not available. Please select from: {list(models.keys())}")
    return llm

def extract_file_paths(markdown_text):
    """
    Extract the bulleted file paths from markdown text 
    and check if they exist and are absolute paths.
    
    Args:
        markdown_text (str): The markdown text containing file paths
    
    Returns:
        tuple: (existing_paths, missing_paths)
    """
    
    # Pattern to match file paths in markdown bullet points
    pattern = r'-\s*([^\n]+\.(?:h5|xlsx|xls|csv|txt|md|py|json|yaml|yml|xml|html|css|js|ts|tsx|jsx|java|cpp|c|h|hpp|go|rs|php|rb|pl|sh|bat|sql|log))'
    
    # Find all matches
    matches = re.findall(pattern, markdown_text, re.IGNORECASE)
    
    # Clean up paths and check existence
    existing_paths = []
    missing_paths = []
    
    for match in matches:
        path = match.strip()
        if os.path.exists(path) and os.path.isabs(path):
            existing_paths.append(path)
        else:
            missing_paths.append(path)
    
    return existing_paths, missing_paths

def check_file_paths(content: str) -> None:
    """Check that file paths indicated in content text have the proper format"""

    existing_paths, missing_paths = extract_file_paths(content)

    if len(missing_paths) > 0:
        warnings.warn(
            f"The following data files paths in the data description are not in the right format or do not exist:\n"
            f"{missing_paths}\n"
            f"Please fix them according to the convention '- /absolute/path/to/file.ext'\n"
            f"otherwise this may cause hallucinations in the LLMs."
        )

    if len(existing_paths) == 0:
        warnings.warn(
            "No data files paths were found in the data description. If you want to provide input data, ensure that you indicate their path, otherwise this may cause hallucinations in the LLM in the get_results() workflow later on."
        )

def create_work_dir(work_dir: str | Path, name: str) -> Path:
    """Create working directory"""

    work_dir = os.path.join(work_dir, f"{name}_generation_output")
    os.makedirs(work_dir, exist_ok=True)
    return Path(work_dir)

def get_task_result(chat_history, name: str):
    """Get task result from chat history"""
    
    for obj in chat_history[::-1]:
        # Using .get() to avoid KeyError if 'name' is missing
        if obj.get('name') == name:
            return obj.get('content')
            
    return None

def in_notebook():
    """Check whether the code is run from a Jupyter Notebook or not, to use different display options"""
    
    try:
        from IPython import get_ipython # type: ignore
        if 'IPKernelApp' not in get_ipython().config:  # type: ignore # pragma: no cover
            return False
    except ImportError:
        return False
    except AttributeError:
        return False
    return True
