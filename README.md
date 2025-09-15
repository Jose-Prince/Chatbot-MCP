# ChispitasGPT

A chatbot application using the Model Context Protocol (MCP) with a Python backend and LÖVE2D frontend. The system allows connecting to both local and remote MCP servers and provides a graphical chat interface.

## Architecture

- **Backend**: Python-based MCP client that connects to multiple MCP servers and provides TCP communication
- **Frontend**: LÖVE2D (Lua) based GUI with chat interface, conversation history, and database storage
- **Communication**: TCP socket communication between frontend and backend

## Prerequisites

### Backend Requirements
- Python 3.8+
- pip (Python package manager)

### Frontend Requirements
- [LÖVE2D (Love2D)](https://love2d.org/) game engine
- The following Lua libraries (included in the project):
  - LoveFrames (for GUI components)
  - classic (for OOP)
  - dkjson (for JSON handling)
  - socket (for TCP communication)

## Installation

### 1. Backend Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Chatbot-MCP
   ```

2. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   Create a `.env` file in the backend directory:
   ```bash
   # Add your Anthropic API key
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

### 2. Frontend Setup

1. **Install LÖVE2D**:
   - **Windows**: Download from [love2d.org](https://love2d.org/) and install
   - **macOS**: `brew install love` (with Homebrew)
   - **Linux**: `sudo apt-get install love2d` (Ubuntu/Debian) or equivalent

2. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

3. **Install required Lua libraries**:
   The project includes the necessary Lua libraries. Make sure you have:
   - LoveFrames (should be in `LoveFrames/` directory)
   - luasocket (usually comes with LÖVE2D)

## Usage

### Starting the System

#### Option 1: Run Backend and Frontend Separately

1. **Start the Backend**:
   ```bash
   cd backend
   python client.py <mcp-server-command> [--tcp-port 8080]
   ```

   Examples:
   ```bash
   # Connect to a local MCP server
   python client.py mcp-server-git
   
   # Connect to multiple servers
   python client.py mcp-server-git server.py
   
   # Connect to a remote server
   python client.py http://localhost:8080/mcp
   
   # Specify custom TCP port
   python client.py mcp-server-git --tcp-port 9090
   ```

2. **Start the Frontend**:
   ```bash
   cd frontend
   love .
   ```

   Or on some systems:
   ```bash
   love2d .
   ```

#### Option 2: Quick Start Script

Create a startup script to launch both components:

**Windows (start.bat)**:
```batch
@echo off
start /D backend python client.py mcp-server-git
timeout /t 2
start /D frontend love .
```

**macOS/Linux (start.sh)**:
```bash
#!/bin/bash
cd backend && python client.py mcp-server-git &
sleep 2
cd ../frontend && love .
```

### Configuration

#### Backend Configuration
- **TCP Port**: Default is 8080, change with `--tcp-port` parameter
- **MCP Servers**: Specify one or more MCP servers as command line arguments
- **API Keys**: Configure in the `.env` file

#### Frontend Configuration
Edit `frontend/networkManager.lua` to change connection settings:
```lua
self.host = "127.0.0.1"  -- Backend host
self.port = 8080         -- Backend TCP port
```

## MCP Server Examples

The system supports various types of MCP servers:

### Local Python Servers
```bash
# Git operations server
python client.py mcp-server-git

# Custom Python server
python client.py path/to/your/server.py
```

### Remote HTTP Servers
```bash
# Remote MCP server
python client.py http://localhost:8080/mcp
```

### Multiple Servers
```bash
# Connect to multiple servers simultaneously
python client.py mcp-server-git http://localhost:8080/mcp server.py --tcp-port 8081
```

## Features

### Backend Features
- **Multi-server support**: Connect to multiple MCP servers simultaneously
- **Local and remote servers**: Support for both stdio and HTTP MCP servers
- **TCP server**: Provides TCP interface for frontend communication
- **Conversation history**: Maintains chat history with configurable length
- **Tool execution**: Executes tools from connected MCP servers
- **Error handling**: Robust error handling and reconnection logic

### Frontend Features
- **Chat interface**: Modern WhatsApp-style chat bubbles
- **Conversation management**: Create, save, and delete chat conversations
- **Database storage**: Local JSON-based conversation storage
- **Scrollable history**: Navigate through long conversations
- **Real-time updates**: Live connection status and message handling
- **Responsive design**: Resizable window with adaptive layout

## Development

### Adding New MCP Servers

1. Install the MCP server package:
   ```bash
   pip install your-mcp-server
   ```

2. Start the client with your server:
   ```bash
   python client.py your-mcp-server-command
   ```

### Customizing the Frontend

- **Colors**: Edit color schemes in component files
- **Layout**: Modify component sizes in `main.lua`
- **Features**: Add new functionality in respective component files

### API Integration

The system uses Claude 3 Haiku for chat responses. To use different models:

1. Edit `backend/client.py`
2. Change the model parameter in the Anthropic API calls:
   ```python
   model="claude-3-sonnet-20240229"  # or other available models
   ```
