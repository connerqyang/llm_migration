# LLM Migration Tool

A tool for migrating TUX UI components in a large monorepo structure using LLM-powered code transformation and validation.

## Overview

This tool helps migrate components from the old TUX UI library to the newer version by using LLM-powered code transformation. It provides functionality for working with files in a large monorepo by using a modular path building approach:

```
Full Path = LOCAL_REPO_PATH + SUBREPO_PATH + FILE_PATH
```

Where:

- `LOCAL_REPO_PATH`: The absolute path to the base repository (configured in .env)
- `SUBREPO_PATH`: The relative path to the subrepository (provided as a command-line argument)
- `FILE_PATH`: The relative path to the specific file (provided as a command-line argument)

The tool uses Gemini 2.5 Flash model to analyze and transform React components, followed by a validation pipeline to ensure the migrated code passes ESLint, TypeScript, and build checks.

## Configuration

The tool uses environment variables for configuration. Create a `.env` file in the project root with the following variables:

```
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash
GIT_REPO_URL=your_repo_url
GIT_AUTH_TOKEN=your_auth_token
LOCAL_REPO_PATH=/absolute/path/to/your/repo
```

### Dependencies

The tool requires the following Python dependencies (specified in requirements.txt):

```
openai==1.88.0
gitpython==3.1.44
python-dotenv==1.0.0
typing-extensions==4.14.0
```

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

The tool provides two main commands: `migrate` and `list`.



### Migrating Components

Use the main.py script to migrate a component:

```bash
python src/main.py migrate --component ComponentName --subrepo-path path/to/subrepo --file-path path/to/component.tsx
```

Example with full paths:

```bash
python src/main.py migrate --component TUXIcon --subrepo-path packages/apps/tiktok_live_web/e-commerce/after-sale-collection --file-path src/pages/Refund/containers/refunddetail-global/components/HorizontalProgressLine/components/ProgressNode/index.tsx
```

Parameters:

- `--component`: The name of the component to migrate (choices: TUXIcon, TUXButton)
- `--file-path`: Relative path to the file within the subrepo path
- `--subrepo-path`: Path to a subrepository relative to LOCAL_REPO_PATH
- `--max-retries`: Maximum number of retries for validation steps (default: 3)
- `--step`: Specific validation steps to run (choices: 'fix-eslint', 'fix-build', 'fix-tsc')

The migration process includes:
1. Reading the source file
2. Analyzing the component using LLM
3. Transforming the component according to migration guidelines
4. Running validation steps (ESLint, TypeScript, Build)
5. Committing the changes if all validations pass

### Listing Supported Components

List all components that can be migrated:

```bash
python src/main.py list
```

## Implementation Details

### Core Components

#### GitOperations Class

The `GitOperations` class provides methods for working with Git repositories:

- `__init__(repo_path=None, subrepo_path=None, file_path=None)`: Initialize with optional custom paths and file path
- `get_subrepo_path()`: Get the full path to the subrepo directory
- `read_file()`: Read the file specified during initialization
- `write_file(content)`: Write content to the file without committing
- `commit_changes(content, commit_message)`: Write and commit changes to the file
- `create_branch(branch_name, base_branch="master")`: Create and checkout a new branch
- `push_changes(branch_name)`: Push changes to remote
- `pull_changes(branch_name)`: Pull changes from remote
- `delete_local_branch(branch_name)`: Delete a local branch
- `delete_remote_branch(branch_name)`: Delete a remote branch
- `cleanup_branch(branch_name)`: Delete a branch both locally and remotely

#### LLMClient Class

The `LLMClient` class handles interactions with the Gemini API for component migration:

- `__init__()`: Initialize the LLM client with API keys and configuration
- `get_supported_components()`: Get a list of supported components for migration
- `migrate_component(component_name, component_code)`: Migrate a component using the LLM

#### ValidationOperations Class

The `ValidationOperations` class handles validation of migrated code:

- `__init__(git_ops, max_retries=3)`: Initialize with GitOperations instance and retry settings
- `update_migration_status(code, status_updates)`: Update migration status comments in the code
- `run_validation_step(code, validation_type, llm_client)`: Run a specific validation step (ESLint, TypeScript, Build)

## Examples

### Reading a File

```python
from src.utils.git_operations import GitOperations

# Initialize with default paths from .env
git_ops = GitOperations()

# Read a file using the modular path
content = git_ops.read_file('component.tsx')
# This will read from: LOCAL_REPO_PATH/PAGE_PATH/component.tsx
```

### Writing and Committing Changes

```python
from src.utils.git_operations import GitOperations

# Initialize with custom page path
git_ops = GitOperations(page_path='custom/page/path')

# Create a branch
git_ops.create_branch('feature/update-component')

# Write and commit changes
git_ops.commit_changes(
    'component.tsx',
    '// Updated component code',
    'Update component'
)

# Push changes
git_ops.push_changes('feature/update-component')
```
