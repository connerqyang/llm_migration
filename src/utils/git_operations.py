from git import Repo
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class GitOperations:
    def __init__(self, repo_path=None, page_path=None):
        """
        Initialize GitOperations with modular path building support.
        
        Args:
            repo_path: Base repository path. If None, uses LOCAL_REPO_PATH from env.
            page_path: Relative path to the page directory. If None, uses PAGE_PATH from env.
        """
        self.repo_url = os.getenv("GIT_REPO_URL")
        self.auth_token = os.getenv("GIT_AUTH_TOKEN")
        
        # Construct authenticated URL if token is provided (for potential remote operations)
        if self.auth_token and self.repo_url:
            # Handle different repository URL formats
            if self.repo_url.startswith("https://"):
                # For HTTPS URLs
                protocol_part, rest = self.repo_url.split("https://", 1)
                self.authenticated_url = f"https://{self.auth_token}@{rest}"
            elif self.repo_url.startswith("git@"):
                # For SSH URLs, token might be used differently or not needed
                self.authenticated_url = self.repo_url
            else:
                self.authenticated_url = self.repo_url
        else:
            self.authenticated_url = self.repo_url
        
        # Use provided repo_path or get from environment
        self.repo_path = repo_path if repo_path else os.getenv("LOCAL_REPO_PATH")
        
        # Get page path from arguments or environment
        self.page_path = page_path if page_path else os.getenv("PAGE_PATH", "")
        
        # Verify the repository path exists
        if not os.path.exists(self.repo_path):
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
            
        # Use existing repository
        self.repo = Repo(self.repo_path)
        
    def build_file_path(self, file_path):
        """
        Build a complete file path using the modular path components
        
        Args:
            file_path: Relative path to the file within the page directory
            
        Returns:
            Complete path to the file (absolute path)
        """
        # Join repo_path, page_path, and file_path to create the complete path
        # Use Path for better cross-platform path handling
        return str(Path(self.repo_path) / self.page_path / file_path)
    
    def read_file(self, file_path):
        """
        Read a file from the repository
        
        Args:
            file_path: Relative path to the file within the page directory
            
        Returns:
            String content of the file
        """
        full_path = self.build_file_path(file_path)
        with open(full_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def write_file(self, file_path, content):
        """
        Write content to a file without committing
        
        Args:
            file_path: Relative path to the file within the page directory
            content: Content to write to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self.build_file_path(file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            print(f"Error writing to file: {str(e)}")
            return False
    
    def create_branch(self, branch_name, base_branch="master"):
        """
        Create a new branch from latest origin/base_branch and switch to it
        
        Args:
            branch_name: Name of the new branch
            base_branch: Base branch to create from (default: "master")
            
        Returns:
            Name of the created branch
        """
        # First checkout the base branch
        if base_branch in [b.name for b in self.repo.branches]:
            self.repo.git.checkout(base_branch)
        else:
            # If base branch doesn't exist locally, create it tracking the remote
            self.repo.git.checkout('-b', base_branch, f'origin/{base_branch}')
        
        # Pull latest changes from remote
        origin = self.repo.remote(name='origin')
        origin.pull(base_branch)
        
        # Check if branch already exists
        if branch_name in [b.name for b in self.repo.branches]:
            # If it exists, just check it out
            branch = self.repo.branches[branch_name]
        else:
            # Create new branch from updated base_branch
            branch = self.repo.create_head(branch_name)
        
        branch.checkout()
        return branch.name
    
    def commit_changes(self, file_path, content, commit_message):
        """
        Write changes to a file and commit them
        
        Args:
            file_path: Relative path to the file within the page directory
            content: New content to write to the file
            commit_message: Commit message
            
        Returns:
            The commit object
        """
        try:
            # Ensure git user is configured
            try:
                # Check if user.name is configured
                self.repo.git.config('--get', 'user.name')
            except Exception:
                # Set a temporary user.name
                print("Setting temporary git user.name")
                self.repo.git.config('--local', 'user.name', 'LLM Migration Tool')
                
            try:
                # Check if user.email is configured
                self.repo.git.config('--get', 'user.email')
            except Exception:
                # Set a temporary user.email
                print("Setting temporary git user.email")
                self.repo.git.config('--local', 'user.email', 'llm.migration@example.com')
            
            # Create the full path to the file using the modular path building
            full_path = self.build_file_path(file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write the content to the file
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            # Calculate the relative path from repo root for git operations
            # This is necessary because git operations need paths relative to repo root
            if self.page_path:
                git_relative_path = os.path.join(self.page_path, file_path)
            else:
                git_relative_path = file_path
            
            # Add the file to git index
            print(f"Adding file to git: {git_relative_path}")
            self.repo.git.add(git_relative_path)
            
            # Commit the changes using git.commit() instead of index.commit()
            print(f"Committing changes with message: {commit_message}")
            self.repo.git.commit('-m', commit_message)
            
            # Get the commit object for the latest commit
            commit = self.repo.head.commit
            print(f"Commit successful: {commit.hexsha}")
            
            return commit
            
        except Exception as e:
            print(f"Error in commit_changes: {str(e)}")
            # Print more detailed git status for debugging
            print(f"Git status: {self.repo.git.status()}")
            raise
    
    def push_changes(self, branch_name=None):
        """
        Push changes to remote repository
        
        Args:
            branch_name: Name of the branch to push. If None, pushes the current branch.
            
        Returns:
            Result of the push operation
        """
        if not branch_name:
            branch_name = self.repo.active_branch.name
        
        # Make sure we have a remote
        if not self.repo.remotes:
            if self.authenticated_url:
                self.repo.create_remote('origin', self.authenticated_url)
            else:
                raise ValueError("No remote configured and no authenticated URL available")
        
        origin = self.repo.remote(name='origin')
        return origin.push(branch_name)
    
    def pull_changes(self, branch_name=None):
        """
        Pull latest changes from remote repository
        
        Args:
            branch_name: Name of the branch to pull. If None, pulls the current branch.
            
        Returns:
            Result of the pull operation
        """
        if not branch_name:
            branch_name = self.repo.active_branch.name
        
        origin = self.repo.remote(name='origin')
        return origin.pull(branch_name)
    
    def delete_local_branch(self, branch_name):
        """
        Delete a local branch
        
        Args:
            branch_name: Name of the branch to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First checkout main/master branch to avoid being on the branch we're trying to delete
            default_branch = 'main' if 'main' in [b.name for b in self.repo.branches] else 'master'
            self.repo.git.checkout(default_branch)
            
            # Delete the branch
            print(f"Deleting local branch: {branch_name}")
            self.repo.git.branch('-D', branch_name)
            print(f"Local branch {branch_name} deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting local branch {branch_name}: {str(e)}")
            return False
    
    def delete_remote_branch(self, branch_name):
        """
        Delete a remote branch
        
        Args:
            branch_name: Name of the branch to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure we have a remote
            if not self.repo.remotes:
                raise ValueError("No remote configured")
            
            origin = self.repo.remote(name='origin')
            print(f"Deleting remote branch: {branch_name}")
            # The syntax for deleting a remote branch is to push an empty reference
            result = origin.push(f":{branch_name}")
            print(f"Remote branch {branch_name} deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting remote branch {branch_name}: {str(e)}")
            return False
    
    def cleanup_branch(self, branch_name):
        """
        Clean up a branch by deleting it both locally and remotely
        
        Args:
            branch_name: Name of the branch to clean up
            
        Returns:
            True if both operations were successful, False otherwise
        """
        remote_success = self.delete_remote_branch(branch_name)
        local_success = self.delete_local_branch(branch_name)
        return remote_success and local_success