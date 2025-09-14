import asyncio
import sys
import json
from typing import Optional, List, Dict, Any, Union
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fastmcp import Client as FastMCPClient

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class UnifiedMCPClient:
    def __init__(self, tcp_port: int = 8080):
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.exit_stack = AsyncExitStack()
        
        self.anthropic = Anthropic()
        self.tcp_port = tcp_port
        self.tcp_server = None
        self.running = True
        
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_length = 10

    async def connect_to_local_server(self, server_name: str, server_script_path: str):
        """Connect to a local MCP server"""
        parts = server_script_path.split()
        if parts[0].endswith(".py"):
            command = sys.executable
            args = parts
        else:
            command = parts[0]
            args = parts[1:]

        server_params = StdioServerParameters(command=command, args=args, env=None)
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        response = await session.list_tools()
        tools = response.tools
        print(f"Connected to LOCAL server {server_name} with tools: {[tool.name for tool in tools]}")

        self.connections[server_name] = {
            "type": "local",
            "session": session,
            "stdio": stdio,
            "write": write
        }

    async def connect_to_remote_server(self, server_name: str, server_url: str):
        """Connect to a remote MCP server"""
        try:
            async with FastMCPClient(server_url) as client:
                tools = await client.list_tools()
                print(f"Connected to REMOTE server {server_name} with tools: {[tool.name for tool in tools]}")
            self.connections[server_name] = {"type": "remote", "url": server_url}
        except Exception as e:
            print(f"Failed to connect to remote server {server_name}: {e}")
            raise

    async def get_tools(self, server_name: str = None):
        """Get tools from a specific server or all servers"""
        if server_name:
            conn = self.connections.get(server_name)
            if not conn:
                raise RuntimeError(f"No server {server_name} connected")

            if conn["type"] == "local":
                response = await conn["session"].list_tools()
                return response.tools
            else:
                async with FastMCPClient(conn["url"]) as client:
                    return await client.list_tools()
        else:
            # Get tools from all connected servers
            all_tools = []
            for srv_name, conn in self.connections.items():
                try:
                    if conn["type"] == "local":
                        response = await conn["session"].list_tools()
                        tools = response.tools
                    else:
                        async with FastMCPClient(conn["url"]) as client:
                            tools = await client.list_tools()
                    
                    # Add server info to tools
                    for tool in tools:
                        tool._server_name = srv_name
                    all_tools.extend(tools)
                except Exception as e:
                    print(f"Error getting tools from {srv_name}: {e}")
            return all_tools

    async def call_tool(self, server_name: str, tool_name: str, tool_input: dict):
        """Call a tool on a specific server"""
        conn = self.connections.get(server_name)
        if not conn:
            raise RuntimeError(f"No server {server_name} connected")

        if conn["type"] == "local":
            return await conn["session"].call_tool(tool_name, tool_input)
        else:
            async with FastMCPClient(conn["url"]) as client:
                return await client.call_tool(tool_name, tool_input)

    def find_tool_server(self, tool_name: str) -> Optional[str]:
        """Find which server has the specified tool"""
        for server_name in self.connections.keys():
            try:
                # This would need to be cached for efficiency in a real implementation
                asyncio.create_task(self._check_tool_exists(server_name, tool_name))
            except:
                continue
        return None

    async def _check_tool_exists(self, server_name: str, tool_name: str) -> bool:
        """Check if a tool exists on a server"""
        try:
            tools = await self.get_tools(server_name)
            return any(tool.name == tool_name for tool in tools)
        except:
            return False

    async def start_tcp_server(self):
        """Start the TCP server for external connections"""
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
        """Handle incoming TCP connections"""
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
        """Process incoming TCP messages"""
        parsed = None
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            pass

        server_name = None
        if isinstance(parsed, dict):
            query = parsed.get("query", message)
            if "server" in parsed:
                server_name = parsed["server"]
        else:
            query = message

        if not self.connections:
            return "No servers connected."

        return await self.process_query(query, conversation_id, server_name)

    async def process_query(self, query: str, conversation_id: str = "console", preferred_server: str = None) -> str:
        """Process a query using available MCP servers"""
        print(f"Processing query: {query}")
        if self.connections:
            print(f"Connected servers: {list(self.connections.keys())}")
        
        try:
            messages = self.get_conversation_history(conversation_id).copy()
            
            user_message = {"role": "user", "content": query}
            messages.append(user_message)
            self.add_to_conversation_history(conversation_id, "user", query)

            # Get available tools from all connected servers
            tools_raw = await self.get_tools()
            available_tools = []
            tool_server_map = {}
            
            for tool in tools_raw:
                tool_info = {
                    "name": tool.name, 
                    "description": tool.description, 
                    "input_schema": tool.inputSchema
                }
                available_tools.append(tool_info)
                # Add server info for tool routing
                if hasattr(tool, '_server_name'):
                    tool_server_map[tool.name] = tool._server_name

            tool_names = [f"{tool['name']} ({tool.get('_server_name', 'unknown')})" for tool in available_tools]
            print(f"Available tools: {tool_names}")
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
                        # Find which server has this tool
                        target_server = None
                        for tool_info in available_tools:
                            if tool_info['name'] == tool_call.name:
                                target_server = tool_info.get('_server_name')
                                break
                        
                        if not target_server:
                            # Fallback: try the preferred server or first available
                            target_server = preferred_server or list(self.connections.keys())[0]
                        
                        print(f"Calling tool {tool_call.name} on server {target_server}")
                        tool_result = await self.call_tool(target_server, tool_call.name, tool_call.input)
                        
                        # Handle results from both local and remote servers
                        conn_type = self.connections[target_server]["type"]
                        if conn_type == 'local':
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
        """Interactive chat loop for console usage"""
        conversation_id = "console"
        print(f"\nUnified MCP Client Started!")
        print(f"Connected to servers: {list(self.connections.keys())}")
        print("Type your queries, 'servers' to list servers, 'clear' to clear conversation history, or 'quit' to exit.")
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
                elif query.lower() == "servers":
                    print(f"Connected servers: {list(self.connections.keys())}")
                    for name, conn in self.connections.items():
                        print(f"  - {name} ({conn['type']})")
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
        """Clean up resources"""
        self.running = False
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()
        await self.exit_stack.aclose()

async def async_input(prompt: str = "") -> str:
    """Async input function"""
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
        print("Usage: python unified_client.py <server1> [server2] [server3] ... [--tcp-port PORT]")
        print("\nExamples:")
        print("  Single server:    python unified_client.py mcp-server-git")
        print("  Multiple servers: python unified_client.py mcp-server-git server.py http://localhost:8080/mcp")
        print("  With TCP port:    python unified_client.py mcp-server-git --tcp-port 9090")
        sys.exit(1)

    # Parse arguments
    servers = []
    tcp_port = 8080
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--tcp-port' and i + 1 < len(args):
            tcp_port = int(args[i + 1])
            i += 2
        else:
            servers.append(args[i])
            i += 1
    
    if not servers:
        print("Error: At least one server must be specified")
        sys.exit(1)
    
    client = UnifiedMCPClient(tcp_port=tcp_port)
    
    try:
        for i, server_arg in enumerate(servers):
            connection_type = detect_connection_type(server_arg)
            server_name = f"server_{i+1}" if len(servers) > 1 else "default"
            
            if connection_type == 'local':
                print(f"Connecting to LOCAL server {server_name}: {server_arg}")
                await client.connect_to_local_server(server_name, server_arg)
            else:
                print(f"Connecting to REMOTE server {server_name}: {server_arg}")
                await client.connect_to_remote_server(server_name, server_arg)
            
        await client.run_with_tcp()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
