# money_machine

## Install pre-commit

Run this command to create Git hooks using the `pre-commit` framework:

```bash
pre-commit install
```

If you have created some commits before installing the Git hooks, you might want to run the hooks against all files right after the installation:

```bash
pre-commit run --all-files
```

## Setup Conda Environment

Create a new Conda environment using the `environment.yml` file:

```bash
mamba env create --name multimodal -f environment.yml
```

Activate the environment:

```bash
mamba activate multimodal
```