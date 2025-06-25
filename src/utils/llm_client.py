import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Import icons from validation.py
from .validation import ERROR_ICON, SUCCESS_ICON, WARNING_ICON, INFO_ICON, PENDING_ICON

# Load environment variables from .env file
load_dotenv()

class LLMClient:
    """Client for interacting with LLM APIs for component migration"""
    
    def __init__(self):
        """Initialize the LLM client with API keys and configuration"""
        # Get API key from environment variables
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # Initialize OpenAI client (will be used with Gemini model)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        # No need to explicitly pass proxies - they'll be picked up from env vars
        
        # Default model to use
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Base paths for prompts
        self.base_path = Path(__file__).parent.parent
        self.system_prompt_path = self.base_path / "prompts" / "system_prompt.md"
        self.components_path = self.base_path / "prompts" / "components"
        
        # Load system prompt
        self.system_prompt = self._load_prompt(self.system_prompt_path)
    
    def _load_prompt(self, prompt_path: Union[str, Path]) -> str:
        """Load a prompt from a file
        
        Args:
            prompt_path: Path to the prompt file
            
        Returns:
            The prompt content as a string
        """
        try:
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise ValueError(f"Failed to load prompt from {prompt_path}: {str(e)}")
    
    def get_supported_components(self) -> List[str]:
        """Get a list of supported components for migration
        
        Returns:
            List of component names that have migration prompts
        """
        try:
            # Get all .md files in the components directory
            component_files = list(self.components_path.glob("*.md"))
            # Extract component names (filename without extension)
            return [file.stem for file in component_files]
        except Exception as e:
            print(f"{ERROR_ICON} Error getting supported components")
            print(f"Details: {str(e)}")
            return []
    
    def migrate_component(self, component_name: str, component_code: str) -> Dict[str, Any]:
        """Migrate a component using the LLM
        
        Args:
            component_name: Name of the component to migrate (must be supported)
            component_code: Source code of the component to migrate
            
        Returns:
            Dictionary containing the migrated code and migration notes
        """
        # Check if component is supported
        if component_name not in self.get_supported_components():
            raise ValueError(f"Component {component_name} is not supported for migration")
        
        # Load component-specific prompt
        component_prompt_path = self.components_path / f"{component_name}.md"
        component_prompt = self._load_prompt(component_prompt_path)
        
        # Construct the full prompt
        user_prompt = f"""# Component Migration Request

## Component to Migrate: {component_name}

```tsx
{component_code}
```

## Migration Guide
{component_prompt}

Please migrate ONLY the {component_name} component according to the guidelines provided. Do not modify other components in the file."""
        
        # Call the LLM API
        response = self._call_llm_api(user_prompt)
        
        # Parse and return the response
        return self._parse_migration_response(response)
    
    def _call_llm_api(self, user_prompt: str) -> str:
        """Call the LLM API with the given prompt
        
        Args:
            user_prompt: The user prompt to send to the LLM
            
        Returns:
            The LLM's response as a string
        """
        try:
            # Create messages with system prompt and user prompt
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call the OpenAI API with the Gemini model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,  # Lower temperature for more deterministic outputs
                max_tokens=50000,  # Adjust based on expected response length
                user="tiktok_llm_tux_migration"
            )
            
            # Check and log the finish reason
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "stop":
                print(f"LLM Finish Reason: {finish_reason}")
            else:
                print(f"{ERROR_ICON} WARNING: LLM DID NOT COMPLETE NORMALLY. Finish Reason: {finish_reason}")
                print(f"{ERROR_ICON} This may indicate truncated output or other issues with the LLM response.")

            # Extract and return the response content
            content = response.choices[0].message.content
            
            return content
        except Exception as e:
            raise RuntimeError(f"Error calling LLM API: {str(e)}")
    
    def _parse_migration_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM's response into structured data
        
        Args:
            response: The raw response from the LLM
            
        Returns:
            Dictionary containing the migrated code and migration notes
        """
        try:
            # Initialize result structure
            result = {
                "migrated_code": "",
                "migration_notes": ""
            }
            
            # Extract code block (between ```tsx and ```)
            code_pattern = r'```tsx\n([\s\S]*?)\n```'
            import re
            print(f"Using code extraction pattern: {code_pattern}")
            code_match = re.search(code_pattern, response, re.DOTALL)
            if code_match:
                result["migrated_code"] = code_match.group(1).strip()
                print(f"Successfully extracted code of length: {len(result['migrated_code'])}")
            else:
                print(f"\n{WARNING_ICON} CODE EXTRACTION ISSUE")
                print(f"Failed to extract code using the primary pattern")
                # Try alternative patterns
                alt_patterns = [
                    r'```(tsx|jsx|js|ts)\n([\s\S]*?)\n```',  # Any language tag
                    r'```\n([\s\S]*?)\n```'  # No language tag
                ]
                
                for pattern in alt_patterns:
                    print(f"Trying alternative pattern: {pattern}")
                    alt_match = re.search(pattern, response, re.DOTALL)
                    if alt_match:
                        # If pattern has language tag, group(2) contains the code
                        # Otherwise group(1) contains the code
                        code_group = 2 if len(alt_match.groups()) > 1 and alt_match.group(1) else 1
                        result["migrated_code"] = alt_match.group(code_group).strip()
                        print(f"Successfully extracted code using alternative pattern, length: {len(result['migrated_code'])}")
                        break
                
                if not result["migrated_code"]:
                    print(f"\n{ERROR_ICON} Failed to extract code using all patterns")
                    print(f"Full response:\n", response)
            
            # Extract migration notes (after ## Migration Notes)
            notes_pattern = "## Migration Notes\n(.+)$"
            notes_match = re.search(notes_pattern, response, re.DOTALL)
            if notes_match:
                result["migration_notes"] = notes_match.group(1).strip()
            
            return result
        except Exception as e:
            print(f"{ERROR_ICON} ERROR PARSING LLM RESPONSE")
            print(f"Details: {str(e)}")
            # Return the raw response if parsing fails
            return {
                "migrated_code": "",
                "migration_notes": "",
                "raw_response": response,
                "error": str(e)
            }
