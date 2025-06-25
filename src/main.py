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

def run_validation_pipeline(git_ops, llm_client, migrated_code, max_retries=3, steps=None):
    """
    Run the validation pipeline on the migrated code
    
    Args:
        git_ops: GitOperations instance (with file_path already set)
        llm_client: LLMClient instance
        migrated_code: The migrated code to validate
        max_retries: Maximum number of retries for validation steps
        steps: List of validation steps to run (e.g., ['fix-lint', 'fix-ts'])
              If None, all steps will be run in sequence
        
    Returns:
        Tuple of (success, final_code)
    """
    # Import icons from ValidationOperations
    from src.utils.validation import SUCCESS_ICON, ERROR_ICON, WARNING_ICON, INFO_ICON, PENDING_ICON
    
    # Initialize ValidationOperations
    validation_ops = ValidationOperations(git_ops=git_ops, max_retries=max_retries)
    
    # Write the migrated code to a temporary file for validation
    # Extract the base name and extension
    file_base, file_ext = os.path.splitext(git_ops.file_path)
    temp_file_path = f"{file_base}_temp{file_ext}"
    
    # Define the validation steps mapping
    validation_steps = {
        'fix-eslint': {'type': 'eslint', 'name': 'ESLint'},
        'fix-build': {'type': 'build', 'name': 'Build'},
        'fix-tsc': {'type': 'typescript', 'name': 'TypeScript'}
    }
    
    # If no specific steps are provided, run all steps in sequence
    if not steps:
        steps = ['fix-eslint', 'fix-build', 'fix-tsc']
    
    try:
        # Print a more visually appealing header
        print(f"\n{INFO_ICON} VALIDATION PIPELINE STARTED")
        print(f"{'-'*60}")
        print(f"File: {git_ops.file_path}")
        print(f"Steps to run: {', '.join(steps)}")
        print(f"{'-'*60}\n")
        
        updated_code = migrated_code
        
        # Initialize migration status comment
        # Set initial status for steps that will be run
        initial_status = {}
        for step in steps:
            if step == 'fix-eslint':
                initial_status['eslint'] = 'pending'
            elif step == 'fix-build':
                initial_status['build'] = 'pending'
            elif step == 'fix-tsc':
                initial_status['tsc'] = 'pending'
                
        # Add the initial status comment to the code
        if initial_status:
            updated_code = validation_ops.update_migration_status(updated_code, initial_status)
            print(f"Initialized migration status for validation steps")
        
        # Run each validation step in sequence
        total_steps = len(steps)
        current_step = 0
        
        for step in steps:
            current_step += 1
            if step not in validation_steps:
                print(f"{WARNING_ICON} UNKNOWN VALIDATION STEP")
                print(f"Step '{step}' not recognized. Skipping.")
                continue
                
            step_info = validation_steps[step]
            print(f"\nStep {current_step}/{total_steps}: {step_info['name']} Validation")
            print(f"{'-'*50}")
            
            step_success, updated_code, remaining_errors = validation_ops.run_validation_step(
                code=updated_code,
                validation_type=step_info['type'],
                llm_client=llm_client
            )
            
            if not step_success:
                print(f"\n{ERROR_ICON} VALIDATION STEP FAILED")
                print(f"{step_info['name']} validation failed after all attempts")
                return False, updated_code
            
            print(f"Step {current_step}/{total_steps} completed: {step_info['name']} validation passed successfully")
        
        # Print a visually appealing completion message
        print(f"\n{SUCCESS_ICON} VALIDATION PIPELINE COMPLETED SUCCESSFULLY")
        print(f"{'-'*60}")
        print(f"All {total_steps} validation steps passed!")
        print(f"{'-'*60}")
        return True, updated_code
    
    except json.JSONDecodeError as e:
        print(f"\n{ERROR_ICON} JSON PARSING ERROR IN VALIDATION PIPELINE")
        print(f"{'-'*60}")
        print(f"Error details: {str(e)}")
        print(f"This error occurred while trying to parse JSON data.")
        print(f"Check the format of status comments or LLM responses.")
        print(f"{'-'*60}")
        return False, migrated_code
    except Exception as e:
        print(f"\n{ERROR_ICON} ERROR IN VALIDATION PIPELINE")
        print(f"{'-'*60}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        print(f"{'-'*60}")
        return False, migrated_code
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"Temporary file cleaned up")
        except Exception as e:
            print(f"{WARNING_ICON} TEMPORARY FILE CLEANUP FAILED")
            print(f"Error: {str(e)}")

