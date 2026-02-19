import os
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load environment variables
load_dotenv()

console = Console()

def test_connection():
    console.print(Panel("🧪 Testing Google Generative AI Connection", style="bold blue"))
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        console.print("[bold red]❌ Error: No API key found in .env[/bold red]")
        return

    # Configure the library
    genai.configure(api_key=api_key)

    try:
        # Use verified model name (trying 2.5)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        console.print("[yellow]📡 Sending test message: 'Hello! Are you alive?'[/yellow]")
        
        # Simple test call
        response = model.generate_content("Hello! Are you alive?")
        
        console.print(Panel(f"✅ [bold green]Connection Successful![/bold green]\n\n[white]Response:[/white] {response.text}", border_style="green"))
        
    except Exception as e:
        console.print(Panel(f"❌ [bold red]Connection Failed[/bold red]\n\n[white]Error:[/white] {str(e)}", border_style="red"))
        
        if "429" in str(e):
            console.print("[yellow]💡 Note: Quota reached. The key is valid, but the limit is exhausted for today.[/yellow]")

if __name__ == "__main__":
    test_connection()
