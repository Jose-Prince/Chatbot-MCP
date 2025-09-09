import asyncio
import sys
import json
from typing import Optional
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

    async def start_tcp_server(self):
        """Start TCP server to receive external messages"""
        self.tcp_server = await asyncio.start_server(
            self.handle_tcp_client,
            'localhost',
            self.tcp_port
        )
        print(f"TCP server started on port {self.tcp_port}")

    async def connect_to_server(self, server_script_path: str):
        parts = server_script_path.split()

        if server_script_path.endswith('.py'):
            command = "python"
            args = [server_script_path]
        elif server_script_path.endswith('.ts'):
            command = "npx"
            args = ["ts-node", server_script_path]
        elif server_script_path.startswith('npx'):
            command = parts[0]  # "npx"
            args = parts[1:]    # ["@modelcontextprotocol/server-filesystem", "./", ...]
        elif len(parts) > 1:
            # Handle commands with arguments like "mcp-server-filesystem ./"
            command = parts[0]  # "mcp-server-filesystem"
            args = parts[1:]    # ["./"]
        else:
            # Single command without arguments (like "mcp-server-git")
            command = parts[0]
            args = []
    
        # Special case: if command is specifically "mcp-server-git" with no args, use your git setup
        if command == "mcp-server-git" and len(args) == 0:
            server_params = StdioServerParameters(
                command="mcp-server-git",
                args=[],
                env=None,
                cwd="/home/akice/Documentos/Repositories/Chatbot-MCP"
            )
        else:
            # General case for all other servers including filesystem
            server_params = StdioServerParameters(
                command=command,
                args=args,
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

    async def handle_tcp_client(self, reader, writer):
        client_addr = writer.get_extra_info('peername')
        print(f"\nTCP client connected: {client_addr}")

        try:
            while self.running:
                data = await reader.read(4096)
                if not data:
                    break
                message = data.decode("utf-8").strip()
                if not message:
                    continue

                print(f"Received TCP message: {message}")
                
                # Process the message and send response
                try:
                    print(f"Processing message: {message}")
                    response = await self.process_tcp_message(message)
                    response_data = {
                        "status": "success",
                        "data": response,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    print(f"Response generated: {response}")
                except Exception as e:
                    print(f"Error processing message: {str(e)}")
                    response_data = {
                        "status": "error",
                        "error": str(e),
                        "timestamp": asyncio.get_event_loop().time()
                    }

                # Send the response back to frontend
                response_json = json.dumps(response_data, ensure_ascii=False) + "\n"
                print(f"Sending response: {response_json.strip()}")
                
                try:
                    writer.write(response_json.encode("utf-8"))
                    await writer.drain()
                    print("Response sent successfully!")
                except Exception as send_error:
                    print(f"Failed to send response: {send_error}")
                    break

        except ConnectionResetError:
            print(f"TCP client disconnected unexpectedly: {client_addr}")
        except Exception as e:
            print(f"Error in TCP handler: {str(e)}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"TCP client disconnected: {client_addr}")

    async def process_tcp_message(self, message: str) -> str:
        """
        Process TCP message and convert it to a query for the MCP system
        """
        try:
            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict) and "query" in parsed:
                    query = parsed["query"]
                    context = parsed.get("context", "")
                    full_query = f"{query}\n{context}" if context else query
                    return await self.process_query(full_query)
                else:
                    return await self.process_query(str(parsed))
            except json.JSONDecodeError:
                pass

            if message.startswith("QUERY:"):
                query = message[6:].strip()
                return await self.process_query(query)

            return await self.process_query(message)

        except Exception as e:
            print(f"Error in process_tcp_message: {str(e)}")
            return f"Error processing TCP message: {str(e)}"

    async def process_query(self, query: str) -> str:
        """
        Process a user query in natural language using Claude + MCP tools
        """
        print(f"Processing query: {query}")
        
        try:
            messages = [{"role": "user", "content": query}]

            # Get list of available tools
            response = await self.session.list_tools()
            available_tools = [
                {"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema}
                for tool in response.tools
            ]

            print(f"Available tools: {[tool['name'] for tool in available_tools]}")

            # Step 1: Send initial message to Claude
            print("Sending initial message to Claude...")
            anthropic_response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                messages=messages,
                max_tokens=1000,
                tools=available_tools
            )

            print(f"Claude response received with {len(anthropic_response.content)} content blocks")

            # Process Claude's response
            assistant_content = []
            tool_calls = []

            for content in anthropic_response.content:
                if content.type == "text":
                    print(f"Text content: {content.text}")
                    assistant_content.append({"type": "text", "text": content.text})
                elif content.type == "tool_use":
                    print(f"Tool use: {content.name} with input: {content.input}")
                    assistant_content.append({
                        "type": "tool_use", 
                        "id": content.id, 
                        "name": content.name, 
                        "input": content.input
                    })
                    tool_calls.append(content)

            # Add assistant's response to conversation
            messages.append({"role": "assistant", "content": assistant_content})

            # If Claude wants to use tools, execute them
            if tool_calls:
                print(f"Executing {len(tool_calls)} tool calls...")
                tool_results = []
                
                for tool_call in tool_calls:
                    try:
                        print(f"Calling tool: {tool_call.name}")
                        tool_result = await self.session.call_tool(tool_call.name, tool_call.input)
                        
                        # Extract content from tool result
                        if hasattr(tool_result, 'content'):
                            if isinstance(tool_result.content, list):
                                content_text = "".join([
                                    getattr(item, 'text', str(item)) for item in tool_result.content
                                ])
                            else:
                                content_text = str(tool_result.content)
                        else:
                            content_text = str(tool_result)
                        
                        print(f"Tool result: {content_text}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": content_text
                        })
                        
                    except Exception as e:
                        print(f"Tool execution failed: {str(e)}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": f"Error: {str(e)}"
                        })

                # Send tool results back to Claude
                messages.append({"role": "user", "content": tool_results})
                
                print("Sending tool results to Claude for final response...")
                followup_response = self.anthropic.messages.create(
                    model="claude-3-haiku-20240307",
                    messages=messages,
                    max_tokens=1000,
                    tools=available_tools
                )

                # Collect final response
                final_texts = []
                for content in followup_response.content:
                    if content.type == "text":
                        final_texts.append(content.text)
                        print(f"Final response: {content.text}")

                return "\n".join(final_texts) if final_texts else "Task completed."

            else:
                # No tools needed, return Claude's direct response
                final_texts = []
                for content in anthropic_response.content:
                    if content.type == "text":
                        final_texts.append(content.text)
                
                return "\n".join(final_texts) if final_texts else "No response generated."

        except Exception as e:
            print(f"Error in process_query: {str(e)}")
            return f"Error processing query: {str(e)}"

    async def chat_loop(self):
        """Interactive chat loop for console input"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print(f"TCP server also listening on port {self.tcp_port}")

        while self.running:
            try:
                query = await async_input("\nQuery: ")
                if query.lower() == "quit":
                    self.running = False
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def run_with_tcp(self):
        """Run both console chat and TCP server concurrently"""
        await self.start_tcp_server()
        chat_task = asyncio.create_task(self.chat_loop())
        server_task = asyncio.create_task(self.tcp_server.serve_forever())

        try:
            done, pending = await asyncio.wait(
                [chat_task, server_task],
                return_when=asyncio.FIRST_COMPLETED
            )

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

async def async_input(prompt: str = "") -> str:
    print(prompt, end="", flush=True)
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(None, sys.stdin.readline)).rstrip()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_script> [tcp_port]")
        sys.exit(1)

    server_command = sys.argv[1]
    tcp_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    client = MCPClient(tcp_port=tcp_port)
    try:
        await client.connect_to_server(server_command)
        await client.run_with_tcp()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
