import os
import subprocess
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

class ValidationOperations:
    """Class for handling validation operations like linting and type checking"""
    
    def __init__(self, repo_path: str = None):
        """Initialize the validation operations
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path or os.getcwd()
    
    def run_lint_fix(self, file_path: str) -> Tuple[bool, str]:
        """Run ESLint with --fix option on the specified file
        
        Args:
            file_path: Path to the file to lint
            
        Returns:
            Tuple of (success, output)
        """
        try:
            # Construct the full path if file_path is relative
            full_path = os.path.join(self.repo_path, file_path)
            
            # Run ESLint with --fix option
            result = subprocess.run(
                ["npx", "eslint", "--fix", full_path],
                capture_output=True,
                text=True,
                cwd=self.repo_path
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
            # Construct the full path if file_path is relative
            full_path = os.path.join(self.repo_path, file_path)
            
            # Run ESLint with --format=json to get structured output
            result = subprocess.run(
                ["npx", "eslint", "--format=json", full_path],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
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
        try:
            # Construct the full path if file_path is relative
            full_path = os.path.join(self.repo_path, file_path)
            
            # Run TypeScript compiler in noEmit mode to check types
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", full_path],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            # Check if there are any errors
            has_errors = result.returncode != 0
            
            # Parse the error output
            errors = []
            if has_errors and result.stderr:
                # Simple parsing of TypeScript error messages
                error_lines = result.stderr.strip().split("\n")
                for line in error_lines:
                    if line.strip() and "error TS" in line:
                        errors.append({
                            "message": line.strip(),
                            "severity": 2
                        })
            
            return has_errors, errors
        except Exception as e:
            return True, [{"message": str(e), "severity": 2}]