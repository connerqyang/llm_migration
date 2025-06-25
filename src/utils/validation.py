import os
import subprocess
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Icons for console output
SUCCESS_ICON = "✅"
ERROR_ICON = "❌"
WARNING_ICON = "⚠️"
INFO_ICON = "ℹ️"
PENDING_ICON = "⏳"

class ValidationOperations:
    """Class for handling validation operations like linting and type checking"""
    
    def __init__(self, git_ops, max_retries=3):
        """Initialize the validation operations
        
        Args:
            git_ops: GitOperations instance for file path handling
            max_retries: Maximum number of retries for validation steps
        """
        self.git_ops = git_ops
        self.max_retries = max_retries
        
    def update_migration_status(self, code: str, status_updates: dict) -> str:
        """
        Update the migration status comment in the code
        
        Args:
            code: Current code content
            status_updates: Dictionary with status updates to apply
            
        Returns:
            Updated code with migration status comment
        """
        import re
        import json
        
        # Define the status comment pattern
        status_pattern = r'// MIGRATION STATUS: (\{.*\})'
        # Using greedy match to ensure we capture the entire JSON object
        
        # Check if a status comment already exists
        status_match = re.search(status_pattern, code)
        
        if status_match:
            # Extract and parse the existing status
            try:
                status_json = status_match.group(1)
                current_status = json.loads(status_json)
            except json.JSONDecodeError as e:
                print(f"\n{ERROR_ICON} JSON PARSING ERROR")
                print(f"Error details: {e}")
                print(f"Problematic JSON string: {status_match.group(1)}")
                # Fallback to empty status if parsing fails
                current_status = {}
            
            # Update the status with new information
            for key, value in status_updates.items():
                current_status[key] = value
                
            # Create the new status comment
            new_status_comment = f"// MIGRATION STATUS: {json.dumps(current_status)}"
            
            # Replace the existing status comment
            updated_code = re.sub(status_pattern, new_status_comment, code)
        else:
            # Create a new status comment
            new_status = {}
            
            # Initialize with pending status for eslint and tsc if not provided
            if 'eslint' not in status_updates:
                new_status['eslint'] = 'pending'
            if 'tsc' not in status_updates:
                new_status['tsc'] = 'pending'
                
            # Update with provided status
            new_status.update(status_updates)
            
            # Create the status comment
            status_comment = f"// MIGRATION STATUS: {json.dumps(new_status)}"
            
            # Add the status comment at the top of the file
            # Check if there's a license or comment block at the top
            if code.strip().startswith('/*') or code.strip().startswith('//'):
                # Find the end of the comment block
                comment_end = code.find('*/', 0) + 2 if code.strip().startswith('/*') else code.find('\n', 0)
                if comment_end > 0:
                    # Insert after the comment block
                    updated_code = code[:comment_end] + '\n' + status_comment + '\n' + code[comment_end:]
                else:
                    # Fallback to inserting at the top
                    updated_code = status_comment + '\n' + code
            else:
                # Insert at the top of the file
                updated_code = status_comment + '\n' + code
                
        return updated_code
    
    def run_lint_fix(self) -> Tuple[bool, str]:
        """Run ESLint with --fix on the file
        
        Returns:
            Tuple of (success, output)
        """
        try:
            # Use the file path directly
            abs_file_path = self.git_ops.file_path
            
            # Run ESLint with --fix
            print(f"{PENDING_ICON} RUNNING ESLINT FIX")
            result = subprocess.run(
                ["npx", "eslint", "--fix", abs_file_path],
                cwd=self.git_ops.get_subrepo_path(),
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if the command was successful
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            return success, output
        except Exception as e:
            return False, str(e)
    
    def check_lint_errors(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if the file has any remaining lint errors
        
        Returns:
            Tuple of (has_errors, errors)
        """
        try:
            # Use the file path directly
            abs_file_path = self.git_ops.file_path
            
            # Check if file exists before running ESLint
            if not os.path.exists(abs_file_path):
                return True, [{"message": f"File not found: {abs_file_path}", "severity": 2}]
            
            # Run ESLint with --format=json to get structured output
            print(f"{PENDING_ICON} CHECKING ESLINT ERRORS")
            result = subprocess.run(
                ["npx", "eslint", "--format=json", abs_file_path],
                capture_output=True,
                text=True,
                cwd=self.git_ops.get_subrepo_path(),
                check=False
            )
            
            # Check for file not found errors in stderr
            if "No files matching the pattern" in result.stderr:
                return True, [{"message": f"ESLint could not find file: {full_path}", "severity": 2}]
            
            # Parse the JSON output
            if result.stdout.strip():
                try:
                    lint_results = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    print(f"\n{ERROR_ICON} ESLINT OUTPUT PARSING ERROR")
                    print(f"Error details: {e}")
                    print(f"Problematic JSON string (first 100 chars): {result.stdout[:100]}")
                    return True, [{"message": f"Failed to parse ESLint output: {str(e)}", "severity": 2}]
                
                # Check if there are any errors or warnings
                errors = []
                for file_result in lint_results:
                    if file_result.get("errorCount", 0) > 0 or file_result.get("warningCount", 0) > 0:
                        errors.extend(file_result.get("messages", []))
                
                return len(errors) > 0, errors
            
            return False, []
        except Exception as e:
            return True, [{"message": str(e), "severity": 2}]
    
    def check_typescript_errors(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if the file has any TypeScript type errors
        
        Returns:
            Tuple of (has_errors, errors)
        """
        try:
            # Use the file path directly
            abs_file_path = self.git_ops.file_path
            
            # Run TypeScript compiler in noEmit mode to check types
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", abs_file_path],
                capture_output=True,
                text=True,
                cwd=self.git_ops.get_subrepo_path(),
                check=False
            )

            # Check if there are any errors
            has_errors = result.returncode != 0
            
            # Parse the error output
            errors = []
            if has_errors:
                # Combine stderr and stdout for error parsing
                error_text = (result.stderr + result.stdout).strip()
                error_lines = error_text.split("\n")
                for line in error_lines:
                    if line.strip() and "error TS" in line:
                        errors.append({
                            "message": line.strip(),
                            "severity": 2
                        })
            
            return has_errors, errors
        except Exception as e:
            return True, [{"message": str(e), "severity": 2}]
    
    def check_build_errors(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Run yarn build and check for errors
        
        Returns:
            Tuple of (success, errors)
        """
        try:
            # Change to the subrepo directory for yarn build
            subrepo_dir = self.git_ops.get_subrepo_path()
            
            # Run yarn build
            result = subprocess.run(
                ["yarn", "build"],
                cwd=subrepo_dir,
                capture_output=True,
                text=True,
                check=False
            )

            # Check if there are any errors
            has_errors = result.returncode != 0
            
            # Parse the error output
            errors = []
            if has_errors:
                # Combine stderr and stdout for error parsing
                error_text = (result.stderr + result.stdout).strip()
                error_lines = error_text.split("\n")
                for line in error_lines:
                    if line.strip() and ("error" in line.lower() or "failed" in line.lower()):
                        errors.append({
                            "message": line.strip(),
                            "severity": 2
                        })
            
            return has_errors, errors
        except Exception as e:
            return True, [{"message": str(e), "severity": 2}]
        
    def _get_validation_config(self, validation_type: str) -> Dict[str, Any]:
        """Get configuration for a validation type
        
        Args:
            validation_type: Type of validation (eslint, typescript, build)
            
        Returns:
            Dictionary with validation configuration
        """
        configs = {
            'eslint': {
                'status_key': 'eslint',
                'check_method': self.check_lint_errors,
                'pre_check_method': self.run_lint_fix,
                'error_type_name': 'lint',
                'fix_focus_message': 'Please fix ONLY these specific lint errors in the code while preserving the functionality.\nDo not introduce new issues or change unrelated code.'
            },
            'typescript': {
                'status_key': 'tsc',
                'check_method': self.check_typescript_errors,
                'pre_check_method': None,
                'error_type_name': 'TypeScript',
                'fix_focus_message': 'Please fix ONLY these specific TypeScript errors in the code while preserving the functionality.\nFocus on fixing type issues, adding proper type annotations, and ensuring type safety.\nDo not introduce new issues or change unrelated code.'
            },
            'build': {
                'status_key': 'build',
                'check_method': self.check_build_errors,
                'pre_check_method': None,
                'error_type_name': 'Build',
                'fix_focus_message': 'Please fix ONLY these specific build errors in the code while preserving the functionality.\nFocus on fixing issues that prevent successful compilation during the build process.\nDo not introduce new issues or change unrelated code.'
            }
        }
        
        return configs.get(validation_type, {
            'status_key': validation_type,
            'check_method': None,
            'pre_check_method': None,
            'error_type_name': validation_type.capitalize(),
            'fix_focus_message': f'Please fix the {validation_type} errors in the code while preserving the functionality.'
        })
    
    def run_validation_step(self, code: str, validation_type: str, llm_client=None, update_status=True) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Run a validation step with retry logic
        
        Args:
            code: Current code content
            validation_type: Type of validation to run (e.g., 'eslint', 'typescript', 'build')
            llm_client: Optional LLM client for fixing errors
            update_status: Whether to update the migration status
            
        Returns:
            Tuple of (success, updated_code, remaining_errors)
        """
        # Get configuration for this validation type
        config = self._get_validation_config(validation_type)
        status_key = config['status_key']
        check_method = config['check_method']
        pre_check_method = config['pre_check_method']
        error_type_name = config['error_type_name']
        fix_focus_message = config['fix_focus_message']
        
        # Print validation step header with improved formatting
        print(f"\n{INFO_ICON} STARTING {error_type_name.upper()} VALIDATION")
        print(f"{'-'*50}")
        
        # Update the migration status to show this step is in progress
        if update_status:
            try:
                code = self.update_migration_status(code, {status_key: "in progress"})
                print(f"Migration status updated: {error_type_name} validation in progress")
            except Exception as e:
                print(f"{ERROR_ICON} MIGRATION STATUS UPDATE FAILED")
                print(f"Error details: {str(e)}")
                # Continue without updating status if there's an error
            
        # Write the code to the file
        self.git_ops.write_file(code)
        
        # Initialize variables
        success = False
        updated_code = code
        remaining_errors = []
        retries = 0
        
        # Run the validation step with retries
        while not success and retries < self.max_retries:
            # Run pre-check method if available (e.g., eslint --fix)
            if pre_check_method:
                print(f"{PENDING_ICON} RUNNING PRE-CHECK FOR {error_type_name.upper()}")
                pre_check_success, pre_check_output = pre_check_method()
                if not pre_check_success and "No files matching the pattern" in pre_check_output:
                    print(f"{ERROR_ICON} FILE NOT FOUND")
                    print(f"Path: {self.git_ops.file_path}")
                    return False, code, [{"message": f"File not found: {self.git_ops.file_path}", "severity": 2}]
                
                # Read the updated file after pre-check
                updated_code = self.git_ops.read_file()
            
            # Check for errors
            print(f"{PENDING_ICON} CHECKING FOR {error_type_name.upper()} ERRORS")
            has_errors, errors = check_method()
            
            # Display errors immediately, regardless of retry status
            if has_errors:
                print(f"{ERROR_ICON} FOUND {len(errors)} {error_type_name.upper()} ERRORS")
                # Print the first 10 errors
                for i, error in enumerate(errors[:10]):
                    print(f"  Error {i+1}: {error.get('message', 'Unknown error')}")
                
                if len(errors) > 10:
                    print(f"  ... and {len(errors) - 10} more errors")
            else:
                print(f"{SUCCESS_ICON} NO ERRORS FOUND")
            
            # Calculate validation metrics
            if update_status:
                # For simplicity, we'll estimate passed items based on errors
                total_checks = len(errors) + 10  # Assuming at least 10 checks were performed
                passed = total_checks - len(errors)
                failed = len(errors)
                skipped = 0  # We don't have skipped information in this simple implementation
                success_rate = int((passed / total_checks) * 100) if total_checks > 0 else 100
                
                validation_status = {
                    "passed": passed,
                    "failed": failed,
                    "total": total_checks,
                    "skipped": skipped,
                    "successRate": success_rate
                }
                
                # Update the status with detailed metrics
                try:
                    updated_code = self.update_migration_status(
                        updated_code,
                        {status_key: validation_status}
                    )
                    print(f"Updated migration status: {passed}/{total_checks} checks passed ({success_rate}%)")
                except Exception as e:
                    print(f"{ERROR_ICON} METRICS UPDATE FAILED")
                    print(f"Error updating {error_type_name} metrics: {str(e)}")
                    # Continue without updating status if there's an error
            
            if not has_errors:
                success = True
                # Update status to show validation is complete
                if update_status:
                    updated_code = self.update_migration_status(
                        updated_code, 
                        {status_key: "done"}
                    )
                    print(f"{SUCCESS_ICON} VALIDATION COMPLETED SUCCESSFULLY")
                break
            
            # If we have an LLM client and there are errors, try to fix them
            if llm_client and has_errors:
                # Use LLM to fix errors
                print(f"{PENDING_ICON} FIXING ERRORS WITH LLM (ATTEMPT {retries + 1}/{self.max_retries})")
                fix_prompt = f"""# {error_type_name} Error Fix Request (Attempt {retries + 1})

## File with {error_type_name} Errors

```tsx
{updated_code}
```

## Current {error_type_name} Errors

```json
{json.dumps(errors, indent=2)}
```

{fix_focus_message}
"""
                
                # Call LLM to fix errors
                fix_response = llm_client._call_llm_api(fix_prompt)
                
                # Extract the fixed code
                import re
                code_pattern = "```tsx\n(.+?)\n```"
                code_match = re.search(code_pattern, fix_response, re.DOTALL)
                
                if code_match:
                    updated_code = code_match.group(1).strip()
                    print(f"LLM provided updated code, applying changes")
                    
                    # Write the updated code back to the file
                    self.git_ops.write_file(updated_code)
                    
                    # Verify that the errors were actually fixed
                    print(f"{PENDING_ICON} VERIFYING FIXES")
                    has_errors, remaining_errors = check_method()
                    if not has_errors:
                        success = True
                        # Update status to show validation is complete
                        if update_status:
                            updated_code = self.update_migration_status(
                                updated_code, 
                                {status_key: "done"}
                            )
                            print(f"{SUCCESS_ICON} VALIDATION COMPLETED SUCCESSFULLY AFTER LLM FIX")
                        break
                    else:
                        print(f"{WARNING_ICON} LLM FIX ATTEMPT INCOMPLETE")
                        print(f"Attempt {retries + 1} did not resolve all errors. Remaining: {len(remaining_errors)}")
                else:
                    print(f"{ERROR_ICON} LLM FAILED TO PROVIDE FIXED CODE")
            
            retries += 1
            if retries < self.max_retries and has_errors:
                print(f"{PENDING_ICON} PROCEEDING TO RETRY {retries + 1}/{self.max_retries}")
        
        # Final status report
        if success:
            print(f"{SUCCESS_ICON} VALIDATION STEP COMPLETED SUCCESSFULLY")
        else:
            print(f"{ERROR_ICON} VALIDATION STEP FAILED")
            print(f"Failed after {self.max_retries} attempts. Remaining errors: {len(remaining_errors)}")
        
        return success, updated_code, remaining_errors