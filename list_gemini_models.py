import os
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

def list_models():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]No API key.[/red]")
        return
    
    genai.configure(api_key=api_key)
    try:
        console.print("[yellow]Listing available models...[/yellow]")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    list_models()