def migrate_component(component_name, file_path, max_retries=3, steps=None, subrepo_path=""):
    """Migrate a component in the specified file using the LLM client
    
    Args:
        component_name: Name of the component to migrate (must be supported)
        file_path: Path to the file containing the component relative to subrepo_path
        max_retries: Maximum number of retries for validation steps
        steps: List of validation steps to run (e.g., ['fix-lint', 'fix-ts'])
              If None, all steps will be run in sequence
        subrepo_path: Subrepository path relative to LOCAL_REPO_PATH from .env
        
    Returns:
        True if successful, False otherwise
    """
    # Import icons from ValidationOperations
    from src.utils.validation import SUCCESS_ICON, ERROR_ICON, WARNING_ICON, INFO_ICON, PENDING_ICON
    
    git_ops = None
    test_branch = None
    commit = None
    
    try:
        # Import icons from ValidationOperations
        from src.utils.validation import SUCCESS_ICON, ERROR_ICON, WARNING_ICON, INFO_ICON, PENDING_ICON
        
        print(f"{INFO_ICON} INITIALIZING COMPONENT MIGRATION")
        print(f"{'-'*60}")
        print(f"Component: {component_name}")
        
        # Initialize GitOperations for file access
        repo_path = os.getenv("LOCAL_REPO_PATH")
        print(f"Repository: {repo_path}")
        print(f"Subrepo: {subrepo_path if subrepo_path else 'None'}")
        
        # Check if the repository path exists
        if not os.path.exists(repo_path):
            print(f"{ERROR_ICON} REPOSITORY PATH NOT FOUND")
            print(f"Path: {repo_path}")
            return False
            
        # Check if the subrepo path exists if provided
        if subrepo_path and not os.path.exists(os.path.join(repo_path, subrepo_path)):
            print(f"{ERROR_ICON} SUBREPOSITORY PATH NOT FOUND")
            print(f"Path: {os.path.join(repo_path, subrepo_path)}")
            print(f"Please check that the subrepo-path '{subrepo_path}' is correct and exists within {repo_path}")
            return False
            
        git_ops = GitOperations(repo_path=repo_path, subrepo_path=subrepo_path, file_path=file_path)
        print(f"Repository initialized successfully")
        
        # Show the full path that will be used
        full_path = git_ops.file_path
        print(f"Full file path: {full_path}")
        print(f"{'-'*60}")
        
        # Read the file
        print(f"{PENDING_ICON} READING SOURCE FILE")
        try:
            original_content = git_ops.read_file()
            print(f"Successfully read file: {file_path}")
            print(f"Original file content (first 100 chars): {original_content[:100]}...")
        except Exception as e:
            print(f"{ERROR_ICON} FILE READ ERROR")
            print(f"Error details: {str(e)}")
            return False
        
        # Initialize LLM client
        print(f"{PENDING_ICON} INITIALIZING MIGRATION")
        llm_client = LLMClient()
        migration_result = llm_client.migrate_component(component_name, original_content)
        
        # Print migration results
        print(f"\n{SUCCESS_ICON} MIGRATION COMPLETE")
        print(f"{'-'*60}")
        print(f"=== Migrated Code ===\n")
        print(f"{migration_result['migrated_code']}")
        print(f"\n=== Migration Notes ===\n")
        print(f"{migration_result['migration_notes']}")
        print(f"{'-'*60}")
        
        # Run validation pipeline if there's migrated code
        final_code = migration_result["migrated_code"]
        validation_success = False
        
        if final_code:
            validation_success, validated_code = run_validation_pipeline(
                git_ops, 
                llm_client, 
                final_code,
                max_retries=max_retries,
                steps=steps
            )
            
            if validation_success:
                final_code = validated_code
                print(f"\n{SUCCESS_ICON} FINAL VALIDATED CODE")
                print(f"{'-'*60}")
                print(f"{final_code}")
                
                # Ensure the migration status shows completion for all steps
                final_status = {}
                for step in steps:
                    if step == 'fix-eslint':
                        final_status['eslint'] = 'done'
                    elif step == 'fix-build':
                        final_status['build'] = 'done'
                    elif step == 'fix-tsc':
                        final_status['tsc'] = 'done'
                        
                # Update the final status in the code
                if final_status:
                    validation_ops = ValidationOperations(git_ops=git_ops, max_retries=max_retries)
                    final_code = validation_ops.update_migration_status(final_code, final_status)
            else:
                print(f"\n{WARNING_ICON} VALIDATION FAILED")
                print(f"{'-'*60}")
                print(f"Migration will proceed despite validation failures.")
                print(f"{'-'*60}")
                # Use the migrated code even though validation failed
                final_code = migration_result["migrated_code"]
        
        # Prompt user whether to commit changes (regardless of validation success)
        if final_code and input(f"\n{INFO_ICON} COMMIT CHANGES? (y/n): ").lower() == 'y':
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
            
            # Add validation status to branch name
            validation_status = "validated" if validation_success else "unvalidated"
            test_branch = f"migration/{component_name}-{file_name}-{validation_status}-{timestamp}"
            
            # Create the branch BEFORE making any changes
            print(f"{PENDING_ICON} GIT OPERATIONS")
            print(f"{'-'*60}")
            print(f"Creating branch: {test_branch}")
            branch_name = git_ops.create_branch(test_branch)
            print(f"Created and checked out branch: {branch_name}")
            
            print(f"Committing changes to: {file_path}")
            validation_message = "(validated)" if validation_success else "(unvalidated)"
            commit = git_ops.commit_changes(
                final_code, 
                f"Migrate {component_name} component in {file_path} {validation_message}"
            )
            print(f"Committed changes with hash: {commit.hexsha}")
            
            # Push changes to remote
            print(f"Pushing branch {test_branch} to remote...")
            result = git_ops.push_changes(test_branch)
            print(f"Push result: {result}")
            print(f"{'-'*60}")
        
        return True
    except Exception as e:
        print(f"\n{ERROR_ICON} ERROR DURING MIGRATION")
        print(f"{'-'*60}")
        print(f"Error: {str(e)}")
        print(f"{'-'*60}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up the test branch if created and user wants to clean up
        if git_ops and test_branch and commit and test_branch in [b.name for b in git_ops.repo.branches] and input("Do you want to clean up the test branch? (y/n): ").lower() == 'y':
            print(f"\n{PENDING_ICON} CLEANUP OPERATIONS")
            cleanup_success = git_ops.cleanup_branch(test_branch)
            if cleanup_success:
                print(f"Successfully cleaned up branch: {test_branch}")
            else:
                print(f"{WARNING_ICON} Failed to clean up branch: {test_branch}")
            print(f"{'-'*60}")

def main():
    """
    Main entry point
    """
    # Import icons from ValidationOperations
    from src.utils.validation import SUCCESS_ICON, ERROR_ICON, WARNING_ICON, INFO_ICON, PENDING_ICON
    
    parser = argparse.ArgumentParser(description="LLM-based UI component migration tool")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Migrate component command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a UI component")
    
    # Initialize LLM client to get supported components
    print(f"{PENDING_ICON} INITIALIZING COMPONENTS LIST")
    try:
        llm_client = LLMClient()
        supported_components = llm_client.get_supported_components()
        print(f"Found {len(supported_components)} supported components")
    except Exception as e:
        print(f"{WARNING_ICON} Could not initialize LLM client to get supported components: {str(e)}")
        supported_components = ["TUXButton"]  # Fallback to hardcoded list
        print(f"Using fallback list of supported components: {supported_components}")
    print(f"{'-'*60}")
    
    migrate_parser.add_argument(
        "--component", 
        choices=supported_components,
        default="TUXButton" if "TUXButton" in supported_components else None,
        required="TUXButton" not in supported_components,
        help="Component to migrate"
    )
    migrate_parser.add_argument(
        "--subrepo-path",
        default="",
        help="Subrepository path relative to LOCAL_REPO_PATH from .env"
    )
    migrate_parser.add_argument(
        "--file-path", 
        default="packages/apps/tiktok_live_web/e-commerce/after-sale-collection/src/pages/Refund/containers/refunddetail-global/modules/ReturnShippingModule/index.tsx",
        help="Full path to the file containing the component (including any page directory)"
    )
    migrate_parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for validation steps"
    )
    migrate_parser.add_argument(
        "--step",
        nargs="*",
        choices=['fix-eslint', 'fix-build', 'fix-tsc'],
        default=None,
        help="Specific validation steps to run (e.g., fix-eslint fix-build fix-tsc). If not specified, all steps will run in sequence."
    )
    
    # List supported components command
    list_parser = subparsers.add_parser("list", help="List supported components for migration")
    
    args = parser.parse_args()
    
    # Default to migrate if no command is specified
    if not args.command:
        args.command = "migrate"
        args.component = "TUXButton"
        args.file_path = "src/pages/Refund/containers/refunddetail-global/modules/ReturnShippingModule/index.tsx"
        args.max_retries = 3
        args.subrepo_path = "packages/apps/tiktok_live_web/e-commerce/after-sale-collection"
        print(f"No command specified, defaulting to 'migrate' with TUXButton component")
    
    # Execute the appropriate command
    if args.command == "migrate":
        print(f"{INFO_ICON} STARTING COMPONENT MIGRATION {'='*25}")
        print(f"Component: {args.component}")
        print(f"File path: {args.file_path}")
        if args.subrepo_path:
            print(f"Subrepo path: {args.subrepo_path}")
        print(f"Max retries: {args.max_retries}")
        if args.step:
            print(f"Selected validation steps: {', '.join(args.step)}")
        else:
            print(f"Running all validation steps")
        print(f"{'-'*60}")
        
        success = migrate_component(
            component_name=args.component,
            file_path=args.file_path,
            max_retries=args.max_retries,
            steps=args.step,
            subrepo_path=args.subrepo_path
        )
        
        if success:
            print(f"\n{SUCCESS_ICON} MIGRATION COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            print(f"\n{ERROR_ICON} MIGRATION FAILED")
            sys.exit(1)
    
    elif args.command == "list":
        print(f"\n{INFO_ICON} SUPPORTED COMPONENTS FOR MIGRATION {'='*20}")
        for component in supported_components:
            print(f"- {component}")
        print(f"Total: {len(supported_components)} components")
        print(f"{'-'*60}")
        sys.exit(0)

if __name__ == "__main__":
    main()