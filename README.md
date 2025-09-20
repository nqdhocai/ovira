# Ovira - Onchain Vault Intelligent & Risk Agent

Ovira is a sophisticated multi-agent system that enables AI agents to communicate and collaborate through the Coral protocol. It combines a powerful orchestrator with specialized agents to create a dynamic, interactive agent ecosystem.

## 🌟 Features

- **Multi-Agent Architecture**: Orchestrator and specialized agents working in harmony
- **Coral Protocol Integration**: Seamless agent-to-agent communication using MCP (Model Context Protocol)
- **Real-time Communication**: SSE-based messaging system for instant agent interactions
- **Flexible Agent Framework**: Extensible system for creating custom agents
- **Thread-based Messaging**: Organized conversation management between agents

## 🏗️ Architecture

The project consists of two main components:

### 1. Coral Server
- **Location**: `coral-server/`
- **Purpose**: MCP server providing communication tools for agent interactions
- **Technology**: Kotlin-based server with Gradle build system
- **Features**: 
  - Agent registration and discovery
  - Thread-based messaging
  - Real-time notifications
  - Agent mention system

### 2. Agent Universe
- **Location**: `strategy_engine/`
- **Purpose**: Collection of AI agents and orchestration system
- **Technology**: Python-based with modern async architecture
- **Components**:
  - Orchestrator: Central coordination agent
  - Specialized Agents: Task-specific AI workers
  - Database Integration: MongoDB for persistent storage
  - Configuration Management: Flexible settings system

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Java 8+ (for Coral server)
- UV package manager
- MongoDB (for data persistence)

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ovira
   ```

2. **Start the Coral Protocol Server**
   ```bash
   ./start-server.sh
   ```
   This will:
   - Navigate to the `coral-server` directory
   - Start the Gradle-based Coral server
   - Enable MCP communication protocols

3. **Configure Environment**
   ```bash
   cd strategy_engine
   cp app-config-template.yaml app-config.yaml
   # Edit app-config.yaml with your settings
   ```

4. **Run the Agent System**
   ```bash
   # Start agents and orchestrator
   cd strategy_engine
   uv run -m agents.agents
   uv run -m agents.orchestrator
   ```

5. **Run the API**
   ```bash
   cd strategy_engine
   uv run -m api.api_main
   ```

## 🔧 Configuration

### Agent Configuration
Edit `strategy_engine/app-config.yaml` to configure:
- Model providers (OpenAI, Google Gemini, etc.)
- Database connections
- MCP server endpoints
- Agent-specific settings

### Server Configuration
The Coral server can be configured through environment variables and the config path.

## 🤝 Development

### Adding New Agents
1. Create a new agent class in `strategy_engine/agents/`
2. Extend the base agent framework
3. Register the agent in the configuration
4. Define agent-specific prompts and tools

### Extending Communication
The Coral protocol provides extensible tools for:
- Custom message types
- Agent discovery mechanisms
- Thread management
- Notification systems

## 📊 Monitoring & Logs

Agent activities and communications are logged for debugging and monitoring purposes. Check the system logs for detailed execution traces.

## 🛠️ Troubleshooting

### Common Issues

1. **Server startup fails**: Ensure Java 8+ is installed and ports are available
2. **Agent connection issues**: Verify Coral server is running before starting agents
3. **Database connection**: Check MongoDB is running and accessible
4. **Environment variables**: Ensure all required configuration is set

### Debug Mode

Run with verbose logging:
```bash
uv run -m agents.orchestrator --debug
```

## 🤖 Agent Types

The system includes various specialized agents:
- **Orchestrator**: Central coordination and task distribution
- **Base Agent**: Foundation for all agent implementations
- **Model Agents**: LLM integration and management
- **Custom Agents**: Domain-specific implementations

## 📈 Performance

The system is designed for:
- Concurrent agent operations
- Efficient message routing
- Scalable agent discovery
- Real-time communication

## 🔮 Future Enhancements

- Remote mode for distributed agent networks
- Enhanced security and authentication
- Advanced agent coordination patterns
- Integration with additional AI models
- Web-based management interface

## 📄 License

[Add your license information here]

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

---

For more detailed information about specific components, see the README files in `coral-server/` and `agent_universe/` directories.
