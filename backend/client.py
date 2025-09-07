import asyncio
import websockets
import sys
import json
from typing import Optional, Any, Dict
from mcp import ClientSession
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

class WebSocketReadStream:
    def __init__(self, websocket):
        self.websocket = websocket
        self._closed = False
    
    async def read(self):
        """Read a message from WebSocket"""
        if self._closed:
            raise RuntimeError("Stream is closed")
        
        try:
            raw_message = await self.websocket.recv()
            message_dict = json.loads(raw_message)
            return message_dict
        except websockets.exceptions.ConnectionClosed:
            self._closed = True
            raise
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON received: {e}")
    
    def close(self):
        self._closed = True

class WebSocketWriteStream:
    def __init__(self, websocket):
        self.websocket = websocket
        self._closed = False
    
    async def send(self, message) -> None:
        """Send a message to WebSocket"""
        if self._closed:
            raise RuntimeError("Stream is closed")
        
        try:
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump(exclude_unset=True)
            elif hasattr(message, 'dict'):
                message_dict = message.dict(exclude_unset=True)
            elif hasattr(message, '__dict__'):
                message_dict = message.__dict__
            elif isinstance(message, dict):
                message_dict = message
            else:
                message_dict = dict(message)
            
            json_message = json.dumps(message_dict, default=str)
            await self.websocket.send(json_message)
        except websockets.exceptions.ConnectionClosed:
            self._closed = True
            raise
        except Exception as e:
            print(f"Error serializing message: {e}")
            print(f"Message type: {type(message)}")
            print(f"Message: {message}")
            raise
    
    def close(self):
        self._closed = True

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.read_stream: Optional[WebSocketReadStream] = None
        self.write_stream: Optional[WebSocketWriteStream] = None
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.anthropic = Anthropic(api_key=api_key)
    
    async def connect_to_server(self, uri: str):
        """Connect to MCP server via WebSocket"""
        try:
            print(f"Connecting to {uri}...")
            
            self.websocket = await websockets.connect(uri)
            
            self.read_stream = WebSocketReadStream(self.websocket)
            self.write_stream = WebSocketWriteStream(self.websocket)
            
            self.session = ClientSession(self.read_stream, self.write_stream)
            
            print("Initializing MCP session...")
            init_result = await self.session.initialize()
            print(f"Session initialized successfully")
            
            try:
                print("Listing available tools...")
                tools_response = await self.session.list_tools()
                tools = tools_response.tools if hasattr(tools_response, 'tools') else []
                print(f"Connected with {len(tools)} tools available:")
                for tool in tools:
                    print(f"  - {tool.name}: {getattr(tool, 'description', 'No description')}")
            except Exception as e:
                print(f"Warning: Could not list tools: {e}")
                
        except Exception as e:
            print(f"Failed to connect: {e}")
            await self.cleanup()
            raise
    
    async def process_query(self, query: str) -> str:
        if not self.session:
            return "Not connected to MCP server"
    
        try:
            tools_response = await self.session.list_tools()
            available_tools = []
            for tool in tools_response.tools:
                available_tools.append({
                    "name": tool.name,
                    "description": getattr(tool, 'description', f"Tool: {tool.name}"),
                    "input_schema": getattr(tool, 'inputSchema', {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            })
        
        # 2. Conversación inicial
            messages = [
                {"role": "user", "content": query}
            ]
        
        # 3. Primer llamado a Claude
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=messages,
                tools=available_tools
            )
        
            final_text = []
        
            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
            
                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input
                    tool_id = content.id  # importante para enlazar el resultado
                
                    print(f"➡ Claude eligió usar la tool '{tool_name}' con args: {tool_args}")
                
                    # 4. Ejecutar tool en MCP
                    tool_result = await self.session.call_tool(tool_name, tool_args)
                
                    result_text = str(tool_result.content) if hasattr(tool_result, 'content') else str(tool_result)
                    print(f"🔧 Tool result: {result_text}")
                
                # 5. Mandar el resultado de vuelta a Claude
                    messages.append({
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result_text
                            }
                        ]
                    })
                
                # 6. Segundo llamado a Claude para cerrar respuesta
                    followup = self.anthropic.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=2000,
                        messages=messages,
                        tools=available_tools
                    )
                
                    for item in followup.content:
                        if item.type == "text":
                            final_text.append(item.text)
        
            return "\n\n".join(final_text) if final_text else "No response generated"
    
        except Exception as e:
            return f"❌ Error processing query: {e}"    

    async def chat_loop(self):
        """Interactive chat loop"""
        print("\nMCP Client ready!")
        print("Commands:")
        print("  - Type your query to process it")
        print("  - 'tools' to list available tools")
        print("  - 'quit'/'exit'/'q' to exit")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("Quitting server...")
                    break
                
                if query.lower() == 'tools':
                    await self.list_tools()
                    continue
                
                if not query:
                    continue
                
                print("Processing...")
                response = await self.process_query(query)
                print(f"\nResponse:\n{response}")
                
            except KeyboardInterrupt:
                print("\nQuitting server...")
                break
            except EOFError:
                print("\nQutting server...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def list_tools(self):
        """List available tools from MCP server"""
        if not self.session:
            print("Not connected to MCP server")
            return
        
        try:
            tools_response = await self.session.list_tools()
            tools = tools_response.tools
            
            if not tools:
                print("No tools available")
                return
            
            print(f"\nAvailable tools ({len(tools)}):")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.name}")
                if hasattr(tool, 'description'):
                    print(f"     Description: {tool.description}")
                if hasattr(tool, 'inputSchema'):
                    schema = tool.inputSchema
                    if isinstance(schema, dict) and 'properties' in schema:
                        props = list(schema['properties'].keys())
                        if props:
                            print(f"     Parameters: {', '.join(props)}")
                print()
                
        except Exception as e:
            print(f"Error listing tools: {e}")
    
    async def cleanup(self):
        print("Cleaning up...")
        
        if self.read_stream:
            try:
                self.read_stream.close()
            except Exception:
                pass
        
        if self.write_stream:
            try:
                self.write_stream.close()
            except Exception:
                pass
        
        if self.session:
            try:
                if hasattr(self.session, 'close'):
                    await self.session.close()
            except Exception:
                pass
        
        if self.websocket:
            try:
                if hasattr(self.websocket, 'closed') and not self.websocket.closed:
                    await self.websocket.close()
                elif hasattr(self.websocket, 'close'):
                    await self.websocket.close()
            except Exception:
                pass

async def main():
    """Main function"""
    if len(sys.argv) > 1:
        server_uri = sys.argv[1]
    else:
        server_uri = "ws://localhost:8765"
    
    client = MCPClient()
    
    try:
        await client.connect_to_server(server_uri)
        await client.chat_loop()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    print("Starting MCP Client...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nQuitting server...")
    except Exception as e:
        print(f"Failed to start: {e}")
