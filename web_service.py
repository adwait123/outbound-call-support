#!/usr/bin/env python3
"""
Web Service for Outbound Call Dispatch - Zapier Integration

This Flask web service exposes the outbound calling functionality as a REST API
for integration with Zapier workflows and other automation tools.
"""

import os
import json
import logging
import subprocess
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime

from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

# Import existing dispatch functionality
from dispatch_call import validate_phone_number, create_dispatch_command

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")
TEST_ADDRESS = os.getenv("TEST_ADDRESS", "123 Oak Street, Springfield, IL 62701")


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            return jsonify({
                'success': False,
                'error': 'Invalid or missing API key',
                'message': 'Please provide a valid X-API-Key header'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def validate_request_data(data: Dict[str, Any]) -> Optional[str]:
    """Validate incoming request data."""
    required_fields = ['first_name', 'last_name', 'phone_number']

    for field in required_fields:
        if not data.get(field):
            return f"Missing required field: {field}"

    # Additional validation
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()

    if len(first_name) < 1 or len(last_name) < 1:
        return "First name and last name must be at least 1 character"

    if len(first_name) > 50 or len(last_name) > 50:
        return "Names must be less than 50 characters"

    return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'outbound-call-dispatcher'
    })


@app.route('/api/v1/dispatch-call', methods=['POST'])
@require_api_key
def dispatch_call():
    """
    Dispatch an outbound call to a potential customer.

    Expected JSON payload:
    {
        "first_name": "John",
        "last_name": "Smith",
        "phone_number": "+12125551234",
        "address": "123 Main St, Springfield, IL 62701" (optional)
    }
    """
    try:
        # Parse JSON data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400

        data = request.get_json()

        # Validate request data
        validation_error = validate_request_data(data)
        if validation_error:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'message': validation_error
            }), 400

        # Extract and clean data
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        phone_number = data['phone_number'].strip()
        address = data.get('address', TEST_ADDRESS).strip()

        # Validate phone number
        validated_phone = validate_phone_number(phone_number)
        if not validated_phone:
            return jsonify({
                'success': False,
                'error': 'Invalid phone number',
                'message': f'Phone number {phone_number} is not a valid US phone number'
            }), 400

        # Generate lead ID and room name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lead_id = f"{first_name.lower()}_{last_name.lower()}_{timestamp}"
        room_name = f"outbound_call_{validated_phone.replace('+', '').replace('-', '')}_{lead_id}"

        # Create metadata for the call
        metadata = {
            "phone_number": validated_phone,
            "lead_id": lead_id,
            "call_type": "sales_outbound",
            "agent_name": "Jack",
            "customer_info": {
                "first_name": first_name,
                "last_name": last_name,
                "address": address
            },
            "initiated_via": "web_api",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Get agent name from environment
        agent_name = os.getenv("AGENT_NAME", "outbound_call_agent")

        # Create LiveKit API client
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

        if not all([livekit_url, livekit_api_key, livekit_api_secret]):
            logger.error("Missing LiveKit credentials")
            return jsonify({
                'success': False,
                'error': 'Configuration error',
                'message': 'LiveKit credentials not configured'
            }), 500

        try:
            # Set up environment for lk CLI command
            env = os.environ.copy()
            env.update({
                'LIVEKIT_URL': livekit_url,
                'LIVEKIT_API_KEY': livekit_api_key,
                'LIVEKIT_API_SECRET': livekit_api_secret
            })

            # Build LiveKit CLI command
            command = [
                'lk', 'dispatch', 'create',
                '--new-room',
                '--room', room_name,
                '--agent-name', agent_name,
                '--metadata', json.dumps(metadata)
            ]

            logger.info(f"Dispatching call to: {validated_phone} for {first_name} {last_name}")
            logger.info(f"Command: {' '.join(command)}")

            # Execute the command using subprocess
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Dispatch successful: {result.stdout}")
                dispatch_success = True
            else:
                logger.error(f"Command failed with code {result.returncode}: {result.stderr}")
                dispatch_success = False

        except subprocess.TimeoutExpired:
            logger.error("LiveKit dispatch command timed out")
            dispatch_success = False
        except FileNotFoundError:
            logger.error("LiveKit CLI (lk) not found - trying alternative installation...")
            # Try different installation methods for LiveKit CLI
            try:
                # Try installing via different methods
                install_commands = [
                    ['npm', 'install', '-g', 'livekit-cli'],  # Alternative package name
                    ['npm', 'install', '-g', '@livekit/livekit-cli'],  # Another alternative
                    ['curl', '-sSL', 'https://github.com/livekit/livekit-cli/releases/latest/download/lk_linux_amd64', '-o', '/tmp/lk'],  # Direct binary
                ]

                installation_success = False
                for install_cmd in install_commands:
                    try:
                        logger.info(f"Trying installation: {' '.join(install_cmd)}")
                        if install_cmd[0] == 'curl':
                            # Download binary directly
                            subprocess.run(install_cmd, timeout=60, check=True)
                            subprocess.run(['chmod', '+x', '/tmp/lk'], timeout=10, check=True)
                            # Update command to use downloaded binary
                            command[0] = '/tmp/lk'
                        else:
                            subprocess.run(install_cmd, timeout=60, check=True)
                        installation_success = True
                        logger.info(f"Installation successful: {' '.join(install_cmd)}")
                        break
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                        logger.warning(f"Installation method failed: {e}")
                        continue

                if installation_success:
                    # Retry the dispatch after installation
                    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
                    dispatch_success = result.returncode == 0
                    if dispatch_success:
                        logger.info(f"Dispatch successful after CLI installation: {result.stdout}")
                    else:
                        logger.error(f"Command failed after CLI installation: {result.stderr}")
                else:
                    logger.error("All CLI installation methods failed")
                    dispatch_success = False

            except Exception as install_error:
                logger.error(f"Failed to install LiveKit CLI: {install_error}")
                dispatch_success = False
        except Exception as e:
            logger.error(f"LiveKit dispatch failed: {str(e)}")
            dispatch_success = False

        if dispatch_success:
            # Success response
            response_data = {
                'success': True,
                'call_id': room_name,
                'lead_id': lead_id,
                'phone_number': validated_phone,
                'customer_name': f"{first_name} {last_name}",
                'address': address,
                'message': f'Call dispatched successfully to {first_name} {last_name}',
                'timestamp': datetime.utcnow().isoformat()
            }

            logger.info(f"Call dispatched successfully: {room_name}")
            return jsonify(response_data), 200

        else:
            # Dispatch failed
            error_msg = f'Failed to dispatch call to {validated_phone}'
            logger.error(f"Dispatch failed: {error_msg}")

            return jsonify({
                'success': False,
                'error': 'Dispatch failed',
                'message': error_msg,
                'phone_number': validated_phone
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in dispatch_call: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while processing the request'
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested endpoint does not exist'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


if __name__ == '__main__':
    # Check required environment variables
    required_env_vars = [
        'SIP_OUTBOUND_TRUNK_ID',
        'LIVEKIT_URL',
        'LIVEKIT_API_KEY',
        'LIVEKIT_API_SECRET'
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)

    # Development server
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"

    logger.info(f"Starting web service on port {port}")
    logger.info(f"Health check available at: http://localhost:{port}/health")
    logger.info(f"API endpoint available at: http://localhost:{port}/api/v1/dispatch-call")

    app.run(host='0.0.0.0', port=port, debug=debug)