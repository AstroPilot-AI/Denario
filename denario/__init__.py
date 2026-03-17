from ._compat import patch_mistralai_for_cmbagent

patch_mistralai_for_cmbagent()

from .denario import Denario, Research, Journal, LLM, models, KeyManager
from .config import REPO_DIR

__all__ = ['Denario', 'Research', 'Journal', 'REPO_DIR', 'LLM', "models", "KeyManager"]

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("denario")
except PackageNotFoundError:
    # fallback for editable installs, local runs, etc.
    __version__ = "0.0.0"
