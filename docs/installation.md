# Installation Guide

This guide will walk you through the process of installing `cloudmesh-ai-vm` on your local machine.

## Prerequisites

- **Python 3.x**: Ensure you have Python 3.8 or higher installed.
- **Pip**: The Python package installer.

### Python 3.15.2

The project is working towards the use of **Python 3.15.2**. It is recommended to use this exact version to avoid compatibility issues. 

!!! warning 
    We are not yet completed with this migration, but if issues are found please immediatly communicate them so we can either fix them or roll back the python version.

You can verify your current Python version with:

```bash
python3 --version
```

If you need to install or switch to Python 3.15.2, consider using a version manager such as **pyenv**:

```bash
pyenv install 3.15.2
pyenv local 3.15.2
```

Or on macOS you can install it via Homebrew:

```bash
brew install python@3.15
```

When creating a virtual environment, explicitly point to this interpreter:

```bash
python3.15 -m venv ~/ENV315
```

We use this location and name as other cloudmesh-ai-* packages can reuse and test the same python version and assure compatibility.

Make aslo sure you have the newest version of pip after you activated the python version with 



```
source ~/ENV3/bin/activate # use the method fro your OS
pip install pip -U
```

## Setup Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/cloudmesh-ai-vm.git
cd cloudmesh-ai-vm
```

### 2. Install Dependencies

We recommend using a virtual environment to avoid dependency conflicts.

```bash
python -m venv ~/ENV315
source ~/ENV315/bin/activate  
# On Windows: $HOME\\ENV315\\Scripts\\activate 
# On windows we highly recommend using gitbash
pip install -r requirements.txt
```

### 3. Install the CLI Tool

Install the package in editable mode so you can make changes to the source code:

```bash
pip install -e .
```

## Verifying Installation

Run the following command to ensure the CLI is installed and working:

```bash
 cmx --help
```

If you see the help menu, you are ready to go!

### 4. Install using uv

**uv** is a fast, drop‑in replacement for `pip` and `venv`. It can create a virtual environment and install the project in a single command.

#### Install `uv`

```bash
# macOS (Homebrew)
brew install uv

# Linux (curl script)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Create a virtual environment (optional)

```bash
uv venv ~/.venv
source .venv/bin/activate   # Activate the environment
```

#### Install the package in editable mode

```bash
uv pip install -e .
```

You can also install directly without creating a separate virtual environment:

```bash
uv pip install -e .
```

### 5. Using direnv for automatic environment activation

`direnv` automatically loads environment variables when you `cd` into a directory. It can also activate a Python virtual environment for you.

#### Install `direnv`

```bash
# macOS
brew install direnv

# Debian/Ubuntu
sudo apt-get install direnv
```

#### Add the shell hook

Add the following line to your shell's startup file (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
eval "$(direnv hook bash)"   # replace `bash` with `zsh` or `fish` as appropriate
```

Reload your shell or source the file:

```bash
source ~/.bashrc   # or the appropriate file
```

#### Create a `.envrc` file in the repository root

```bash
# .envrc
# If a .venv exists, activate it
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    # Let direnv set up a temporary python virtual environment
    layout python
fi
```

After creating the file, allow direnv to trust it:

```bash
direnv allow
```

Now, whenever you `cd` into the `cloudmesh-ai-vm` directory, the virtual environment will be automatically activated. This works seamlessly with the `uv` virtual environment created above.
