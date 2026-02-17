import os
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pathlib import Path

# Initialize the model using the API key from .env (automatically picked up by pydantic-ai)
model = GeminiModel('gemini-2.0-flash')

# Define the Liaison Agent
liaison_agent = Agent(
    model,
    system_prompt=(
        "You are NitroScout Liaison. Read the SOUL.md, AGENTS.md, and COMPETITORS.md "
        "files provided in context to understand your persona and mission. "
        "Your task is to draft a technical, helpful, and elite response to a developer inquiry."
    )
)

async def draft_response(platform: str, inquiry: str):
    """
    Drafts a response and saves it to the workspace/drafts folder.
    """
    # Load context from brain files
    brain_dir = Path(__file__).parent.parent / "brain"
    soul = (brain_dir / "SOUL.md").read_text()
    
    prompt = f"""
    CONTEXT (SOUL):
    {soul}

    PLATFORM: {platform}
    INQUIRY: {inquiry}

    TASK: Draft a response following the SOUL guidelines. 
    Output only the markdown content of the draft.
    """
    
    result = await liaison_agent.run(prompt)
    
    # Save to workspace
    drafts_dir = Path(__file__).parent.parent / "workspace" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{platform}_draft_test.md"
    filepath = drafts_dir / filename
    filepath.write_text(result.data_str)
    
    return filepath
