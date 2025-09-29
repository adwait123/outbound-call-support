# Quick Start Guide - Outbound Call Dispatcher API

🚀 **Ready to integrate with Zapier and other automation tools!**

## 📁 New Files Created

```
/agent/
├── web_service.py          ✅ Flask REST API service
├── web_requirements.txt    ✅ Web service dependencies
├── test_api.py            ✅ API testing script
├── start_web_service.sh   ✅ Easy startup script
├── render.yaml           ✅ Render deployment config
├── .gitignore           ✅ Git exclusions (.env protected)
├── README.md            ✅ Complete API documentation
└── API_QUICKSTART.md    ✅ This quick start guide
```

## 🏃‍♂️ Quick Start (3 steps)

### 1. Start the Service
```bash
cd /Users/adwait/PycharmProjects/outbound_call_support/agent
./start_web_service.sh
```

### 2. Test the API
```bash
# In another terminal
python test_api.py
```

### 3. Make Your First Call
```bash
curl -X POST http://localhost:5000/api/v1/dispatch-call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-api-key-change-this-in-production" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "phone_number": "2125551234",
    "address": "456 Main St, Chicago, IL 60601"
  }'
```

## 🔌 Zapier Integration

### Webhook URL
```
http://localhost:5000/api/v1/dispatch-call
```

### Headers
```
X-API-Key: secure-api-key-change-this-in-production
Content-Type: application/json
```

### Payload
```json
{
  "first_name": "{{first_name}}",
  "last_name": "{{last_name}}",
  "phone_number": "{{phone}}",
  "address": "{{address}}"
}
```

## 🚀 Deploy to Render

1. **Push to GitHub** (your .env file won't be included thanks to .gitignore)
2. **Create new Web Service** on Render
3. **Connect your GitHub repo**
4. **Set environment variables** in Render dashboard:
   - `API_KEY`
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `SIP_OUTBOUND_TRUNK_ID`
   - `OPENAI_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `CARTESIA_API_KEY`

5. **Deploy!** - Render will use the `render.yaml` configuration

## 🔧 Environment Variables Added

Check your `.env` file - these were added:
- `API_KEY='secure-api-key-change-this-in-production'`
- `TEST_ADDRESS='123 Oak Street, Springfield, IL 62701'`

## 📊 Response Format

### Success
```json
{
  "success": true,
  "call_id": "outbound_call_12125551234_john_smith_20240115_143022",
  "phone_number": "+12125551234",
  "customer_name": "John Smith",
  "message": "Call dispatched successfully to John Smith"
}
```

### Error
```json
{
  "success": false,
  "error": "Validation error",
  "message": "Missing required field: first_name"
}
```

## 📞 Phone Number Formats Supported
- `+12125551234` ✅
- `12125551234` ✅
- `2125551234` ✅
- `(212) 555-1234` ✅
- `212-555-1234` ✅

## 🛡️ Security Features
- ✅ API Key authentication
- ✅ Input validation
- ✅ Phone number validation
- ✅ Environment variable protection
- ✅ Error handling without info leakage

---

**🎉 Your outbound calling API is ready for Zapier integration!**

For complete documentation, see `README.md`