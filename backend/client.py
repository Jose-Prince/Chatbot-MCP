import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """
        Process a user query in natural language using Claude + MCP tools
        following the recommended message flow.
        """
        # Initial user message
        messages = [
            {"role": "user", "content": query}
        ]

        # Get list of available tools
        response = await self.session.list_tools()
        available_tools = [
            {"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema}
            for tool in response.tools
        ]
    
        final_text = []

        # Step 1: Send initial message and receive tool_use
        anthropic_response = self.anthropic.messages.create(
            model="claude-3-haiku-20240307",
            messages=messages,
            max_tokens=1000,
            tools=available_tools
        )

        # Add Claude's response to the conversation
        assistant_content = []
    
        for content in anthropic_response.content:
            if content.type == "text":
                final_text.append(content.text)
                assistant_content.append({
                    "type": "text",
                    "text": content.text
                })
            elif content.type == "tool_use":
                # Add the tool_use to assistant's message
                assistant_content.append({
                    "type": "tool_use",
                    "id": content.id,
                    "name": content.name,
                    "input": content.input
                })
            
                # Step 2: Execute the tool using MCP
                tool_name = content.name
                tool_args = content.input

                try:
                    tool_result = await self.session.call_tool(tool_name, tool_args)
                    tool_content = tool_result.content
                
                # Handle different types of tool result content
                    if isinstance(tool_content, list):
                    # If content is a list, extract text from it
                        content_text = ""
                        for item in tool_content:
                            if hasattr(item, 'text'):
                                content_text += item.text
                            else:
                                content_text += str(item)
                    else:
                        content_text = str(tool_content)
                
                    final_text.append(f"[Tool '{tool_name}' executed with result: {content_text}]")
                
                except Exception as e:
                    content_text = f"Error executing tool: {str(e)}"
                    final_text.append(f"[Tool '{tool_name}' failed: {content_text}]")

        # Add assistant's message to conversation
        messages.append({
            "role": "assistant", 
            "content": assistant_content
        })

        # Step 3: Add tool results as user message
        if any(c.get("type") == "tool_use" for c in assistant_content):
            tool_results = []
        
            # Process each tool_use from the assistant's response
            for content in anthropic_response.content:
                if content.type == "tool_use":
                    try:
                        tool_result = await self.session.call_tool(content.name, content.input)
                        tool_content = tool_result.content
                    
                        # Handle different types of tool result content
                        if isinstance(tool_content, list):
                            content_text = ""
                            for item in tool_content:
                                if hasattr(item, 'text'):
                                    content_text += item.text
                                else:
                                    content_text += str(item)
                        else:
                            content_text = str(tool_content)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": content_text
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result", 
                            "tool_use_id": content.id,
                            "content": f"Error: {str(e)}"
                        })

        # Add tool results as user message
            messages.append({
                "role": "user",
                "content": tool_results
            })

        # Step 4: Get Claude's final response
            followup_response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                messages=messages,
                max_tokens=1000,
                tools=available_tools
            )

            for followup_content in followup_response.content:
                if followup_content.type == "text":
                    final_text.append(followup_content.text)

        return "\n".join(final_text)    

    async def chat_loop(self):
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("sage: pyhton client.py <server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
