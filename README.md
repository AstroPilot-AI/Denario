# Denario

[![Version](https://img.shields.io/pypi/v/denario.svg)](https://pypi.python.org/pypi/denario) [![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue.svg)](https://www.python.org/downloads/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/denario)](https://pypi.python.org/pypi/denario) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/AstroPilot-AI/Denario)
<a href="https://www.youtube.com/@denario-ai" target="_blank">
<img src="https://img.shields.io/badge/YouTube-Subscribe-red?style=flat-square&logo=youtube" alt="Subscribe on YouTube" width="140"/>
</a>

Denario is a multiagent system designed to be a scientific research assistant. Denario implements AI agents with [AG2](https://ag2.ai/) and [LangGraph](https://www.langchain.com/langgraph), using [cmbagent](https://github.com/CMBAgents/cmbagent) as the research analysis backend. Denario and Cmbagent are Open Source Software projects under GPL-3 and Apache 2 licenses respectively. No private or public organizations/individuals other than the three copyright holders can claim IP and/or ownership on these software packages.

## Resources

- [🌐 Project page](https://astropilot-ai.github.io/DenarioPaperPage/)

- [📄 Paper](https://arxiv.org/abs/2510.26887)

- [📖 Documentation](https://denario.readthedocs.io/en/latest/)

- [🖥️ Denario GUI repository](https://github.com/AstroPilot-AI/DenarioApp)

- [🤗 Demo web app for Denario GUI](https://huggingface.co/spaces/astropilot-ai/Denario)

- [📝 End-to-end research papers generated with Denario](https://github.com/AstroPilot-AI/DenarioExamplePapers)

- [🎥 YouTube channel](https://www.youtube.com/@denario-ai)

## Last updates

- January 20, 2026 - [Denario](https://github.com/AstroPilot-AI/Denario) and [Cmbagent](https://github.com/CMBAgents/cmbagent) featured in the [LSST DESC AI Roadmap](https://arxiv.org/abs/2601.14235). 

- December 7, 2025 - [Cmbagent](https://github.com/CMBAgents/cmbagent), the research analysis backend of Denario, won a **first place award** at the **NeurIPS 2025 [Fair Universe Competition](https://fair-universe.lbl.gov/)**. 

- November 3, 2025 - Version 1.0 is released and the Denario paper is out at [arxiv](https://arxiv.org/pdf/2510.26887)!

- October 9, 2025 - A paper fully generated with Denario has been accepted for publication in the [Open Conference of AI Agents for Science 2025](https://openreview.net/forum?id=LENY7OWxmN), the 1st open conference with AI as primary authors.

## Installation

To install denario create a virtual environment and pip install it. We recommend using Python 3.12:

```bash
python -m venv Denario_env
source Denario_env/bin/activate
pip install "denario[app]"
```

Or alternatively install it with [uv](https://docs.astral.sh/uv/), initializing a project and installing it:

```bash
uv init
uv add denario[app]
```

Then, run the gui with:

```
denario run
```

### Credentials 

Denario makes use of LLMs from OpenAI, Claude and Gemini. See the [documentation on LLM API keys](https://denario.readthedocs.io/en/latest/llm_api_keys/apikeys/) for setup instructions.


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

Before paper generation, Denario now requires explicit human sign-off that the generated artifacts were reviewed and that a human accepts authorship responsibility.

```python
den.confirm_authorship(
    "I checked the claims against the results, reviewed the citations, and rewrote the sections I will stand behind."
)
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

## DenarioApp

You can run Denario using a GUI through the [DenarioApp](https://github.com/AstroPilot-AI/DenarioApp).

The app is already installed with `pip install "denario[app]"`, otherwise install it with `pip install denario_app` or `uv sync --extra app`.

Then, launch the GUI with

```bash
denario run
```

Test a [deployed demo of the app in HugginFace Spaces](https://huggingface.co/spaces/astropilot-ai/Denario).

## Build from source

### pip

You will need python 3.12 or higher installed. Clone Denario:

```bash
git clone https://github.com/AstroPilot-AI/Denario.git
cd Denario
```

Create and activate a virtual environment

```bash
python3 -m venv Denario_env
source Denario_env/bin/activate
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

## Docker

You can run Denario in a [Docker](https://www.docker.com/) image, which includes all the required dependencies for Denario including LaTeX. Pull the image with:

```bash
docker pull pablovd/denario:latest
```

Once built, you can run the GUI with

```bash
docker run -p 8501:8501 --rm pablovd/denario:latest
```

or in interactive mode with

```bash
docker run --rm -it pablovd/denario:latest bash
```

Share volumes with `-v $(pwd)/project:/app/project` for inputing data and accessing to it. You can also share the API keys with a `.env` file in the same folder with `-v $(pwd).env/app/.env`.

You can also build an image locally with

```bash
docker build -f docker/Dockerfile.dev -t denario_src .
```

Read more information on how to use the Docker images in the [documentation](https://denario.readthedocs.io/en/latest/docker/).

## Contributing

Pull requests are welcome! Feel free to open an issue for bugs, comments, questions and suggestions.

<!-- ## Citation

If you use this library please link this repository and cite [arXiv:2506.xxxxx](arXiv:x2506.xxxxx). -->

## Citation

If you make use of Denario, please cite the following references:

```bibtex
@article{villaescusanavarro2025denarioprojectdeepknowledge,
         title={The Denario project: Deep knowledge AI agents for scientific discovery}, 
         author={Francisco Villaescusa-Navarro and Boris Bolliet and Pablo Villanueva-Domingo and Adrian E. Bayer and Aidan Acquah and Chetana Amancharla and Almog Barzilay-Siegal and Pablo Bermejo and Camille Bilodeau and Pablo Cárdenas Ramírez and Miles Cranmer and Urbano L. França and ChangHoon Hahn and Yan-Fei Jiang and Raul Jimenez and Jun-Young Lee and Antonio Lerario and Osman Mamun and Thomas Meier and Anupam A. Ojha and Pavlos Protopapas and Shimanto Roy and David N. Spergel and Pedro Tarancón-Álvarez and Ujjwal Tiwari and Matteo Viel and Digvijay Wadekar and Chi Wang and Bonny Y. Wang and Licong Xu and Yossi Yovel and Shuwen Yue and Wen-Han Zhou and Qiyao Zhu and Jiajun Zou and Íñigo Zubeldia},
         year={2025},
         eprint={2510.26887},
         archivePrefix={arXiv},
         primaryClass={cs.AI},
         url={https://arxiv.org/abs/2510.26887},
}

@software{Denario_2025,
          author = {Pablo Villanueva-Domingo, Francisco Villaescusa-Navarro, Boris Bolliet},
          title = {Denario: Modular Multi-Agent System for Scientific Research Assistance},
          year = {2025},
          url = {https://github.com/AstroPilot-AI/Denario},
          note = {Available at https://github.com/AstroPilot-AI/Denario},
          version = {latest}
          }

@software{CMBAGENT_2025,
          author = {Boris Bolliet},
          title = {CMBAGENT: Open-Source Multi-Agent System for Science},
          year = {2025},
          url = {https://github.com/CMBAgents/cmbagent},
          note = {Available at https://github.com/CMBAgents/cmbagent},
          version = {latest}
          }
```

## License

[GNU GENERAL PUBLIC LICENSE (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.html)

Denario - Copyright (C) 2026 Pablo Villanueva-Domingo, Francisco Villaescusa-Navarro, Boris Bolliet

## Contact and enquiries

E-mail: [denario.astropilot.ai@gmail.com](mailto:denario.astropilot.ai@gmail.com)
