import os
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pathlib import Path

# Initialize the model using the API key from .env (automatically picked up by pydantic-ai)
# Initialize the model using the working version found in tests
model = GeminiModel('gemini-2.5-flash')

# Define the Liaison Agent
liaison_agent = Agent(
    model,
    system_prompt=(
        "You are NitroScout Liaison. Your mission is to draft elite, technical, "
        "and helpful responses for the Nitrostack community. Refer to the provided "
        "SOUL, AGENTS, and NITROSTACK KNOWLEDGE BASE to ensure absolute accuracy."
    )
)

async def draft_response(platform: str, inquiry: str):
    """
    Drafts a response and saves it to the workspace/drafts folder.
    """
    # Load context from brain files
    brain_dir = Path(__file__).parent.parent / "brain"
    soul = (brain_dir / "SOUL.md").read_text()
    marketing = (brain_dir / "nitro_marketing.md").read_text() if (brain_dir / "nitro_marketing.md").exists() else ""
    
    prompt = f"""
    CONTEXT (SOUL):
    {soul}

    NITROSTACK TECHNICAL KNOWLEDGE:
    {marketing}

    PLATFORM: {platform}
    INQUIRY: {inquiry}

    TASK: Draft a high-signal response following the SOUL guidelines and technical facts from the knowledge base. 
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
