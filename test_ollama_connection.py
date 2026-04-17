"""Test script to verify Ollama connection and Mistral availability."""
import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def test_ollama_connection():
    """Test if Ollama server is running."""
    console.print("\n[cyan]Testing Ollama Connection...[/cyan]\n")
    
    base_url = "http://localhost:11434"
    
    # Test 1: Check if server is running
    console.print("1. Checking if Ollama server is running...")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            console.print("[green]✓ Ollama server is running![/green]\n")
        else:
            console.print(f"[yellow]⚠ Server responded with status {response.status_code}[/yellow]\n")
            return False
    except requests.exceptions.ConnectionError:
        console.print("[red]✗ Cannot connect to Ollama server[/red]")
        console.print("[yellow]Solution: Run 'ollama serve' in another terminal[/yellow]\n")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]\n")
        return False
    
    # Test 2: List available models
    console.print("2. Checking available models...")
    try:
        data = response.json()
        models = data.get('models', [])
        
        if not models:
            console.print("[yellow]⚠ No models found[/yellow]")
            console.print("[yellow]Solution: Run 'ollama pull mistral' to download Mistral[/yellow]\n")
            return False
        
        # Create table of models
        table = Table(title="Available Models")
        table.add_column("Model Name", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="yellow")
        
        mistral_found = False
        for model in models:
            name = model.get('name', 'unknown')
            size = model.get('size', 0)
            size_gb = size / (1024**3)
            modified = model.get('modified_at', 'unknown')
            
            table.add_row(name, f"{size_gb:.2f} GB", modified[:10])
            
            if 'ministral' in name.lower() or 'mistral' in name.lower():
                mistral_found = True
        
        console.print(table)
        console.print()
        
        if not mistral_found:
            console.print("[yellow]⚠ Ministral/Mistral model not found[/yellow]")
            console.print("[yellow]Solution: Run 'ollama pull mistral' to download it[/yellow]\n")
            return False
        else:
            console.print("[green]✓ Ministral-3 model is available![/green]\n")
        
    except Exception as e:
        console.print(f"[red]✗ Error parsing models: {e}[/red]\n")
        return False
    
    # Test 3: Test generation with Ministral-3
    console.print("3. Testing Ministral-3 generation...")
    try:
        payload = {
            "model": "ministral-3:latest",
            "prompt": "Say 'Hello, I am working!' and nothing else.",
            "stream": False
        }
        
        response = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '')
            console.print(f"[green]✓ Ministral-3 responded: {response_text[:100]}[/green]\n")
        else:
            console.print(f"[yellow]⚠ Generation failed with status {response.status_code}[/yellow]\n")
            return False
            
    except Exception as e:
        console.print(f"[red]✗ Generation test failed: {e}[/red]\n")
        return False
    
    # Success!
    console.print(Panel(
        "[green]✓ All tests passed! Your Ollama setup is ready.[/green]\n"
        "You can now run: [cyan]python main.py sample_documents/sample_1.txt[/cyan]",
        title="Success",
        border_style="green"
    ))
    
    return True


if __name__ == "__main__":
    test_ollama_connection()
