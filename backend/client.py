import asyncio
import sys
import json
from typing import Optional, List, Dict, Any, Union
from contextlib import AsyncExitStack

# Local server imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Remote server imports
from fastmcp import Client as FastMCPClient

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class UnifiedMCPClient:
    def __init__(self, tcp_port: int = 8080):
        # Local server attributes
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio = None
        self.write = None
        
        # Remote server attributes
        self.server_url: Optional[str] = None
        
        # Common attributes
        self.anthropic = Anthropic()
        self.tcp_port = tcp_port
        self.tcp_server = None
        self.running = True
        self.connection_type: Optional[str] = None  # 'local' or 'remote'
        
        # Conversation context storage
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_length = 10

    async def connect_to_local_server(self, server_script_path: str):
        """Connect to local MCP server via stdio"""
        self.connection_type = 'local'
        
        parts = server_script_path.split()

        if server_script_path.endswith('.py'):
            command = "python"
            args = [server_script_path]
        elif server_script_path.endswith('.ts'):
            command = "npx"
            args = ["ts-node", server_script_path]
        elif server_script_path.startswith('npx'):
            command = parts[0]
            args = parts[1:]    
        elif len(parts) > 1:
            command = parts[0]  
            args = parts[1:]
        else:
            command = parts[0]
            args = []
    
        if command == "mcp-server-git" and len(args) == 0:
            server_params = StdioServerParameters(
                command="mcp-server-git",
                args=[],
                env=None,
                cwd="/home/akice/Documentos/Repositories/Chatbot-MCP"
            )
        else:
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
        print(f"\nConnected to LOCAL server with tools: {[tool.name for tool in tools]}")

    async def connect_to_remote_server(self, server_url: str):
        """Connect to remote MCP server via HTTP"""
        self.connection_type = 'remote'
        self.server_url = server_url
        
        # Test the connection
        try:
            async with FastMCPClient(server_url) as client:
                tools = await client.list_tools()
                print(f"\nConnected to REMOTE server with tools: {[tool.name for tool in tools]}")
        except Exception as e:
            print(f"Failed to connect to remote server: {e}")
            raise

    async def get_tools(self):
        """Get available tools from the connected server"""
        if self.connection_type == 'local':
            response = await self.session.list_tools()
            return response.tools
        elif self.connection_type == 'remote':
            async with FastMCPClient(self.server_url) as client:
                tools = await client.list_tools()
                return tools
        else:
            raise RuntimeError("No server connected")

    async def call_tool(self, tool_name: str, tool_input: dict):
        """Call a tool on the connected server"""
        if self.connection_type == 'local':
            return await self.session.call_tool(tool_name, tool_input)
        elif self.connection_type == 'remote':
            async with FastMCPClient(self.server_url) as client:
                result = await client.call_tool(tool_name, tool_input)
                return result
        else:
            raise RuntimeError("No server connected")

    async def start_tcp_server(self):
        """Start TCP server to receive external messages"""
        self.tcp_server = await asyncio.start_server(
            self.handle_tcp_client,
            'localhost',
            self.tcp_port
        )
        print(f"TCP server started on port {self.tcp_port}")

    def get_conversation_id(self, client_addr: str = "console") -> str:
        """Generate a conversation ID based on client address"""
        return str(client_addr)

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a specific conversation"""
        return self.conversation_history.get(conversation_id, [])

    def add_to_conversation_history(self, conversation_id: str, role: str, content: Any):
        """Add a message to conversation history"""
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        self.conversation_history[conversation_id].append({
            "role": role,
            "content": content
        })
        
        if len(self.conversation_history[conversation_id]) > self.max_history_length * 2:
            history = self.conversation_history[conversation_id]
            if history[0].get("role") == "system":
                self.conversation_history[conversation_id] = [history[0]] + history[-(self.max_history_length * 2 - 1):]
            else:
                self.conversation_history[conversation_id] = history[-self.max_history_length * 2:]

    async def handle_tcp_client(self, reader, writer):
        client_addr = writer.get_extra_info('peername')
        conversation_id = self.get_conversation_id(str(client_addr))
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
                
                try:
                    print(f"Processing message: {message}")
                    response = await self.process_tcp_message(message, conversation_id)
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

    async def process_tcp_message(self, message: str, conversation_id: str) -> str:
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
                    return await self.process_query(full_query, conversation_id)
                else:
                    return await self.process_query(str(parsed), conversation_id)
            except json.JSONDecodeError:
                pass

            if message.startswith("QUERY:"):
                query = message[6:].strip()
                return await self.process_query(query, conversation_id)

            return await self.process_query(message, conversation_id)

        except Exception as e:
            print(f"Error in process_tcp_message: {str(e)}")
            return f"Error processing TCP message: {str(e)}"

    async def process_query(self, query: str, conversation_id: str = "console") -> str:
        print(f"Processing query: {query} (Connection: {self.connection_type})")
        
        try:
            messages = self.get_conversation_history(conversation_id).copy()
            
            user_message = {"role": "user", "content": query}
            messages.append(user_message)
            self.add_to_conversation_history(conversation_id, "user", query)

            # Get available tools from the connected server
            tools_raw = await self.get_tools()
            available_tools = [
                {
                    "name": tool.name, 
                    "description": tool.description, 
                    "input_schema": tool.inputSchema
                }
                for tool in tools_raw
            ]

            print(f"Available tools: {[tool['name'] for tool in available_tools]}")
            print(f"Conversation history length: {len(messages)}")

            print("Sending message with context to Claude...")
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

            self.add_to_conversation_history(conversation_id, "assistant", assistant_content)
            messages.append({"role": "assistant", "content": assistant_content})

            if tool_calls:
                print(f"Executing {len(tool_calls)} tool calls...")
                tool_results = []
                
                for tool_call in tool_calls:
                    try:
                        print(f"Calling {self.connection_type} tool: {tool_call.name}")
                        tool_result = await self.call_tool(tool_call.name, tool_call.input)
                        
                        # Handle results from both local and remote servers
                        if self.connection_type == 'local':
                            # Local server result handling
                            if hasattr(tool_result, 'content'):
                                if isinstance(tool_result.content, list):
                                    content_text = "".join([
                                        getattr(item, 'text', str(item)) for item in tool_result.content
                                    ])
                                else:
                                    content_text = str(tool_result.content)
                            else:
                                content_text = str(tool_result)
                        else:
                            # Remote server result handling
                            if isinstance(tool_result, list) and len(tool_result) > 0:
                                if hasattr(tool_result[0], 'text'):
                                    content_text = tool_result[0].text
                                else:
                                    content_text = str(tool_result[0])
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

                self.add_to_conversation_history(conversation_id, "user", tool_results)
                messages.append({"role": "user", "content": tool_results})
                
                print("Sending tool results to Claude for final response...")
                followup_response = self.anthropic.messages.create(
                    model="claude-3-haiku-20240307",
                    messages=messages,
                    max_tokens=1000,
                    tools=available_tools
                )

                final_texts = []
                final_assistant_content = []
                
                for content in followup_response.content:
                    if content.type == "text":
                        final_texts.append(content.text)
                        final_assistant_content.append({"type": "text", "text": content.text})
                        print(f"Final response: {content.text}")

                if final_assistant_content:
                    self.add_to_conversation_history(conversation_id, "assistant", final_assistant_content)

                return "\n".join(final_texts) if final_texts else "Task completed."

            else:
                final_texts = []
                for content in anthropic_response.content:
                    if content.type == "text":
                        final_texts.append(content.text)
                
                return "\n".join(final_texts) if final_texts else "No response generated."

        except Exception as e:
            print(f"Error in process_query: {str(e)}")
            return f"Error processing query: {str(e)}"

    async def chat_loop(self):
        conversation_id = "console"
        print(f"\nUnified MCP Client Started! (Connection: {self.connection_type})")
        print("Type your queries, 'clear' to clear conversation history, or 'quit' to exit.")
        print(f"TCP server also listening on port {self.tcp_port}")

        while self.running:
            try:
                query = await async_input("\nQuery: ")
                if query.lower() == "quit":
                    self.running = False
                    break
                elif query.lower() == "clear":
                    if conversation_id in self.conversation_history:
                        del self.conversation_history[conversation_id]
                    print("Conversation history cleared!")
                    continue
                    
                response = await self.process_query(query, conversation_id)
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
        if self.connection_type == 'local':
            await self.exit_stack.aclose()

async def async_input(prompt: str = "") -> str:
    print(prompt, end="", flush=True)
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(None, sys.stdin.readline)).rstrip()

def detect_connection_type(server_arg: str) -> str:
    """Detect if the server argument is a URL (remote) or script path (local)"""
    if server_arg.startswith(('http://', 'https://')):
        return 'remote'
    else:
        return 'local'

async def main():
    if len(sys.argv) < 2:
        print("Usage: python unified_client.py <server_script_or_url> [tcp_port]")
        print("\nExamples:")
        print("  Local:  python unified_client.py mcp-server-git 8080")
        print("  Local:  python unified_client.py server.py 8080")
        print("  Remote: python unified_client.py http://localhost:8080/mcp 8080")
        sys.exit(1)

    server_arg = sys.argv[1]
    tcp_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    connection_type = detect_connection_type(server_arg)
    client = UnifiedMCPClient(tcp_port=tcp_port)
    
    try:
        if connection_type == 'local':
            print(f"Connecting to LOCAL server: {server_arg}")
            await client.connect_to_local_server(server_arg)
        else:
            print(f"Connecting to REMOTE server: {server_arg}")
            await client.connect_to_remote_server(server_arg)
            
        await client.run_with_tcp()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
