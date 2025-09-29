# Outbound Calling Setup - Floor Covering International Sales Agent

## Overview
The agent is now configured to make outbound sales calls using LiveKit SIP dispatch and your Twilio trunk.

## Quick Start

### 1. Make a Single Call
```bash
# Dry run (shows command without executing)
python dispatch_call.py +12125551234 --lead-id customer123

# Actually make the call
python dispatch_call.py +12125551234 --lead-id customer123 --execute
```

### 2. Batch Calling
```bash
# Create a file with phone numbers
echo "+12125551234" > leads.txt
echo "+13105554567" >> leads.txt

# Dispatch batch calls
python dispatch_call.py --batch leads.txt --execute
```

### 3. Interactive Mode
```bash
python dispatch_call.py
# Follow prompts to enter phone numbers manually
```

## How It Works

### Call Flow
1. **Dispatch**: `dispatch_call.py` creates LiveKit dispatch with phone number metadata
2. **Agent Startup**: Agent detects outbound call via `phone_number` in metadata
3. **SIP Connection**: Agent creates SIP participant using your `SIP_OUTBOUND_TRUNK_ID`
4. **Call Placement**: LiveKit dials the customer via Twilio
5. **Sales Script**: Jack starts the Floor Covering International sales workflow

### Agent Behavior
- **Outbound Calls**: Waits for customer to answer, then starts sales script
- **Console Mode**: Starts immediately for testing
- **Error Handling**: Validates phone numbers and SIP configuration

## Environment Variables Required
```bash
SIP_OUTBOUND_TRUNK_ID=ST_qywyMKzxScLr    # Your trunk ID
LIVEKIT_URL=wss://your-livekit-server     # LiveKit server
LIVEKIT_API_KEY=your-api-key              # LiveKit API key
LIVEKIT_API_SECRET=your-api-secret        # LiveKit API secret
AGENT_NAME=outbound_call_agent            # Agent identifier
```

## Phone Number Format
- Must be US numbers: `+1XXXXXXXXXX`
- Valid area codes (2-9 for first digit)
- Valid exchange codes (2-9 for first digit)
- Example: `+12125551234` ✅
- Invalid: `+15551234567` ❌ (555 area code)

## Testing

### Console Testing
```bash
# Test the agent in console mode
source .agent_venv/bin/activate
python src/agent.py console
```

### Validate Dispatch Commands
```bash
# See what command would be executed
python dispatch_call.py +12125551234
```

### Check SIP Trunk
```bash
# Verify your trunk is configured
lk sip outbound list
```

## Sales Workflow

The agent follows this conversation flow:

1. **Opening**: "Hi, this is Jack from Floor Covering International..."
2. **Lead Validation**: Confirms web form submission
3. **Address Confirmation**: Verifies consultation address
4. **Project Details**: Confirms flooring project type
5. **Appointment Scheduling**: Presents 3 available time slots
6. **Booking**: Secures appointment and provides confirmation
7. **SMS Follow-up**: Promises text confirmation in 15-20 minutes

## Troubleshooting

### Common Issues
- **Invalid phone number**: Check format (+1XXXXXXXXXX)
- **SIP trunk not found**: Verify `SIP_OUTBOUND_TRUNK_ID`
- **Permission denied**: Check LiveKit API credentials
- **Call fails**: Verify Twilio trunk configuration

### Logs
Agent logs include:
- `Starting outbound call to: +1XXXXXXXXXX`
- `SIP participant created successfully`
- `Error creating SIP participant: [error]`

### Manual Testing
```bash
# Direct LiveKit CLI dispatch
lk dispatch create --new-room --agent-name outbound_call_agent --metadata '{"phone_number": "+12125551234"}'
```

## Production Deployment

1. **Scale Worker**: Run `python src/agent.py start` on production server
2. **Batch Processing**: Use cron jobs with batch calling
3. **Lead Integration**: Connect dispatch script to your CRM
4. **Monitoring**: Monitor LiveKit dashboard for call success rates

## Integration Examples

### CRM Integration
```python
# Example: Call leads from database
import sqlite3
leads = get_pending_leads_from_db()
for lead in leads:
    dispatch_single_call(lead.phone, lead.id, execute=True)
```

### Webhook Integration
```python
# Example: Trigger calls from webhooks
@app.route('/call-lead', methods=['POST'])
def trigger_call():
    phone = request.json['phone']
    lead_id = request.json['lead_id']
    result = dispatch_single_call(phone, lead_id, execute=True)
    return {'success': result}
```