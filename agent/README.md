# Outbound Call Dispatcher Web Service

A Flask-based REST API for dispatching outbound sales calls using LiveKit and Twilio SIP integration. This service is designed for integration with Zapier workflows and other automation tools.

## Features

- 🚀 REST API for outbound call dispatch
- 🔐 Simple API key authentication
- 📞 Phone number validation for US numbers
- 🎯 Integration with Floor Covering International sales agent
- 🔄 Perfect for Zapier workflows
- ☁️ Ready for cloud deployment (Render, Heroku, etc.)

## Quick Start

### 1. Local Development Setup

```bash
# Clone and navigate to the agent directory
cd /path/to/outbound_call_support/agent

# Install dependencies
pip install -r web_requirements.txt

# Set up environment variables (copy from .env.example)
cp .env.example .env
# Edit .env with your actual values

# Run the development server
python web_service.py
```

### 2. Environment Variables

Required environment variables:

```bash
# API Authentication
API_KEY=your-secure-api-key-here

# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# SIP Configuration
SIP_OUTBOUND_TRUNK_ID=your-twilio-trunk-id

# Agent Configuration
AGENT_NAME=outbound_call_agent
OPENAI_API_KEY=your-openai-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key
CARTESIA_API_KEY=your-cartesia-api-key

# Optional
TEST_ADDRESS="123 Oak Street, Springfield, IL 62701"
FLASK_ENV=development
PORT=5000
```

## API Documentation

### Base URL
- Local: `http://localhost:5000`
- Production: `https://your-app.onrender.com`

### Authentication
All API requests require an `X-API-Key` header:

```bash
X-API-Key: your-secure-api-key-here
```

### Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "service": "outbound-call-dispatcher"
}
```

#### 2. Dispatch Outbound Call
```http
POST /api/v1/dispatch-call
Content-Type: application/json
X-API-Key: your-secure-api-key-here
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+12125551234",
  "address": "456 Main Street, Chicago, IL 60601"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "call_id": "outbound_call_12125551234_john_smith_20240115_143022",
  "lead_id": "john_smith_20240115_143022",
  "phone_number": "+12125551234",
  "customer_name": "John Smith",
  "address": "456 Main Street, Chicago, IL 60601",
  "message": "Call dispatched successfully to John Smith",
  "timestamp": "2024-01-15T14:30:22.000Z"
}
```

**Error Response (400 - Validation Error):**
```json
{
  "success": false,
  "error": "Validation error",
  "message": "Missing required field: first_name"
}
```

**Error Response (401 - Authentication Error):**
```json
{
  "success": false,
  "error": "Invalid or missing API key",
  "message": "Please provide a valid X-API-Key header"
}
```

**Error Response (500 - Dispatch Failed):**
```json
{
  "success": false,
  "error": "Dispatch failed",
  "message": "Failed to dispatch call to +12125551234",
  "phone_number": "+12125551234"
}
```

## Integration Examples

### cURL Example
```bash
curl -X POST https://your-app.onrender.com/api/v1/dispatch-call \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-secure-api-key-here" \\
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "phone_number": "2125551234",
    "address": "456 Main Street, Chicago, IL 60601"
  }'
```

### Zapier Integration

1. **Create a Webhook Action**
   - URL: `https://your-app.onrender.com/api/v1/dispatch-call`
   - Method: `POST`
   - Headers: `X-API-Key: your-secure-api-key-here`

2. **Configure the Payload**
   ```json
   {
     "first_name": "{{lead_first_name}}",
     "last_name": "{{lead_last_name}}",
     "phone_number": "{{lead_phone}}",
     "address": "{{lead_address}}"
   }
   ```

3. **Handle the Response**
   - Success: Use `call_id` for tracking
   - Error: Handle based on `error` field

### Python Integration
```python
import requests

url = "https://your-app.onrender.com/api/v1/dispatch-call"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-secure-api-key-here"
}
data = {
    "first_name": "John",
    "last_name": "Smith",
    "phone_number": "+12125551234",
    "address": "456 Main Street, Chicago, IL 60601"
}

response = requests.post(url, json=data, headers=headers)
result = response.json()

if result.get("success"):
    print(f"Call dispatched! Call ID: {result['call_id']}")
else:
    print(f"Error: {result.get('message')}")
```

## Phone Number Format

The API accepts US phone numbers in various formats:
- `+12125551234` (preferred)
- `12125551234`
- `2125551234`
- `(212) 555-1234`
- `212-555-1234`

All numbers are validated and converted to E.164 format (+1XXXXXXXXXX).

## Deployment

### Render Deployment

1. **Connect Your GitHub Repository**
   - Fork or push this code to GitHub
   - Connect your GitHub account to Render

2. **Create a New Web Service**
   - Select your repository
   - Choose "Web Service"
   - Use the `render.yaml` configuration

3. **Set Environment Variables**
   Set these in the Render dashboard:
   - `API_KEY`
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `SIP_OUTBOUND_TRUNK_ID`
   - `OPENAI_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `CARTESIA_API_KEY`

4. **Deploy**
   - Render will automatically build and deploy your service
   - Your API will be available at `https://your-app-name.onrender.com`

### Manual Deployment (Heroku, etc.)

```bash
# Install dependencies
pip install -r web_requirements.txt

# Set environment variables
export API_KEY=your-secure-api-key-here
export LIVEKIT_URL=wss://your-livekit-server
# ... (set all required env vars)

# Run with Gunicorn
gunicorn --bind 0.0.0.0:$PORT web_service:app
```

## Security Considerations

- 🔑 **API Key**: Use a strong, unique API key and rotate it regularly
- 🌐 **HTTPS**: Always use HTTPS in production
- 🚫 **Rate Limiting**: Consider implementing rate limiting for production use
- 📝 **Logging**: Monitor API usage and failed requests
- 🔒 **Environment Variables**: Never commit secrets to version control

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check your API key in the `X-API-Key` header
   - Ensure the API key matches the `API_KEY` environment variable

2. **400 Invalid Phone Number**
   - Ensure phone number is a valid US number
   - Check format: +1XXXXXXXXXX

3. **500 Dispatch Failed**
   - Verify LiveKit and SIP configuration
   - Check environment variables are set correctly
   - Review server logs for detailed error messages

### Logs

Check application logs for detailed error information:
```bash
# Local development
python web_service.py

# Production (Render)
# View logs in the Render dashboard
```

## Development

### Project Structure
```
/agent/
├── web_service.py          # Flask API service
├── dispatch_call.py        # Core dispatch functionality
├── web_requirements.txt    # Web service dependencies
├── requirements.txt        # Agent dependencies
├── render.yaml            # Render deployment config
├── .gitignore            # Git exclusions
└── README.md             # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the application logs
3. Create an issue in the GitHub repository

## License

This project is part of the Floor Covering International outbound calling system.