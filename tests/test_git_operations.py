import os
import sys
import argparse
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.git_operations import GitOperations

def test_git_operations(file_path="packages/apps/tiktok_live_web/e-commerce/after-sale-collection/src/pages/Refund/containers/refunddetail-global/modules/ReturnShippingModule/index.tsx"):
    """
    Test the GitOperations class functionality with modular path building
    by reading an existing file, modifying it, and pushing the changes
    
    Args:
        file_path: Full path to the file (including any page directory)
                  Default is 'modules/ReturnShippingModule/index.tsx'
        
    Returns:
        True if successful, False otherwise
    """
    git_ops = None
    test_branch = None
    
    try:
        print("Initializing GitOperations...")
        git_ops = GitOperations()
        print(f"Repository initialized at: {git_ops.repo_path}")
        
        # Create a test branch
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_branch = f"temp/git-{timestamp}"
        
        print(f"Creating branch: {test_branch}")
        branch_name = git_ops.create_branch(test_branch)
        print(f"Created and checked out branch: {branch_name}")
        
        # Show the full path that will be used
        full_path = git_ops.get_absolute_path(file_path)
        print(f"Full file path: {full_path}")
        
        # Read the existing file
        print(f"Reading file: {file_path}")
        try:
            original_content = git_ops.read_file(file_path)
            print(f"Successfully read file: {file_path}")
            print(f"Original file content (first 100 chars): {original_content[:100]}...")
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return False
        
        # Modify the content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        modified_content = f"// Modified by LLM Migration Tool at {timestamp}\n{original_content}"
        
        # Commit the changes
        print(f"Committing changes to: {file_path}")
        commit = git_ops.commit_changes(file_path, modified_content, f"Update {file_path} with timestamp")
        print(f"Committed changes with hash: {commit.hexsha}")
        
        # Read the file back to verify changes
        print(f"Reading updated file: {file_path}")
        updated_content = git_ops.read_file(file_path)
        print(f"Updated file content (first 100 chars): {updated_content[:100]}...")
        
        # Push changes to remote
        print(f"Pushing branch {test_branch} to remote...")
        result = git_ops.push_changes(test_branch)
        print(f"Push result: {result}")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    finally:
        # Clean up the test branch regardless of test outcome
        if git_ops and test_branch and input("Do you want to clean up the test branch? (y/n): ").lower() == 'y':
            print("\nCleaning up test resources...")
            cleanup_success = git_ops.cleanup_branch(test_branch)
            if cleanup_success:
                print(f"Successfully cleaned up branch: {test_branch}")
            else:
                print(f"Warning: Failed to clean up branch: {test_branch}")

# Allow running the test directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Git operations with modular path building")
    parser.add_argument(
        "--file-path", 
        default="modules/ReturnShippingModule/index.tsx",
        help="Full path to the file to modify (including any page directory)"
    )
    
    args = parser.parse_args()
    
    print("Testing Git operations...")
    success = test_git_operations(
        file_path=args.file_path
    )
    
    if success:
        print("Git operations test completed successfully!")
    else:
        print("Git operations test failed!")
        sys.exit(1)