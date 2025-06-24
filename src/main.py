import os
import sys
import json
import argparse
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.git_operations import GitOperations
from src.utils.llm_client import LLMClient
from src.utils.validation import ValidationOperations
from tests.test_git_operations import test_git_operations

def run_validation_pipeline(git_ops, llm_client, file_path, migrated_code, max_retries=3):
    """
    Run the validation pipeline on the migrated code
    
    Args:
        git_ops: GitOperations instance
        llm_client: LLMClient instance
        file_path: Path to the file being migrated
        migrated_code: The migrated code to validate
        max_retries: Maximum number of retries for validation steps
        
    Returns:
        Tuple of (success, final_code)
    """
    # Initialize ValidationOperations
    validation_ops = ValidationOperations(git_ops=git_ops, max_retries=max_retries)
    
    # Write the migrated code to a temporary file for validation
    # Extract the base name and extension
    file_base, file_ext = os.path.splitext(file_path)
    temp_file_path = f"{file_base}_temp{file_ext}"
    
    try:
        print(f"\n=== Running Validation Pipeline ===\n")
        
        # Run the lint validation step
        print("Running lint validation...")
        lint_success, updated_code, remaining_errors = validation_ops.run_validation_step(
            file_path=temp_file_path,
            code=migrated_code,
            validation_type='lint',
            llm_client=llm_client
        )
        
        if not lint_success:
            print("Lint validation failed:")
            for error in remaining_errors[:5]:  # Show first 5 errors
                print(f"- {error.get('message', 'Unknown error')}")
            
            if len(remaining_errors) > 5:
                print(f"... and {len(remaining_errors) - 5} more")
            
            print("Validation pipeline cannot continue.")
            return False, updated_code
        
        print("Lint validation passed successfully!")
        
        # TypeScript validation is commented out for now
        # print("\nRunning TypeScript validation...")
        # ts_success, updated_code, remaining_errors = validation_ops.run_validation_step(
        #     file_path=temp_file_path,
        #     code=updated_code,
        #     validation_type='typescript',
        #     llm_client=llm_client
        # )
        # 
        # if not ts_success:
        #     print("TypeScript validation failed:")
        #     for error in remaining_errors[:5]:  # Show first 5 errors
        #         print(f"- {error.get('message', 'Unknown error')}")
        #     
        #     if len(remaining_errors) > 5:
        #         print(f"... and {len(remaining_errors) - 5} more")
        #     
        #     print("Validation pipeline cannot continue.")
        #     return False, updated_code
        # 
        # print("TypeScript validation passed successfully!")
        
        print("\n=== Validation Pipeline Complete ===\n")
        print("All validation steps passed successfully!")
        return True, updated_code
    
    except Exception as e:
        print(f"Error in validation pipeline: {str(e)}")
        return False, migrated_code
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(git_ops.get_absolute_path(temp_file_path)):
                os.remove(git_ops.get_absolute_path(temp_file_path))
        except Exception as e:
            print(f"Warning: Failed to clean up temporary file: {str(e)}")

