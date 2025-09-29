#!/bin/bash

# Outbound Call Dispatcher Web Service Startup Script

echo "🚀 Starting Floor Covering International Outbound Call Dispatcher Web Service"
echo "============================================================================="

# Check if virtual environment exists
if [ ! -d ".agent_venv" ]; then
    echo "❌ Virtual environment not found. Please run ./build.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .agent_venv/bin/activate

# Install web service requirements if they don't exist
echo "📦 Installing web service dependencies..."
pip install -r web_requirements.txt

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo "❌ .env file not found. Please create it with the required environment variables."
    echo "See README.md for required variables."
    exit 1
fi

# Load environment variables from .env file (handle quotes properly)
set -a  # automatically export all variables
source ../.env
set +a  # stop automatically exporting

# Check required environment variables
echo "🔍 Checking required environment variables..."

required_vars=(
    "API_KEY"
    "LIVEKIT_URL"
    "LIVEKIT_API_KEY"
    "LIVEKIT_API_SECRET"
    "SIP_OUTBOUND_TRUNK_ID"
    "OPENAI_API_KEY"
    "DEEPGRAM_API_KEY"
    "CARTESIA_API_KEY"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   %s\n' "${missing_vars[@]}"
    echo "Please check your .env file."
    exit 1
fi

echo "✅ All required environment variables are set"

# Set default values
export FLASK_ENV=${FLASK_ENV:-development}
export PORT=${PORT:-5000}

echo "🌐 Starting web service..."
echo "   Environment: $FLASK_ENV"
echo "   Port: $PORT"
echo "   API Key: ${API_KEY:0:10}..."
echo ""
echo "📖 API Documentation:"
echo "   Health Check: http://localhost:$PORT/health"
echo "   Dispatch Call: http://localhost:$PORT/api/v1/dispatch-call"
echo ""
echo "🧪 To test the API, run: python test_api.py"
echo ""

# Start the web service
python web_service.py