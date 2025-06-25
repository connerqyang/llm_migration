from git import Repo
import os
from dotenv import load_dotenv
from pathlib import Path

# Import console output icons
from src.utils.validation import SUCCESS_ICON, ERROR_ICON, WARNING_ICON, INFO_ICON, PENDING_ICON

# Load environment variables from .env file
load_dotenv()

class GitOperations:
    def __init__(self, repo_path=None, subrepo_path=None, file_path=None):
        """
        Initialize GitOperations with modular path building support.
        
        Args:
            repo_path: Base repository path. If None, uses LOCAL_REPO_PATH from env.
            subrepo_path: Subrepository path relative to repo_path. Used for operations like yarn build.
            file_path: Path to the file relative to subrepo_path.
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
        
        # Make paths absolute
        # Store subrepo_path as absolute path
        if subrepo_path:
            self.subrepo_path = str(Path(self.repo_path) / subrepo_path)
        else:
            self.subrepo_path = None
            
        # Store file_path as absolute path
        if file_path:
            if self.subrepo_path:
                self.file_path = str(Path(self.subrepo_path) / file_path)
            else:
                self.file_path = str(Path(self.repo_path) / file_path)
        else:
            self.file_path = None
        
        # Verify the repository path exists
        if not os.path.exists(self.repo_path):
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
            
        # Use existing repository
        self.repo = Repo(self.repo_path)
        
        # Fetch latest changes from remote master branch
        try:
            print(f"{PENDING_ICON} UPDATING REPOSITORY")
            origin = self.repo.remote(name='origin')
            origin.fetch('master')
            
            # Checkout master branch if it exists locally
            if 'master' in [b.name for b in self.repo.branches]:
                print(f"Checking out local master branch...")
                self.repo.git.checkout('master')
            else:
                # If master branch doesn't exist locally, create it tracking the remote
                print(f"Creating local master branch tracking remote...")
                self.repo.git.checkout('-b', 'master', 'origin/master')
            
            # Pull latest changes from remote
            print(f"Pulling latest changes from remote master...")
            origin.pull('master')
            print(f"Successfully updated repository with latest changes.")
            print(f"{'-'*60}")
        except Exception as e:
            print(f"{WARNING_ICON} Could not update repository with latest changes: {str(e)}")
            print(f"Continuing with existing repository state.")
            print(f"{'-'*60}")
            # Don't raise the exception, just continue with the current state
            
    def get_subrepo_path(self):
        """
        Get the full path to the subrepo directory
        
        Returns:
            Complete path to the subrepo directory (absolute path)
        """
        if self.subrepo_path:
            return self.subrepo_path
        else:
            return self.repo_path
    
    def read_file(self):
        """
        Read a file from the repository
        
        Returns:
            String content of the file
        """
        full_path = self.file_path
        with open(full_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def write_file(self, content):
        """
        Write content to a file without committing
        
        Args:
            content: Content to write to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self.file_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            print(f"{ERROR_ICON} FILE WRITE ERROR")
            print(f"Details: {str(e)}")
            return False
    
    def create_branch(self, branch_name, base_branch="master"):
        """
        Create a new branch from base_branch and switch to it
        
        Args:
            branch_name: Name of the new branch
            base_branch: Base branch to create from (default: "master")
            
        Returns:
            Name of the created branch
        """
        # We already fetched and pulled the latest changes in __init__
        # Just make sure we're on the base branch
        if base_branch in [b.name for b in self.repo.branches]:
            self.repo.git.checkout(base_branch)
        else:
            # This should rarely happen since we already tried to set up master in __init__
            print(f"{WARNING_ICON} Base branch {base_branch} not found locally")
            print(f"Creating it now from origin/{base_branch}")
            self.repo.git.checkout('-b', base_branch, f'origin/{base_branch}')
        
        # Check if branch already exists
        if branch_name in [b.name for b in self.repo.branches]:
            # If it exists, just check it out
            branch = self.repo.branches[branch_name]
        else:
            # Create new branch from updated base_branch
            branch = self.repo.create_head(branch_name)
        
        branch.checkout()
        return branch.name
    
    def commit_changes(self, content, commit_message):
        """
        Write changes to a file and commit them
        
        Args:
            content: New content to write to the file
            commit_message: Commit message
            
        Returns:
            The commit object
        """
        try:
            # Ensure we have a file path set
            if self.file_path is None:
                raise ValueError("No default file path set in the constructor")
                
            # Ensure git user is configured
            try:
                # Check if user.name is configured
                self.repo.git.config('--get', 'user.name')
            except Exception:
                # Set a temporary user.name
                print(f"Setting temporary git user.name: 'LLM Migration Tool'")
                self.repo.git.config('--local', 'user.name', 'LLM Migration Tool')
                
            try:
                # Check if user.email is configured
                self.repo.git.config('--get', 'user.email')
            except Exception:
                # Set a temporary user.email
                print(f"Setting temporary git user.email: 'llm.migration@example.com'")
                self.repo.git.config('--local', 'user.email', 'llm.migration@example.com')
            
            # Use the file path directly
            full_path = self.file_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write the content to the file
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            # Add the file to git index
            print(f"{PENDING_ICON} COMMITTING CHANGES")
            print(f"Adding file to git: {self.file_path}")
            self.repo.git.add(self.file_path)
            
            # Commit the changes using git.commit() instead of index.commit()
            print(f"Committing with message: {commit_message}")
            self.repo.git.commit('-m', commit_message)
            
            # Get the commit object for the latest commit
            commit = self.repo.head.commit
            print(f"{SUCCESS_ICON} Commit successful")
            print(f"Commit hash: {commit.hexsha}")
            
            return commit
            
        except Exception as e:
            print(f"{ERROR_ICON} COMMIT FAILED")
            print(f"Error details: {str(e)}")
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
            print(f"{PENDING_ICON} DELETING LOCAL BRANCH")
            print(f"Branch name: {branch_name}")
            self.repo.git.branch('-D', branch_name)
            print(f"{SUCCESS_ICON} Branch deleted successfully")
            return True
        except Exception as e:
            print(f"{ERROR_ICON} BRANCH DELETION FAILED")
            print(f"Error deleting branch {branch_name}: {str(e)}")
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
            print(f"{PENDING_ICON} DELETING REMOTE BRANCH")
            print(f"Branch name: {branch_name}")
            # The syntax for deleting a remote branch is to push an empty reference
            result = origin.push(f":{branch_name}")
            print(f"{SUCCESS_ICON} Remote branch deleted successfully")
            return True
        except Exception as e:
            print(f"{ERROR_ICON} REMOTE BRANCH DELETION FAILED")
            print(f"Error deleting branch {branch_name}: {str(e)}")
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