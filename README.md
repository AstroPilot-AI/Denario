# Denario

[![Version](https://img.shields.io/pypi/v/denario.svg)](https://pypi.python.org/pypi/denario) [![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue.svg)](https://www.python.org/downloads/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/denario)](https://pypi.python.org/pypi/denario) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Denario is a multiagent system designed to automatize scientific research. Denario implements AI agents with [AG2](https://ag2.ai/) and [LangGraph](https://www.langchain.com/langgraph). The research analysis backend is [cmbagent](https://github.com/CMBAgents/cmbagent). Project under construction.

## Resources

- [Project page](https://astropilot-ai.github.io/DenarioPaperPage/)

- [Documentation](https://denario.readthedocs.io/en/latest/)

- [End-to-end research papers generated with Denario](https://github.com/AstroPilot-AI/DenarioExamplePapers)

## Installation

To install denario, just run

```bash
pip install denario
```

## Get started

Initialize a `Denario` instance and describe the data and tools to be employed.

```python
from denario import Denario

den = Denario(project_dir="project_dir")

prompt = """
Analyze the experimental data stored in data.csv using sklearn and pandas.
This data includes time-series measurements from a particle detector.
"""

den.set_data_description(prompt)
```

Generate a research idea from that data specification.

```python
den.get_idea()
```

Generate the methodology required for working on that idea.

```python
den.get_method()
```

With the methodology setup, perform the required computations and get the plots and results.

```python
den.get_results()
```

Finally, generate a latex article with the results. You can specify the journal style, in this example we choose the [APS (Physical Review Journals)](https://journals.aps.org/) style.

```python
from denario import Journal

den.get_paper(journal=Journal.APS)
```

You can also manually provide any info as a string or markdown file in an intermediate step, using the `set_idea`, `set_method` or `set_results` methods. For instance, for providing a file with the methodology developed by the user:

```python
den.set_method(path_to_the_method_file.md)
```

## App

You can run Denario using a GUI through the [DenarioApp](https://github.com/AstroPilot-AI/DenarioApp).

Test the deployed app in [HugginFace Spaces](nope).

## Build from source

### pip

You will need python 3.12 installed.

Create a virtual environment

```bash
python3 -m venv .venv
```

Activate the virtual environment

```bash
source .venv/bin/activate
```

And install the project

```bash
pip install -e .
```

### uv

You can also install the project using [uv](https://docs.astral.sh/uv/), just running:

```bash
uv sync
```

which will create the virtual environment and install the dependencies and project. Activate the virtual environment if needed with

```bash
source .venv/bin/activate
```

## Contributing

Pull requests are welcome! Feel free to open an issue for bugs, comments, questions and suggestions.

<!-- ## Citation

If you use this library please link this repository and cite [arXiv:2506.xxxxx](arXiv:x2506.xxxxx). -->

## License

[GNU GENERAL PUBLIC LICENSE (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.html)
