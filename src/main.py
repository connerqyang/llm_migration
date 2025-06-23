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

def run_validation_pipeline(git_ops, llm_client, file_path, migrated_code):
    """
    Run the validation pipeline on the migrated code
    
    Args:
        git_ops: GitOperations instance
        llm_client: LLMClient instance
        file_path: Path to the file being migrated
        migrated_code: The migrated code to validate
        
    Returns:
        Tuple of (success, final_code)
    """
    # Initialize ValidationOperations
    validation_ops = ValidationOperations(repo_path=git_ops.repo_path)
    
    # Write the migrated code to a temporary file for validation
    temp_file_path = f"{file_path}.temp"
    try:
        git_ops.write_file(temp_file_path, migrated_code)
        print(f"\n=== Running Validation Pipeline ===\n")
        
        # Step 1: Run lint --fix
        print("Step 1: Running ESLint with --fix...")
        lint_fix_success, lint_fix_output = validation_ops.run_lint_fix(temp_file_path)
        if lint_fix_success:
            print("ESLint --fix completed successfully")
        else:
            print(f"ESLint --fix encountered issues: {lint_fix_output}")
            # Continue anyway as we'll check for remaining errors in the next step
        
        # Read the updated file after lint --fix
        updated_code = git_ops.read_file(temp_file_path)
        
        # Step 2: Check for remaining lint errors
        print("\nStep 2: Checking for remaining lint errors...")
        has_lint_errors, lint_errors = validation_ops.check_lint_errors(temp_file_path)
        
        if has_lint_errors:
            print(f"Found {len(lint_errors)} lint errors/warnings:")
            for error in lint_errors[:5]:  # Show first 5 errors
                print(f"- {error.get('message', 'Unknown error')}")
            
            if len(lint_errors) > 5:
                print(f"... and {len(lint_errors) - 5} more")
            
            # Use LLM to fix lint errors
            print("\nUsing LLM to fix lint errors...")
            lint_fix_prompt = f"""# Lint Error Fix Request

## File with Lint Errors

```tsx
{updated_code}
```

## Lint Errors

{json.dumps(lint_errors, indent=2)}

Please fix the lint errors in the code while preserving the functionality."""
            
            # Call LLM to fix lint errors
            lint_fix_response = llm_client._call_llm_api(lint_fix_prompt)
            
            # Extract the fixed code
            import re
            code_pattern = "```tsx\n(.+?)\n```"
            code_match = re.search(code_pattern, lint_fix_response, re.DOTALL)
            
            if code_match:
                updated_code = code_match.group(1).strip()
                print("LLM attempted to fix lint errors")
                
                # Write the updated code back to the temp file
                git_ops.write_file(temp_file_path, updated_code)
                
                # Verify that the lint errors were actually fixed
                still_has_errors, remaining_errors = validation_ops.check_lint_errors(temp_file_path)
                if still_has_errors:
                    print("LLM could not fix all lint errors. Validation failed.")
                    return False, updated_code
            else:
                print("LLM failed to provide fixed code")
                return False, updated_code
        else:
            print("No lint errors found")
        
        # Step 3: Check for TypeScript type issues
        print("\nStep 3: Checking for TypeScript type issues...")
        has_type_errors, type_errors = validation_ops.check_typescript_errors(temp_file_path)
        
        if has_type_errors:
            print(f"Found {len(type_errors)} TypeScript errors:")
            for error in type_errors[:5]:  # Show first 5 errors
                print(f"- {error.get('message', 'Unknown error')}")
            
            if len(type_errors) > 5:
                print(f"... and {len(type_errors) - 5} more")
            
            # Use LLM to fix type errors
            print("\nUsing LLM to fix TypeScript type errors...")
            type_fix_prompt = f"""# TypeScript Error Fix Request

## File with Type Errors

```tsx
{updated_code}
```

## TypeScript Errors

{json.dumps(type_errors, indent=2)}

Please fix the TypeScript type errors in the code while preserving the functionality."""
            
            # Call LLM to fix type errors
            type_fix_response = llm_client._call_llm_api(type_fix_prompt)
            
            # Extract the fixed code
            code_match = re.search(code_pattern, type_fix_response, re.DOTALL)
            
            if code_match:
                updated_code = code_match.group(1).strip()
                print("LLM attempted to fix type errors")
                
                # Write the updated code back to the temp file
                git_ops.write_file(temp_file_path, updated_code)
                
                # Verify that the type errors were actually fixed
                still_has_errors, remaining_errors = validation_ops.check_typescript_errors(temp_file_path)
                if still_has_errors:
                    print("LLM could not fix all TypeScript errors. Validation failed.")
                    return False, updated_code
            else:
                print("LLM failed to provide fixed code")
                return False, updated_code
        else:
            print("No TypeScript type errors found")
        
        print("\n=== Validation Pipeline Complete ===\n")
        print("All validation steps passed successfully!")
        return True, updated_code
    
    except Exception as e:
        print(f"Error in validation pipeline: {str(e)}")
        return False, migrated_code
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(git_ops.build_file_path(temp_file_path)):
                os.remove(git_ops.build_file_path(temp_file_path))
        except Exception as e:
            print(f"Warning: Failed to clean up temporary file: {str(e)}")

def migrate_component(component_name, file_path, page_path=None):
    """
    Migrate a component in the specified file using the LLM client
    
    Args:
        component_name: Name of the component to migrate (must be supported)
        file_path: Relative path to the file containing the component
        page_path: Optional page path to override the one in .env
        
    Returns:
        True if successful, False otherwise
    """
    git_ops = None
    test_branch = None
    commit = None
    
    try:
        print(f"Initializing component migration for {component_name}...")
        
        # Initialize GitOperations for file access
        git_ops = GitOperations(page_path=page_path)
        print(f"Repository initialized at: {git_ops.repo_path}")
        print(f"Page path: {git_ops.page_path}")
        
        # Show the full path that will be used
        full_path = git_ops.build_file_path(file_path)
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
                final_code
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
            test_branch = f"migration/{component_name.lower()}-{file_name}-{timestamp}"
            
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
        help="Relative path to the file to modify within the page directory"
    )
    git_parser.add_argument(
        "--page-path", 
        help="Page path to override the one in .env"
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
        help="Relative path to the file containing the component"
    )
    migrate_parser.add_argument(
        "--page-path", 
        help="Page path to override the one in .env"
    )
    
    # List supported components command
    list_parser = subparsers.add_parser("list", help="List supported components for migration")
    
    args = parser.parse_args()
    
    # Default to migrate if no command is specified
    if not args.command:
        args.command = "migrate"
        args.component = "TUXButton"
        args.file_path = "modules/ReturnShippingModule/index.tsx"
        args.page_path = None
    
    # Execute the appropriate command
    if args.command == "test-git":
        print("Testing Git operations...")
        success = test_git_operations(
            file_path=args.file_path,
            page_path=args.page_path
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
            page_path=args.page_path,
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