#!/usr/bin/env python3
"""
MCP Client using the official MCP Python SDK
"""

import asyncio
import sys
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

class MCPClient:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.anthropic = Anthropic(api_key=api_key)
    
    async def connect_and_chat(self, server_script_path: str):
        """Connect to MCP server and start interactive chat"""
        try:
            print(f"🚀 Starting MCP server: {server_script_path}")
            
            # Create server parameters for stdio connection
            server_params = StdioServerParameters(
                command="python",
                args=[server_script_path],
            )
            
            # Connect to server using stdio transport
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    print("🔗 Connected to MCP server")
                    
                    # Initialize session
                    await session.initialize()
                    print("✅ Session initialized")
                    
                    # List available tools
                    try:
                        tools_response = await session.list_tools()
                        tools = tools_response.tools
                        print(f"🔧 Connected with {len(tools)} tools available:")
                        for tool in tools:
                            print(f"  - {tool.name}: {getattr(tool, 'description', 'No description')}")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not list tools: {e}")
                        tools = []
                    
                    # Start interactive chat loop
                    await self.chat_loop(session, tools)
                    
        except Exception as e:
            print(f"💥 Failed to connect: {e}")
            import traceback
            traceback.print_exc()
    
    async def chat_loop(self, session: ClientSession, available_tools):
        """Interactive chat loop"""
        print("\n🎉 MCP Client ready!")
        print("Commands:")
        print("  - Type your query to process it")
        print("  - 'tools' to list available tools")
        print("  - 'test' to run a test prediction")
        print("  - 'health' to check server health")
        print("  - 'sample' to get sample data")
        print("  - 'quit'/'exit'/'q' to exit")
        
        while True:
            try:
                query = input("\n📝 Query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if query.lower() == 'tools':
                    await self.list_tools(session)
                    continue
                
                if query.lower() == 'health':
                    await self.check_health(session)
                    continue
                    
                if query.lower() == 'sample':
                    await self.get_sample_data(session)
                    continue
                    
                if query.lower() == 'test':
                    test_query = "Can you make a game score prediction for an indie action game that costs $19.99, released in March, with tags ['Action', 'Adventure', 'Indie'] and genres ['Action']?"
                    print(f"🧪 Running test query: {test_query}")
                    response = await self.process_query(session, available_tools, test_query)
                    print(f"\n📊 Final Response:\n{response}")
                    continue
                
                if not query:
                    continue
                
                print("⏳ Processing...")
                response = await self.process_query(session, available_tools, query)
                print(f"\n📋 Final Response:\n{response}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n💥 Error: {str(e)}")
                import traceback
                traceback.print_exc()
    
    async def process_query(self, session: ClientSession, available_tools, query: str) -> str:
        """Process a query using Claude and MCP tools"""
        try:
            # Convert MCP tools to Anthropic format
            anthropic_tools = []
            for tool in available_tools:
                anthropic_tools.append({
                    "name": tool.name,
                    "description": getattr(tool, 'description', f"Tool: {tool.name}"),
                    "input_schema": getattr(tool, 'inputSchema', {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                })
            
            print(f"🤖 Sending query to Claude: {query}")
            
            # Initial conversation with Claude
            messages = [
                {"role": "user", "content": query}
            ]
        
            # First call to Claude
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=messages,
                tools=anthropic_tools
            )
        
            final_text = []
            
            # Process Claude's response
            for content in response.content:
                if content.type == "text":
                    print(f"💭 Claude says: {content.text}")
                    final_text.append(content.text)
                
                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input
                    tool_id = content.id
                
                    print(f"🔧 Claude is using tool '{tool_name}' with args: {tool_args}")
                
                    try:
                        # Execute tool via MCP
                        tool_result = await session.call_tool(tool_name, tool_args)
                    
                        # Extract result content
                        result_text = ""
                        if hasattr(tool_result, 'content') and tool_result.content:
                            for item in tool_result.content:
                                if hasattr(item, 'text'):
                                    result_text += item.text + "\n"
                                else:
                                    result_text += str(item) + "\n"
                        
                        # Also check for structured content
                        if hasattr(tool_result, 'structuredContent') and tool_result.structuredContent:
                            import json
                            structured_result = json.dumps(tool_result.structuredContent, indent=2)
                            result_text += f"\nStructured Result:\n{structured_result}"
                        
                        if not result_text.strip():
                            result_text = str(tool_result)
                    
                        print(f"✅ Tool result: {result_text.strip()}")
                    
                        # Continue conversation with Claude including the tool result
                        messages.append({
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": tool_id,
                                    "name": tool_name,
                                    "input": tool_args
                                }
                            ]
                        })
                        
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": result_text.strip()
                                }
                            ]
                        })
                    
                        # Get Claude's final response
                        followup = self.anthropic.messages.create(
                            model="claude-3-haiku-20240307",
                            max_tokens=2000,
                            messages=messages,
                            tools=anthropic_tools
                        )
                    
                        for item in followup.content:
                            if item.type == "text":
                                final_text.append(item.text)
                                print(f"💭 Claude's follow-up: {item.text}")
                    
                    except Exception as tool_error:
                        error_msg = f"Tool execution failed: {str(tool_error)}"
                        print(f"❌ {error_msg}")
                        final_text.append(error_msg)
        
            return "\n\n".join(final_text) if final_text else "No response generated"
    
        except Exception as e:
            print(f"💥 Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return f"💥 Error processing query: {e}"
    
    async def list_tools(self, session: ClientSession):
        """List available tools from MCP server"""
        try:
            tools_response = await session.list_tools()
            tools = tools_response.tools
            
            if not tools:
                print("📭 No tools available")
                return
            
            print(f"\n🔧 Available tools ({len(tools)}):")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.name}")
                if hasattr(tool, 'description'):
                    print(f"     📝 Description: {tool.description}")
                if hasattr(tool, 'inputSchema'):
                    schema = tool.inputSchema
                    if isinstance(schema, dict) and 'properties' in schema:
                        props = list(schema['properties'].keys())
                        if props:
                            print(f"     📊 Parameters: {', '.join(props)}")
                print()
                
        except Exception as e:
            print(f"💥 Error listing tools: {e}")
            import traceback
            traceback.print_exc()
    
    async def check_health(self, session: ClientSession):
        """Check server health"""
        try:
            result = await session.call_tool("health_check", {})
            
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(f"🏥 Health Check: {item.text}")
            
            if hasattr(result, 'structuredContent') and result.structuredContent:
                import json
                structured = json.dumps(result.structuredContent, indent=2)
                print(f"📊 Structured Health Data:\n{structured}")
                        
        except Exception as e:
            print(f"💥 Error checking health: {e}")
    
    async def get_sample_data(self, session: ClientSession):
        """Get sample data from server"""
        try:
            result = await session.call_tool("get_sample_data", {})
            
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(f"📊 Sample Data: {item.text}")
            
            if hasattr(result, 'structuredContent') and result.structuredContent:
                import json
                structured = json.dumps(result.structuredContent, indent=2)
                print(f"📋 Structured Sample Data:\n{structured}")
                        
        except Exception as e:
            print(f"💥 Error getting sample data: {e}")

async def main():
    """Main function"""
    if len(sys.argv) > 1:
        server_script = sys.argv[1]
    else:
        # Default to the server script
        server_script = "correct_mcp_server.py"
    
    # Check if server script exists
    if not os.path.exists(server_script):
        print(f"❌ Server script '{server_script}' not found!")
        print("Please make sure the server script exists.")
        return
    
    client = MCPClient()
    
    try:
        await client.connect_and_chat(server_script)
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting MCP Client...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Failed to start: {e}")
        import traceback
        traceback.print_exc()