def migrate_component(component_name, file_path, max_retries=3):
    """
    Migrate a component in the specified file using the LLM client
    
    Args:
        component_name: Name of the component to migrate (must be supported)
        file_path: Full path to the file containing the component (including any page directory)
        max_retries: Maximum number of retries for validation steps
        
    Returns:
        True if successful, False otherwise
    """
    git_ops = None
    test_branch = None
    commit = None
    
    try:
        print(f"Initializing component migration for {component_name}...")
        
        # Initialize GitOperations for file access
        git_ops = GitOperations()
        print(f"Repository initialized at: {git_ops.repo_path}")
        
        # Show the full path that will be used
        full_path = git_ops.get_absolute_path(file_path)
        print(f"Full file path: {full_path}")
        
        # Read the file
        print(f"Reading file: {file_path}")
        try:
            original_content = git_ops.read_file(file_path)
            print(f"Successfully read file: {file_path}")
            print(f"Original file content (first 100 chars): {original_content[:100]}...")
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return False
        
        # Initialize LLM client
        print("Initializing LLM client...")
        llm_client = LLMClient()
        
        # Migrate the component
        print(f"Migrating {component_name} component...")
        migration_result = llm_client.migrate_component(component_name, original_content)
        
        # Print migration results
        print("\n=== Migration Complete ===\n")
        print("=== Migrated Code ===\n")
        print(migration_result["migrated_code"])
        print("\n=== Migration Notes ===\n")
        print(migration_result["migration_notes"])
        
        # Run validation pipeline if there's migrated code
        final_code = migration_result["migrated_code"]
        validation_success = False
        
        if final_code:
            validation_success, validated_code = run_validation_pipeline(
                git_ops, 
                llm_client, 
                file_path, 
                final_code,
                max_retries=max_retries
            )
            
            if validation_success:
                final_code = validated_code
                print("\n=== Final Validated Code ===\n")
                print(final_code)
            else:
                print("\n=== Validation Failed ===\n")
                print("Migration cannot proceed due to validation failures.")
                return False
        
        # Prompt user whether to commit changes only if validation was successful
        if validation_success and final_code and input("\nDo you want to commit these changes? (y/n): ").lower() == 'y':
            # Create a test branch for committing changes
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # Extract component folder name for branch name
            file_basename = os.path.basename(file_path)
            if file_basename == "index.tsx" or file_basename == "index.ts":
                # Use parent folder name for index files
                parent_dir = os.path.basename(os.path.dirname(file_path))
                file_name = parent_dir
            else:
                # Use file name without extension for other files
                file_name = file_basename.split('.')[0]
            test_branch = f"migration/{component_name}-{file_name}-{timestamp}"
            
            # Create the branch BEFORE making any changes
            print(f"Creating branch: {test_branch}")
            branch_name = git_ops.create_branch(test_branch)
            print(f"Created and checked out branch: {branch_name}")
            
            print(f"\nCommitting changes to: {file_path}")
            commit = git_ops.commit_changes(
                file_path, 
                final_code, 
                f"Migrate {component_name} component in {file_path}"
            )
            print(f"Committed changes with hash: {commit.hexsha}")
            
            # Push changes to remote
            print(f"Pushing branch {test_branch} to remote...")
            result = git_ops.push_changes(test_branch)
            print(f"Push result: {result}")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    finally:
        # Clean up the test branch if created and user wants to clean up
        if git_ops and test_branch and commit and test_branch in [b.name for b in git_ops.repo.branches] and input("Do you want to clean up the test branch? (y/n): ").lower() == 'y':
            print("\nCleaning up test resources...")
            cleanup_success = git_ops.cleanup_branch(test_branch)
            if cleanup_success:
                print(f"Successfully cleaned up branch: {test_branch}")
            else:
                print(f"Warning: Failed to clean up branch: {test_branch}")

def main():
    """
    Main entry point
    """
    parser = argparse.ArgumentParser(description="LLM-based UI component migration tool")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Test git operations command
    git_parser = subparsers.add_parser("test-git", help="Test Git operations with modular path building")
    git_parser.add_argument(
        "--file-path", 
        default="modules/ReturnShippingModule/index.tsx",
        help="Full path to the file to modify (including any page directory)"
    )
    
    # Migrate component command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a UI component")
    
    # Initialize LLM client to get supported components
    try:
        llm_client = LLMClient()
        supported_components = llm_client.get_supported_components()
    except Exception as e:
        print(f"Warning: Could not initialize LLM client to get supported components: {str(e)}")
        supported_components = ["TUXButton"]  # Fallback to hardcoded list
    
    migrate_parser.add_argument(
        "--component", 
        choices=supported_components,
        default="TUXButton" if "TUXButton" in supported_components else None,
        required="TUXButton" not in supported_components,
        help="Component to migrate"
    )
    migrate_parser.add_argument(
        "--file-path", 
        default="modules/ReturnShippingModule/index.tsx",
        help="Full path to the file containing the component (including any page directory)"
    )
    migrate_parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for validation steps"
    )
    
    # List supported components command
    list_parser = subparsers.add_parser("list", help="List supported components for migration")
    
    args = parser.parse_args()
    
    # Default to migrate if no command is specified
    if not args.command:
        args.command = "migrate"
        args.component = "TUXButton"
        args.file_path = "packages/apps/tiktok_live_web/e-commerce/after-sale-collection/src/pages/Refund/containers/refunddetail-global/modules/ReturnShippingModule/index.tsx"
        args.max_retries = 3
    
    # Execute the appropriate command
    if args.command == "test-git":
        print("Testing Git operations...")
        success = test_git_operations(
            file_path=args.file_path
        )
        
        if success:
            print("Git operations test completed successfully!")
        else:
            print("Git operations test failed!")
            sys.exit(1)
    
    elif args.command == "migrate":
        print(f"Migrating {args.component} component in {args.file_path}...")
        success = migrate_component(
            component_name=args.component,
            file_path=args.file_path,
            max_retries=args.max_retries
        )
        
        if success:
            print("Component migration completed successfully!")
        else:
            print("Component migration failed!")
            sys.exit(1)
    
    elif args.command == "list":
        try:
            llm_client = LLMClient()
            components = llm_client.get_supported_components()
            
            if components:
                print("Supported components for migration:")
                for component in components:
                    print(f"- {component}")
            else:
                print("No supported components found.")
                print("Add component migration guides to src/prompts/components/ directory.")
        except Exception as e:
            print(f"Error listing supported components: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()