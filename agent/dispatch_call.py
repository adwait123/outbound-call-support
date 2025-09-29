#!/usr/bin/env python3
"""
Outbound Call Dispatcher for Floor Covering International Sales Agent

This script triggers outbound calls using LiveKit SIP dispatch API.
Calls are made to potential customers to schedule design consultations.
"""

import os
import json
import sys
import argparse
import re
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_phone_number(phone: str) -> Optional[str]:
    """
    Validate and format phone number for outbound calling.

    Args:
        phone (str): Phone number to validate

    Returns:
        Optional[str]: Formatted phone number or None if invalid
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'[^\d]', '', phone)

    # Handle US numbers
    if len(digits_only) == 10:
        # Add US country code
        formatted = f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # Already has US country code
        formatted = f"+{digits_only}"
    else:
        return None

    # Validate US phone number format
    if re.match(r'^\+1[2-9]\d{2}[2-9]\d{6}$', formatted):
        return formatted
    else:
        return None

def create_dispatch_command(phone_number: str, lead_id: Optional[str] = None) -> str:
    """
    Create LiveKit dispatch command for outbound call.

    Args:
        phone_number (str): Validated phone number
        lead_id (str, optional): Lead identifier

    Returns:
        str: LiveKit CLI dispatch command
    """
    # Generate unique room name
    room_name = f"outbound_call_{phone_number.replace('+', '').replace('-', '')}_{lead_id or 'manual'}"

    # Create metadata with phone number
    metadata = {
        "phone_number": phone_number,
        "lead_id": lead_id or f"manual_{phone_number.replace('+', '')}",
        "call_type": "sales_outbound",
        "agent_name": "Jack"
    }

    # Build LiveKit CLI command
    agent_name = os.getenv("AGENT_NAME", "outbound_call_agent")

    command = f"lk dispatch create --new-room --room-name {room_name} --agent-name {agent_name} --metadata '{json.dumps(metadata)}'"

    return command

def dispatch_single_call(phone_number: str, lead_id: Optional[str] = None, execute: bool = False) -> bool:
    """
    Dispatch a single outbound call.

    Args:
        phone_number (str): Phone number to call
        lead_id (str, optional): Lead identifier
        execute (bool): Whether to execute the command or just print it

    Returns:
        bool: Success status
    """
    # Validate phone number
    validated_phone = validate_phone_number(phone_number)
    if not validated_phone:
        print(f"❌ Invalid phone number: {phone_number}")
        return False

    print(f"📞 Preparing call to: {validated_phone}")

    # Create dispatch command
    command = create_dispatch_command(validated_phone, lead_id)

    if execute:
        print(f"🚀 Executing: {command}")
        result = os.system(command)
        if result == 0:
            print(f"✅ Call dispatched successfully to {validated_phone}")
            return True
        else:
            print(f"❌ Failed to dispatch call to {validated_phone}")
            return False
    else:
        print(f"🔍 Command to execute: {command}")
        print("💡 Add --execute to actually make the call")
        return True

def dispatch_batch_calls(phone_list: list, execute: bool = False) -> None:
    """
    Dispatch multiple outbound calls from a list.

    Args:
        phone_list (list): List of phone numbers or (phone, lead_id) tuples
        execute (bool): Whether to execute commands or just print them
    """
    success_count = 0
    total_count = len(phone_list)

    print(f"📋 Processing {total_count} outbound calls...")

    for i, item in enumerate(phone_list, 1):
        print(f"\n--- Call {i}/{total_count} ---")

        if isinstance(item, tuple):
            phone, lead_id = item
        else:
            phone, lead_id = item, None

        success = dispatch_single_call(phone, lead_id, execute)
        if success:
            success_count += 1

    print(f"\n📊 Results: {success_count}/{total_count} calls processed successfully")

def main():
    parser = argparse.ArgumentParser(description="Dispatch outbound sales calls")
    parser.add_argument("phone", nargs="?", help="Phone number to call")
    parser.add_argument("--lead-id", help="Lead ID for tracking")
    parser.add_argument("--batch", help="File containing phone numbers (one per line)")
    parser.add_argument("--execute", action="store_true", help="Actually execute the calls (default: dry run)")

    args = parser.parse_args()

    # Check environment
    if not os.getenv("SIP_OUTBOUND_TRUNK_ID"):
        print("❌ Error: SIP_OUTBOUND_TRUNK_ID not found in environment")
        sys.exit(1)

    if not os.getenv("LIVEKIT_URL") or not os.getenv("LIVEKIT_API_KEY"):
        print("❌ Error: LiveKit credentials not found in environment")
        sys.exit(1)

    print("🏢 Floor Covering International - Outbound Call Dispatcher")
    print("=" * 60)

    if args.batch:
        # Batch calling from file
        try:
            with open(args.batch, 'r') as f:
                phone_list = [line.strip() for line in f if line.strip()]
            dispatch_batch_calls(phone_list, args.execute)
        except FileNotFoundError:
            print(f"❌ Error: File {args.batch} not found")
            sys.exit(1)
    elif args.phone:
        # Single call
        dispatch_single_call(args.phone, args.lead_id, args.execute)
    else:
        # Interactive mode
        print("📞 Interactive Mode - Enter phone numbers to call")
        print("💡 Type 'quit' to exit")

        while True:
            try:
                phone = input("\nPhone number: ").strip()
                if phone.lower() in ['quit', 'exit', 'q']:
                    break

                lead_id = input("Lead ID (optional): ").strip() or None
                dispatch_single_call(phone, lead_id, args.execute)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break

if __name__ == "__main__":
    main()