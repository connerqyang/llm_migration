import os
import subprocess
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

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
        
    def update_migration_status(self, file_path: str, code: str, status_updates: dict) -> str:
        """
        Update the migration status comment in the code
        
        Args:
            file_path: Path to the file
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
                print(f"\nJSON parsing error in update_migration_status: {e}")
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
    
    def run_lint_fix(self, file_path: str) -> Tuple[bool, str]:
        """Run ESLint with --fix option on the specified file
        
        Args:
            file_path: Path to the file to lint
            
        Returns:
            Tuple of (success, output)
        """
        try:
            # Use git_ops to get the absolute path
            full_path = self.git_ops.get_absolute_path(file_path)
            
            # Run ESLint with --fix option
            result = subprocess.run(
                ["npx", "eslint", "--fix", full_path],
                capture_output=True,
                text=True,
                cwd=self.git_ops.repo_path
            )
            
            # Check if the command was successful
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            return success, output
        except Exception as e:
            return False, str(e)
    
    def check_lint_errors(self, file_path: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if the file has any remaining lint errors
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Tuple of (has_errors, errors)
        """
        try:
            # Use git_ops to get the absolute path
            full_path = self.git_ops.get_absolute_path(file_path)
            
            # Check if file exists before running ESLint
            if not os.path.exists(full_path):
                return True, [{"message": f"File not found: {full_path}", "severity": 2}]
            
            # Run ESLint with --format=json to get structured output
            result = subprocess.run(
                ["npx", "eslint", "--format=json", full_path],
                capture_output=True,
                text=True,
                cwd=self.git_ops.repo_path
            )
            
            # Check for file not found errors in stderr
            if "No files matching the pattern" in result.stderr:
                return True, [{"message": f"ESLint could not find file: {full_path}", "severity": 2}]
            
            # Parse the JSON output
            if result.stdout.strip():
                try:
                    print("\nParsing ESLint JSON output (first 100 chars):\n", result.stdout[:100])
                    lint_results = json.loads(result.stdout)
                    print("Successfully parsed ESLint JSON output")
                except json.JSONDecodeError as e:
                    print(f"\nJSON parsing error in check_lint_errors: {e}")
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
    
    def check_typescript_errors(self, file_path: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if the file has any TypeScript type errors
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Tuple of (has_errors, errors)
        """
        try:
            # Use git_ops to get the absolute path
            full_path = self.git_ops.get_absolute_path(file_path)
            
            # Run TypeScript compiler in noEmit mode to check types
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", full_path],
                capture_output=True,
                text=True,
                cwd=self.git_ops.repo_path
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
        
    def run_validation_step(self, file_path: str, code: str, validation_type: str, llm_client=None, update_status=True) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Run a validation step with retry logic
        
        Args:
            file_path: Path to the file to validate
            code: Current code content
            validation_type: Type of validation to run (e.g., 'eslint')
            llm_client: Optional LLM client for fixing errors
            
        Returns:
            Tuple of (success, updated_code, remaining_errors)
        """
        # Update the migration status to show this step is in progress
        if update_status:
            try:
                status_key = 'eslint' if validation_type == 'eslint' else 'tsc'
                code = self.update_migration_status(file_path, code, {status_key: "in progress"})
            except Exception as e:
                print(f"\nError updating migration status: {str(e)}")
                # Continue without updating status if there's an error
            
        # Write the code to the file
        self.git_ops.write_file(file_path, code)
        
        # Initialize variables
        success = False
        updated_code = code
        remaining_errors = []
        retries = 0
        
        # Run the validation step with retries
        while not success and retries < self.max_retries:
            if validation_type == 'eslint':
                # Step 1: Run lint --fix
                lint_fix_success, lint_fix_output = self.run_lint_fix(file_path)
                if not lint_fix_success and "No files matching the pattern" in lint_fix_output:
                    return False, code, [{"message": f"File not found: {file_path}", "severity": 2}]
                
                # Read the updated file after lint --fix
                updated_code = self.git_ops.read_file(file_path)
                
                # Step 2: Check for remaining lint errors
                has_errors, errors = self.check_lint_errors(file_path)
                
                # Calculate validation metrics
                if update_status:
                    # For simplicity, we'll estimate passed items based on errors
                    # In a real implementation, you might want to parse the actual lint output
                    # to get more accurate metrics
                    total_rules = len(errors) + 10  # Assuming at least 10 rules were checked
                    passed = total_rules - len(errors)
                    failed = len(errors)
                    skipped = 0  # We don't have skipped information in this simple implementation
                    success_rate = int((passed / total_rules) * 100) if total_rules > 0 else 100
                    
                    lint_status = {
                        "passed": passed,
                        "failed": failed,
                        "total": total_rules,
                        "skipped": skipped,
                        "successRate": success_rate
                    }
                    
                    # Update the status with detailed metrics
                    try:
                        updated_code = self.update_migration_status(
                            file_path,
                            updated_code,
                            {"eslint": lint_status}
                        )
                    except Exception as e:
                        print(f"\nError updating migration status with lint metrics: {str(e)}")
                        # Continue without updating status if there's an error
                
                if not has_errors:
                    success = True
                    # Update status to show lint validation is complete
                    if update_status:
                        updated_code = self.update_migration_status(
                            file_path, 
                            updated_code, 
                            {'eslint': "done"}
                        )
                    break
                
                # If we have an LLM client and there are errors, try to fix them
                if llm_client and has_errors:
                    # Use LLM to fix lint errors
                    print(f"\nAttempt {retries + 1}/{self.max_retries}: Using LLM to fix lint errors...")
                    lint_fix_prompt = f"""# Lint Error Fix Request (Attempt {retries + 1})

## File with Lint Errors

```tsx
{updated_code}
```

## Current Lint Errors

```json
{json.dumps(errors, indent=2)}
```

Please fix ONLY these specific lint errors in the code while preserving the functionality.
Do not introduce new issues or change unrelated code.
"""
                    
                    # Call LLM to fix lint errors
                    lint_fix_response = llm_client._call_llm_api(lint_fix_prompt)
                    
                    # Log the response for debugging
                    print("\nLLM Response (first 200 chars):\n", lint_fix_response[:200])
                    
                    # Extract the fixed code
                    import re
                    code_pattern = "```tsx\n(.+?)\n```"
                    print("Attempting to extract code with pattern:", code_pattern)
                    code_match = re.search(code_pattern, lint_fix_response, re.DOTALL)
                    
                    if code_match:
                        updated_code = code_match.group(1).strip()
                        print("LLM attempted to fix lint errors")
                        
                        # Write the updated code back to the file
                        self.git_ops.write_file(file_path, updated_code)
                        
                        # Verify that the lint errors were actually fixed
                        has_errors, remaining_errors = self.check_lint_errors(file_path)
                        if not has_errors:
                            success = True
                            # Update status to show lint validation is complete
                            if update_status:
                                updated_code = self.update_migration_status(
                                    file_path, 
                                    updated_code, 
                                    {'eslint': "done"}
                                )
                            break
                    else:
                        print("LLM failed to provide fixed code")
            
            elif validation_type == 'typescript':
                # Check for TypeScript errors
                has_errors, errors = self.check_typescript_errors(file_path)
                
                # Calculate validation metrics
                if update_status:
                    # For simplicity, we'll estimate passed items based on errors
                    # In a real implementation, you might want to parse the actual TypeScript output
                    # to get more accurate metrics
                    total_checks = len(errors) + 10  # Assuming at least 10 type checks were performed
                    passed = total_checks - len(errors)
                    failed = len(errors)
                    skipped = 0  # We don't have skipped information in this simple implementation
                    success_rate = int((passed / total_checks) * 100) if total_checks > 0 else 100
                    
                    ts_status = {
                        "passed": passed,
                        "failed": failed,
                        "total": total_checks,
                        "skipped": skipped,
                        "successRate": success_rate
                    }
                    
                    # Update the status with detailed metrics
                    try:
                        updated_code = self.update_migration_status(
                            file_path,
                            updated_code,
                            {"tsc": ts_status}
                        )
                    except Exception as e:
                        print(f"\nError updating migration status with TypeScript metrics: {str(e)}")
                        # Continue without updating status if there's an error
                
                if not has_errors:
                    success = True
                    # Update status to show TypeScript validation is complete
                    if update_status:
                        updated_code = self.update_migration_status(
                            file_path, 
                            updated_code, 
                            {'tsc': "done"}
                        )
                    break
                
                # If we have an LLM client and there are errors, try to fix them
                if llm_client and has_errors:
                    # Use LLM to fix TypeScript errors
                    print(f"\nAttempt {retries + 1}/{self.max_retries}: Using LLM to fix TypeScript errors...")
                    ts_fix_prompt = f"""# TypeScript Error Fix Request (Attempt {retries + 1})

## File with TypeScript Errors

```tsx
{updated_code}
```

## Current TypeScript Errors

```json
{json.dumps(errors, indent=2)}
```

Please fix ONLY these specific TypeScript errors in the code while preserving the functionality.
Focus on fixing type issues, adding proper type annotations, and ensuring type safety.
Do not introduce new issues or change unrelated code.
"""
                    
                    # Call LLM to fix TypeScript errors
                    ts_fix_response = llm_client._call_llm_api(ts_fix_prompt)
                    
                    # Extract the fixed code
                    import re
                    code_pattern = "```tsx\n(.+?)\n```"
                    code_match = re.search(code_pattern, ts_fix_response, re.DOTALL)
                    
                    if code_match:
                        updated_code = code_match.group(1).strip()
                        print("LLM attempted to fix TypeScript errors")
                        
                        # Write the updated code back to the file
                        self.git_ops.write_file(file_path, updated_code)
                        
                        # Verify that the TypeScript errors were actually fixed
                        has_errors, remaining_errors = self.check_typescript_errors(file_path)
                        if not has_errors:
                            success = True
                            # Update status to show TypeScript validation is complete
                            if update_status:
                                updated_code = self.update_migration_status(
                                    file_path, 
                                    updated_code, 
                                    {'tsc': "done"}
                                )
                            break
                    else:
                        print("LLM failed to provide fixed code")
            
            retries += 1
        
        return success, updated_code, remaining_errors