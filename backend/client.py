import asyncio
import sys
import json
from typing import Optional, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self, tcp_port: int = 8080):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.tcp_port = tcp_port
        self.tcp_server = None
        self.running = True

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

    async def start_tcp_server(self):
        """Start TCP server to receive external messages"""
        self.tcp_server = await asyncio.start_server(
            self.handle_tcp_client,
            'localhost',
            self.tcp_port
        )
        print(f"TCP server started on port {self.tcp_port}")

    async def handle_tcp_client(self, reader, writer):
        """Handle incoming TCP connections and process messages"""
        client_addr = writer.get_extra_info('peername')
        print(f"\nTCP client connected: {client_addr}")
        
        try:
            while self.running:
                # Read message from TCP client
                data = await reader.read(4096)  # Increased buffer size
                if not data:
                    break
                
                message = data.decode('utf-8').strip()
                if not message:
                    continue
                    
                print(f"Received TCP message: {message}")
                
                # Process the message and get response
                try:
                    response = await self.process_tcp_message(message)
                    response_data = {
                        "status": "success",
                        "data": response
                    }
                except Exception as e:
                    response_data = {
                        "status": "error",
                        "error": str(e)
                    }
                
                # Send response back to TCP client
                response_json = json.dumps(response_data, indent=2) + '\n'
                writer.write(response_json.encode('utf-8'))
                await writer.drain()
                
        except Exception as e:
            print(f"Error handling TCP client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"TCP client disconnected: {client_addr}")

    async def process_tcp_message(self, message: str) -> str:
        """
        Process TCP message and convert it to a query for the MCP system
        
        Supported formats:
        1. Plain text query: "What is the weather today?"
        2. JSON query: {"query": "What is the weather today?", "context": "additional context"}
        3. Command format: "QUERY: What is the weather today?"
        """
        try:
            # Try to parse as JSON first
            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict) and "query" in parsed:
                    query = parsed["query"]
                    # You can add additional context processing here if needed
                    context = parsed.get("context", "")
                    full_query = f"{query}\n{context}" if context else query
                    return await self.process_query(full_query)
                else:
                    return await self.process_query(str(parsed))
            except json.JSONDecodeError:
                pass
            
            # Handle command format
            if message.startswith("QUERY:"):
                query = message[6:].strip()
                return await self.process_query(query)
            
            # Handle plain text as direct query
            return await self.process_query(message)
            
        except Exception as e:
            return f"Error processing TCP message: {str(e)}"

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
        """Interactive chat loop for console input"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print(f"TCP server also listening on port {self.tcp_port}")

        while self.running:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    self.running = False
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def run_with_tcp(self):
        """Run both console chat and TCP server concurrently"""
        # Start TCP server
        await self.start_tcp_server()
        
        # Create tasks for both console chat and TCP server
        chat_task = asyncio.create_task(self.chat_loop())
        server_task = asyncio.create_task(self.tcp_server.serve_forever())
        
        try:
            # Wait for either task to complete (chat_loop ends on 'quit')
            done, pending = await asyncio.wait(
                [chat_task, server_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False

    async def cleanup(self):
        self.running = False
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_script> [tcp_port]")
        sys.exit(1)

    tcp_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    client = MCPClient(tcp_port=tcp_port)
    try:
        await client.connect_to_server(sys.argv[1])
        await client.run_with_tcp()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
