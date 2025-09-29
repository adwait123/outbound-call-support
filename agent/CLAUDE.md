# Voice Assistant Agent

Python-based voice assistant that handles real-time conversations using LiveKit and AI services.

## Technology Stack

- **Framework**: LiveKit Agents SDK
- **Speech**: Deepgram (STT), Cartesia/OpenAI (TTS)  
- **AI**: OpenAI GPT with tonies® support knowledge
- **Audio**: Silero noise cancellation

## Setup & Development

### Build & Start (Recommended)
```bash
# Create virtual environment and install dependencies
./build.sh

# Activate virtual environment and start agent
./start.sh
```

The `build.sh` script creates `.agent_venv/` virtual environment and installs all dependencies. The `start.sh` script activates this environment and runs the agent.

### Manual Development
```bash
# Create and activate virtual environment
python3 -m venv .agent_venv
source .agent_venv/bin/activate

# Install dependencies  
pip install -r requirements.txt

# Run agent
python src/agent.py
```

## Configuration

Environment variables (create `.env` file):
```bash
LIVEKIT_URL=wss://your-livekit-server
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
```

## Core Components

### Assistant Class (`src/agent.py:22`)
Main agent orchestration and conversation management

### Utilities (`src/utils/`)
- **auth.py**: Token management  
- **session.py**: Conversation lifecycle
- **tracing.py**: Analytics and logging
- **fetching.py**: External API calls
- **common.py**: Shared utilities

## Agent Capabilities

- **Voice Processing**: Real-time speech-to-text and text-to-speech
- **Support Tools**: Access device logs, documentation, ticket creation
- **Workflow**: Guided troubleshooting with escalation triggers
- **Analytics**: Comprehensive conversation tracing

## Conversation Flow

1. User connects → 2. Issue identification → 3. Documentation lookup → 4. Step-by-step guidance → 5. Device diagnostics (if needed) → 6. Escalation (if unresolved)

## Related Components

- **[Backend](../backend/CLAUDE.md)**: API services and database
- **[Admin Interface](../admin_interface/CLAUDE.md)**: Monitoring dashboard  
- **[User Interface](../user_interface/CLAUDE.md)**: End-user portal
- **[Integration Tests](../integration_tests/CLAUDE.md)**: Testing framework