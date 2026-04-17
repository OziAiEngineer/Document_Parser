"""Core extraction logic using Ollama."""
import json
import requests
from typing import Dict, Any
from prompt_builder import build_system_prompt, build_extraction_prompt


class OllamaAgent:
    """Agent that communicates with local Ollama instance."""
    
    def __init__(self, model: str = "ministral-3:latest", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        
        # Default builders
        from prompt_builder import build_system_prompt, build_extraction_prompt
        self.system_prompt_fn = build_system_prompt
        self.extraction_prompt_fn = build_extraction_prompt
    
    def extract_from_document(self, document_text: str) -> Dict[str, Any]:
        """
        Send document to Ollama and extract structured data in two passes.
        
        Args:
            document_text: The full text of the legal document
            
        Returns:
            Dictionary containing extracted fields from both passes merged
        """
        final_extracted_data = {}
        
        for pass_number in [1, 2]:
            print(f"Executing Extraction Pass {pass_number}...")
            system_prompt = self.system_prompt_fn(pass_number)
            user_prompt = self.extraction_prompt_fn(document_text, pass_number)
            
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "format": "json"
            }
            
            try:
                response = requests.post(self.generate_url, json=payload, timeout=120)
                response.raise_for_status()
                
                result = response.json()
                response_text = result.get("response", "")
                
                # Parse the JSON response
                extracted_data = self._parse_response(response_text)
                final_extracted_data.update(extracted_data)
                
            except requests.exceptions.RequestException as e:
                raise Exception(f"Failed to connect to Ollama on pass {pass_number}: {e}")
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse LLM response as JSON on pass {pass_number}: {e}")
                
        return final_extracted_data
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and clean the LLM response."""
        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response_text[start:end])
            raise

def extract_document(text: str, system_prompt_fn = None, extraction_prompt_fn = None) -> Dict[str, Any]:
    """Helper to instantiate agent and extract."""
    agent = OllamaAgent()
    if system_prompt_fn:
        agent.system_prompt_fn = system_prompt_fn
    if extraction_prompt_fn:
        agent.extraction_prompt_fn = extraction_prompt_fn
    return agent.extract_from_document(text)


def call_ollama(system_prompt: str, user_prompt: str, model: str = "ministral-3:latest") -> str:
    """Helper for raw LLM calls without JSON parsing mapping."""
    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "stream": False,
        "format": "json"
    }
    response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
    response.raise_for_status()
    return response.json().get("response", "")
