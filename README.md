# Building an AI Agent

## Workshop description
In this workshop, we will first study the relationship between an AI Agent and an AI model. Then, by some hands-on exercises, we will learn how to choose the right model for building your own AI Agent; and how to build an AI Agent from scratch.

This workshop is designed for participants to be creative and come up with their own unique AI agent ideas. We will only provide the basic knowledge and techniques needed to build an AI agent and guidance for problem-solving.

By building an AI Agent and comparing AI models, we will learn more about how an AI Agent works and all the things we need to know when considering building an AI Agent for commercial use.

## Requirements
* PyLadies Amsterdam uses [uv](https://docs.astral.sh/uv/) for dependency management
* Please see [pyproject.toml](solutions/Exercise_2/pyproject.toml) for dependencies
 
## Usage
### with uv
Run the following code:
```bash
git clone <github-url-of-workshop-repo>
cd <name-of-repo>

# create and activate venv, install dependencies
uv sync
```

### for a workshop giver
To get started, open the `pyproject.toml` file and set the required Python version. The pre-selected version 3.8 is generally a safe choice for most use cases.

After you have specified the Python version, you can create a virtual environment with `uv venv` and add packages with `uv add <package>`. Before the workshop, you can generate a requirements.txt file, which is needed e.g. for running code in Google Colab, by running `uv export > requirements.txt`.

## Video record
Re-watch [this YouTube stream](https://youtube.com/live/H3SKftUjXLg)

## Credits
This workshop was set up by @pyladiesams and @Cheukting

## Appendix
### Pre-Commit Hooks

To ensure our code looks beautiful, PyLadies uses pre-commit hooks. You can enable them by running `pre-commit install`. You may have to install `pre-commit` first, using `uv sync`, `uv pip install pre-commit` or `pip install pre-commit`.

Happy Coding :)
