import asyncio
import logging
import os

from fastmcp import FastMCP 
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp = FastMCP("MCP Server on Cloud Run")
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@mcp.tool()
def tell_joke(category: str = "general") -> str:
    """Tell a short and funny joke.
    
    Args:
        category: optional category for the joke
    """
    prompt = f"Tell me a short and funny joke about {category}."
    response = anthropic.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}]
    )

    joke = ""
    for block in response.content:
        if block.type == "text":
            joke += block.text.strip()

    return joke if joke else "I couldn't make a joke."

if __name__ == "__main__":
    logger.info(f" MCP server started on port {os.getenv('PORT', 8090)}")
    # Could also use 'sse' transport, host="0.0.0.0" required for Cloud Run.
    asyncio.run(
        mcp.run_async(
            transport="streamable-http", 
            host="0.0.0.0", 
            port=os.getenv("PORT", 8090),
        )
    )

