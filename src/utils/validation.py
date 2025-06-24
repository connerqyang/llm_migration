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
                lint_results = json.loads(result.stdout)
                
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
        # This method is commented out as we're focusing only on lint validation for now
        # try:
        #     # Use git_ops to get the absolute path
        #     full_path = self.git_ops.get_absolute_path(file_path)
        #     
        #     # Run TypeScript compiler in noEmit mode to check types
        #     result = subprocess.run(
        #         ["npx", "tsc", "--noEmit", full_path],
        #         capture_output=True,
        #         text=True,
        #         cwd=self.git_ops.repo_path
        #     )
        #     
        #     # Log the result
        #     print(f"TypeScript compiler return code: {result.returncode}")
        #     print(f"TypeScript compiler stderr: {result.stderr}")
        #     print(f"TypeScript compiler stdout: {result.stdout}")

        #     # Check if there are any errors
        #     has_errors = result.returncode != 0
        #     
        #     # Parse the error output
        #     errors = []
        #     if has_errors:
        #         # Combine stderr and stdout for error parsing
        #         error_text = (result.stderr + result.stdout).strip()
        #         error_lines = error_text.split("\n")
        #         for line in error_lines:
        #             if line.strip() and "error TS" in line:
        #                 errors.append({
        #                     "message": line.strip(),
        #                     "severity": 2
        #                 })
        #     
        #     return has_errors, errors
        # except Exception as e:
        #     return True, [{"message": str(e), "severity": 2}]
        
        # Return no errors since TypeScript validation is disabled
        return False, []
        
    def run_validation_step(self, file_path: str, code: str, validation_type: str, llm_client=None) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Run a validation step with retry logic
        
        Args:
            file_path: Path to the file to validate
            code: Current code content
            validation_type: Type of validation to run (e.g., 'lint')
            llm_client: Optional LLM client for fixing errors
            
        Returns:
            Tuple of (success, updated_code, remaining_errors)
        """
        # Write the code to the file
        self.git_ops.write_file(file_path, code)
        
        # Initialize variables
        success = False
        updated_code = code
        remaining_errors = []
        retries = 0
        
        # Run the validation step with retries
        while not success and retries < self.max_retries:
            if validation_type == 'lint':
                # Step 1: Run lint --fix
                lint_fix_success, lint_fix_output = self.run_lint_fix(file_path)
                if not lint_fix_success and "No files matching the pattern" in lint_fix_output:
                    return False, code, [{"message": f"File not found: {file_path}", "severity": 2}]
                
                # Read the updated file after lint --fix
                updated_code = self.git_ops.read_file(file_path)
                
                # Step 2: Check for remaining lint errors
                has_errors, errors = self.check_lint_errors(file_path)
                
                if not has_errors:
                    success = True
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
                    
                    # Extract the fixed code
                    import re
                    code_pattern = "```tsx\n(.+?)\n```"
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
                            break
                    else:
                        print("LLM failed to provide fixed code")
            
            # Add more validation types here in the future
            # elif validation_type == 'typescript':
            #     # TypeScript validation logic would go here
            #     pass
            
            retries += 1
        
        return success, updated_code, remaining_errors