# LLM Migration Tool

A tool for migrating components in a large monorepo structure using modular path building.

## Overview

This tool provides functionality for working with files in a large monorepo by using a modular path building approach:

```
Full Path = LOCAL_REPO_PATH + PAGE_PATH + FILE_PATH
```

Where:

- `LOCAL_REPO_PATH`: The absolute path to the base repository (configured in .env)
- `PAGE_PATH`: The relative path to the page directory (configured in .env)
- `FILE_PATH`: The relative path to the specific file (provided programmatically)

## Configuration

The tool uses environment variables for configuration. Create a `.env` file in the project root with the following variables:

```
GOOGLE_API_KEY=your_api_key
GIT_REPO_URL=your_repo_url
GIT_AUTH_TOKEN=your_auth_token
LOCAL_REPO_PATH=/absolute/path/to/your/repo
PAGE_PATH=relative/path/to/page/directory
```

## Usage

### Testing Git Operations

Test the Git operations functionality with the modular path building approach by reading, modifying, and pushing changes to an existing file:

```bash
python -m src.main --file-path=modules/ReturnShippingModule/index.tsx --page-path=custom/page/path
```

Or directly run the test module:

```bash
python -m tests.test_git_operations --file-path=modules/ReturnShippingModule/index.tsx --page-path=custom/page/path
```

Parameters:

- `--file-path`: Relative path to the test file within the page directory
- `--page-path`: Override the PAGE_PATH from .env
- `--auto-push`: Automatically push changes without prompting

### Migrating Components

Use the migrate_component.py script to migrate a component:

```bash
python migrate_component.py path/to/component.tsx --branch=feature/migrate-component
```

Parameters:

- `file_path`: Relative path to the file within the page directory
- `--branch`: Optional branch name to create for the migration

## Implementation Details

### GitOperations Class

The `GitOperations` class provides methods for working with Git repositories using the modular path building approach:

- `__init__(repo_path=None, page_path=None)`: Initialize with optional custom paths
- `build_file_path(file_path)`: Build a complete file path using the modular components
- `read_file(file_path)`: Read a file using the modular path
- `commit_changes(file_path, content, commit_message)`: Write and commit changes
- `create_branch(branch_name)`: Create and checkout a new branch
- `push_changes(branch_name)`: Push changes to remote
- `pull_changes(branch_name)`: Pull changes from remote
- `cleanup_branch(branch_name)`: Delete a branch both locally and remotely

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
