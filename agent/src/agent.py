import os
from typing import AsyncIterable, cast
import textwrap

from dotenv import load_dotenv
import logging
import json
from dataclasses import asdict
import asyncio

from livekit import agents, rtc
from livekit.plugins import deepgram, openai, cartesia, silero, noise_cancellation
from livekit.plugins.turn_detector.english import EnglishModel

from utils import session, tracing, fetching, common

load_dotenv()

logger: logging.Logger = logging.getLogger(os.getenv("AGENT_NAME"))


class Assistant(agents.Agent):
    def __init__(self, room: rtc.Room, is_sip_session: bool = False) -> None:
        super().__init__(
            instructions=textwrap.dedent("""
                    You are Jack, the Floor Covering International Sales Assistant, an expert in helping potential clients schedule their Free In-Home Design Consultation. Your primary role is to validate the user's request, confirm appointment details, and secure a booking for a professional design consultant.

                    IMPORTANT: This is an outbound voice call. You are calling the customer who submitted a web form. Keep responses professional, confident, friendly, and persuasive. Use a clear, warm, and inviting tone suitable for a premium home services brand.

                    CRITICAL BEHAVIOR RULES:
                    - Be Proactive and Direct: Your goal is to move the user quickly and smoothly to a confirmed appointment
                    - Present Steps One at a Time: For any multi-step process, present information ONE step at a time
                    - Always Wait for User Confirmation: Never proceed without explicit verbal confirmation from the user
                    - REPEAT BACK UNCLEAR RESPONSES: If customer response seems unclear or contradictory, repeat what you heard: "I heard you say [X], is that correct?"
                    - CONFIRM BEFORE BOOKING: Always confirm appointment selection clearly: "Just to confirm, you chose [DATE] at [TIME], is that right?"
                    - CONFIRM EVERY NEW INFORMATION: After receiving ANY new information from the customer (address changes, project details, preferences), immediately confirm by repeating it back: "Got it, so that's [INFORMATION], is that correct?"
                    - SPELL OUT ALL NUMBERS: For ZIP codes, phone numbers, and addresses, spell out each digit individually. Say "six-two-seven-one" instead of "six thousand two hundred seventy-one"
                    - Be Crisp and Confident: Maintain an expert tone suitable for a high-quality service
                    - Keep Responses Suitable for Speech: Use conversational language with no special formatting
                    - Use Brand Language: Use terms like "Free In-Home Design Consultation," "design consultant," and "Floor Covering International"

                    SALES & SCHEDULING WORKFLOW:
                    1. Opening and Lead Validation:
                       Begin immediately: "Hi, this is Jack from Floor Covering International. I see you recently submitted a request to quote on Yelp. Is that right, and do you still have a few minutes to confirm your appointment details?"
                       WAIT for confirmation.

                    2. Information Confirmation:
                       Call confirm_lead_details to verify the address and project type.
                       Confirm address: "Great. I have your consultation address as [ADDRESS]. Is that correct?"
                       WAIT for confirmation. If customer provides corrections, immediately repeat back: "Got it, so the correct address is [NEW ADDRESS], is that right?"
                       Confirm project: "And this consultation is for [PROJECT_TYPE]? That will help our consultant prepare."
                       WAIT for confirmation. If customer provides new details, immediately repeat back: "Perfect, so this is for [NEW PROJECT_TYPE], correct?"

                    3. Material Provision Validation:
                       Ask: "One quick question - will you be providing the flooring materials for this job, or would you like us to handle everything including materials?"
                       WAIT for response.
                       - If customer says they will provide materials:
                         First attempt: "I understand you have materials in mind. However, would you be open to reconsidering? We have access to exclusive designer collections and premium materials that aren't available to the public, plus we offer comprehensive warranties when we handle both materials and installation. Would you be interested in hearing about our material options during a consultation?"
                         WAIT for response.
                         - If customer is open to reconsidering: Continue to appointment scheduling.
                         - If customer still insists on providing materials: "I understand. Unfortunately, we specialize in full-service installations where we provide both materials and installation to ensure quality and warranty coverage. Thank you for your time, and best of luck with your project."
                       - If customer wants Floor Covering International to provide materials: Continue to appointment scheduling.

                    4. Appointment Scheduling:
                       Call generate_appointment_slots with the confirmed details.
                       Present exactly TWO options initially: "Fantastic. We have a design consultant available to visit you on [DATE_1] at [TIME_1], or [DATE_2] at [TIME_2]. Which works better for you?"
                       ONLY provide additional options if customer asks for more choices.
                       WAIT for their selection. Immediately confirm their choice: "Perfect, so you've chosen [SELECTED_DATE] at [SELECTED_TIME], is that correct?"

                    5. Confirmation and Wrap-Up:
                       Call book_appointment to secure the time.
                       Provide summary: "Excellent. I have secured your Free In-Home Design Consultation for [DAY], [DATE] at [TIME] at [ADDRESS]. Your consultant will be arriving with hundreds of samples."
                       Conclude: "You'll receive a confirmation text message with all these details in the next 15-20 minutes. Is there anything else I can help you with today?"

                    EXCEPTION HANDLING:
                    - No Available Slots: "I apologize, those exact times didn't work. I can have our local scheduling manager call you back within the next hour to personally secure a time that works best. Would that be helpful?" If yes, call raise_callback_request.
                    - User No Longer Interested: "I understand. Thank you for letting us know. If you change your mind, you can always reach us directly. We appreciate your time."
                    - Incorrect Information: "Not a problem, I can quickly update that. What is the correct [DETAIL]?" Continue from step 2.

                    SALES TOOLS:
                    - confirm_lead_details: Verify address and project type from web form
                    - generate_appointment_slots: Generate available appointment times
                    - book_appointment: Secure the selected appointment slot
                    - raise_callback_request: Handle callback requests for scheduling conflicts
            """),
            stt=deepgram.STT(
                model="nova-2",
                language="en-US",
                smart_format=True,
                interim_results=False,
                filler_words=False,
                punctuate=True,
                profanity_filter=False,
                redact=False
            ),
            llm=openai.LLM(
                model="gpt-4.1",
                parallel_tool_calls=False,
                temperature=0.3,
                max_tokens=150
            ),
            tts=cartesia.TTS(
                model="sonic-2",
                voice="146485fd-8736-41c7-88a8-7cdd0da34d84",
                language="en",
                speed=1.1,
                sample_rate=24000,
                encoding="pcm_s16le",
            ),
            vad=silero.VAD.load(),
            turn_detection=EnglishModel(),
        )
        self.room = room

    async def on_enter(self):
        logger.info(f"on_enter: Agent started now for user: {self.session.userdata.user_id}")
        logger.info(f"on_enter: User info: {self.session.userdata.country}, {self.session.userdata.app_version}")

        # Check if this is an outbound call (sales lead vs console/inbound)
        is_outbound_call = self.session.userdata.app_version == "outbound_sales"

        selected_keys = {"user_id", "country", "app_version", "all_devices"}
        user_data = {k: v for k, v in asdict(self.session.userdata).items() if k in selected_keys}

        # For outbound calls, skip business rules fetching to avoid errors
        if is_outbound_call:
            business_rules = "Focus on scheduling appointments efficiently and professionally."
        else:
            business_rules = fetching.fetch_business_rules()

        # Add context instructions
        chat_ctx = self.chat_ctx.copy()

        # Extract customer info for outbound calls
        customer_context = ""
        if is_outbound_call:
            # Access room metadata to get customer info
            room_metadata = getattr(self.room, 'metadata', {})
            if room_metadata:
                try:
                    # Parse room metadata to get customer info
                    import json
                    if isinstance(room_metadata, str):
                        metadata_dict = json.loads(room_metadata)
                    else:
                        metadata_dict = room_metadata

                    customer_info = metadata_dict.get("customer_info", {})
                    if customer_info:
                        first_name = customer_info.get("first_name", "")
                        last_name = customer_info.get("last_name", "")
                        address = customer_info.get("address", "")
                        project_info = customer_info.get("project_info", "")

                        customer_context = f"""
                        CUSTOMER INFORMATION (from lead):
                        - First Name: {first_name}
                        - Last Name: {last_name}
                        - Address: {address}
                        - Project Info: {project_info}

                        GREETING PROTOCOL:
                        1. Start with: "Hi, I am Jack from Floor Covering International. Is this {first_name}?"
                        2. Wait for confirmation (Yes/No)
                        3. If YES: Proceed with sales flow
                        4. If NO: Ask to speak with {first_name} or politely end call

                        OPTION PRESENTATION STRATEGY:
                        - Start with only 2 main options when presenting choices
                        - Only provide additional options if customer specifically asks for more
                        - Keep initial choices simple and clear
                        """
                except:
                    customer_context = ""

        chat_ctx.add_message(
            role="system",  # role=system works for OpenAI's LLM and Realtime API
            content=textwrap.dedent(f"""
                Current user data: {user_data}.

                {customer_context}

                Follow these business rules:
                {business_rules}
            """)
        )
        await self.update_chat_ctx(chat_ctx)

        logger.info(f"on_enter: Chat context: {chat_ctx}")

        if is_outbound_call:
            # For outbound calls, wait for customer to speak first, then start sales script
            await self.session.generate_reply(
                instructions=textwrap.dedent(f"""
                    You are Jack from Floor Covering International making an outbound call.
                    The customer should speak first since you called them.
                    Wait for them to say "Hello" or respond, then immediately follow the GREETING PROTOCOL:

                    Say: "Hi, I am Jack from Floor Covering International. Is this [CUSTOMER_FIRST_NAME]?"

                    IMPORTANT: Replace [CUSTOMER_FIRST_NAME] with the actual customer's first name from the lead information if available.

                    Wait for their confirmation:
                    - If YES: Continue with "Great! I see you recently submitted a request for a flooring quote. Do you have a few minutes to confirm your appointment details?"
                    - If NO: Ask "May I speak with [CUSTOMER_FIRST_NAME]?" or politely end the call

                    Only proceed with the sales flow after confirming you're speaking with the right person.
                """),
                allow_interruptions=True
            )
        else:
            # Console mode - start immediately
            await self.session.generate_reply(
                instructions=textwrap.dedent(f"""
                    You are Jack calling from Floor Covering International. The customer submitted a Request to quote on Yelp for a flooring job.
                    Start the conversation immediately with: "Hi, this is Jack from Floor Covering International. I see you recently submitted a Request to quote on Yelp for a flooring job. Is that right, and do you still have a few minutes to confirm your appointment details?"
                    Wait for their response before proceeding.
                """),
                allow_interruptions=True
            )

    async def on_exit(self) -> None:
        logger.info(f"on_exit: Agent exited")
        if self.session.userdata.consent_to_record:
            await session.notify_session_end(self.session.userdata)

    async def llm_node(
        self, chat_ctx: agents.ChatContext, tools: list[agents.FunctionTool], model_settings: agents.ModelSettings
    ):
        # not all LLMs support structured output, so we need to cast to the specific LLM type
        llm = cast(openai.LLM, self.llm)
        tool_choice = model_settings.tool_choice if model_settings else agents.NOT_GIVEN
        async with llm.chat(
            chat_ctx=chat_ctx,
            tools=tools,
            tool_choice=tool_choice,
            response_format=session.ResponseFormat,
        ) as stream:
            async for chunk in stream:
                yield chunk

    async def tts_node(self, text: AsyncIterable[str], model_settings: agents.ModelSettings):
        logger.info(f"tts_node: inside tts_node")
        return agents.Agent.default.tts_node(self, session.process_structured_output(text), model_settings)

    @agents.function_tool()
    async def save_consent_to_record(self, context: agents.RunContext, consent_to_record: bool, reasoning_for_tool_call: str) -> str:
        """
        Save the user consent to record the conversation.

        Args:
            consent_to_record (bool): The user's consent to record the conversation.
            reasoning_for_tool_call (str): The agent's reasoning for the tool call.

        Returns:
            str: success or failure.
        """
        self.session.userdata.consent_to_record = consent_to_record
        return json.dumps({"status": "success"})

    @agents.function_tool()
    async def confirm_lead_details(self, context: agents.RunContext, reasoning_for_tool_call: str) -> str:
        """
        Verify address and project type from the web form submission.

        Args:
            reasoning_for_tool_call (str): The agent's reasoning for the tool call.

        Returns:
            str: Lead details including address and project type.
        """
        # Dummy data for lead details
        lead_details = {
            "address": "123 Oak Street, Springfield, IL 62701",
            "project_type": "Living room carpet replacement",
            "submitted_date": "2024-01-15",
            "phone": "+1-555-123-4567",
            "email": "john.smith@email.com",
            "preferred_contact": "phone"
        }

        result_message = json.dumps({
            "status": "success",
            "lead_details": lead_details,
            "message": f"Lead details confirmed: {lead_details['address']} for {lead_details['project_type']}"
        })

        return result_message

    @agents.function_tool()
    async def generate_appointment_slots(self, context: agents.RunContext, address: str, project_type: str, reasoning_for_tool_call: str) -> str:
        """
        Generate available appointment time slots for design consultation.

        Args:
            address (str): The customer's address for the consultation.
            project_type (str): Type of flooring project.
            reasoning_for_tool_call (str): The agent's reasoning for the tool call.

        Returns:
            str: Available appointment slots.
        """
        from datetime import datetime, timedelta

        # Generate dummy appointment slots - next 3 business days
        today = datetime.now()
        slots = []

        # Find next 3 business days
        current_date = today + timedelta(days=1)
        while len(slots) < 3:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                day_name = current_date.strftime("%A")
                date_str = current_date.strftime("%B %d")

                # Morning and afternoon slots
                morning_time = "10:00 AM"
                afternoon_time = "2:00 PM"

                slots.append({
                    "day": day_name,
                    "date": date_str,
                    "time": morning_time,
                    "slot_id": f"slot_{len(slots)+1}"
                })

                if len(slots) < 3:
                    slots.append({
                        "day": day_name,
                        "date": date_str,
                        "time": afternoon_time,
                        "slot_id": f"slot_{len(slots)+1}"
                    })

            current_date += timedelta(days=1)

        # Return only the first 3 slots
        available_slots = slots[:3]

        result_message = json.dumps({
            "status": "success",
            "available_slots": available_slots,
            "message": f"Found {len(available_slots)} available consultation slots"
        })

        return result_message

    @agents.function_tool()
    async def book_appointment(self, context: agents.RunContext, slot_id: str, day: str, date: str, time: str, address: str, reasoning_for_tool_call: str) -> str:
        """
        Book the selected appointment slot for design consultation.

        Args:
            slot_id (str): Unique identifier for the selected appointment slot.
            day (str): Day of the week for the appointment.
            date (str): Date of the appointment.
            time (str): Time of the appointment.
            address (str): Customer's address for the consultation.
            reasoning_for_tool_call (str): The agent's reasoning for the tool call.

        Returns:
            str: Appointment booking confirmation.
        """
        import random

        # Generate dummy appointment confirmation
        appointment_id = f"FCI-{random.randint(10000, 99999)}"
        consultant_name = random.choice(["Sarah Johnson", "Mike Thompson", "Lisa Chen", "David Rodriguez"])

        booking_details = {
            "appointment_id": appointment_id,
            "day": day,
            "date": date,
            "time": time,
            "address": address,
            "consultant_name": consultant_name,
            "service_type": "Free In-Home Design Consultation",
            "duration": "60-90 minutes",
            "confirmation_sms": "Will be sent within 15-20 minutes"
        }

        result_message = json.dumps({
            "status": "success",
            "booking_details": booking_details,
            "message": f"Appointment successfully booked for {day}, {date} at {time}"
        })

        return result_message

    @agents.function_tool()
    async def raise_callback_request(self, context: agents.RunContext, customer_phone: str, preferred_time: str, reason: str, reasoning_for_tool_call: str) -> str:
        """
        Request a callback from the scheduling manager when no suitable appointment slots are available.

        Args:
            customer_phone (str): Customer's phone number for callback.
            preferred_time (str): Customer's preferred callback time.
            reason (str): Reason for callback (e.g., no available slots).
            reasoning_for_tool_call (str): The agent's reasoning for the tool call.

        Returns:
            str: Callback request confirmation.
        """
        import random
        from datetime import datetime, timedelta

        # Generate dummy callback request details
        callback_id = f"CB-{random.randint(10000, 99999)}"
        callback_time = datetime.now() + timedelta(minutes=random.randint(30, 60))
        manager_name = random.choice(["Jennifer Adams", "Robert Martinez", "Susan Williams", "Michael Brown"])

        callback_details = {
            "callback_id": callback_id,
            "customer_phone": customer_phone,
            "scheduled_callback_time": callback_time.strftime("%I:%M %p"),
            "manager_name": manager_name,
            "reason": reason,
            "status": "scheduled",
            "priority": "high"
        }

        result_message = json.dumps({
            "status": "success",
            "callback_details": callback_details,
            "message": f"Callback scheduled with {manager_name} within the next hour at {callback_time.strftime('%I:%M %p')}"
        })

        return result_message


async def entrypoint(ctx: agents.JobContext):
    # Initialize trace system first
    await tracing.init_trace_system()

    # Add shutdown callback for cleanup
    ctx.add_shutdown_callback(session.on_shutdown)

    try:
        metadata = json.loads(ctx.job.metadata)
    except:
        metadata = {"identity": "sales-lead"}
    logger.info(f"metadata: {metadata}")

    # Check if this is an outbound call (has phone_number in metadata)
    is_outbound_call = "phone_number" in metadata
    phone_number = metadata.get("phone_number")

    if is_outbound_call and phone_number:
        logger.info(f"Starting outbound call to: {phone_number}")

        # Connect to establish room connection
        await ctx.connect()

        try:
            # Validate phone number format
            import re
            if not re.match(r'^\+1[2-9]\d{2}[2-9]\d{6}$', phone_number):
                raise ValueError(f"Invalid phone number format: {phone_number}")

            # Validate SIP trunk ID
            sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
            if not sip_trunk_id:
                raise ValueError("SIP_OUTBOUND_TRUNK_ID not configured")

            # Create SIP participant for outbound call
            from livekit import api
            await ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone_number,
                participant_identity=f"customer_{phone_number.replace('+', '').replace('-', '')}",
                wait_until_answered=True
            ))
            logger.info(f"SIP participant created successfully for {phone_number}")

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            ctx.shutdown()
            return
        except api.TwirpError as e:
            logger.error(f"SIP API error: {e.message}")
            ctx.shutdown()
            return
        except Exception as e:
            logger.error(f"Unexpected error creating SIP participant: {e}")
            ctx.shutdown()
            return

        # Wait for participant to join
        participant: rtc.Participant = await ctx.wait_for_participant()
        is_sip_session = True

        # For outbound calls, use metadata for user info
        user_id = f"lead_{phone_number.replace('+', '').replace('-', '')}"
        user_info = {
            "all_devices": {},  # No devices for sales leads
            "country": "US",
            "app_version": "outbound_sales"
        }
        tenant_id = None
        conversation_id = metadata.get("conversation_id")
    else:
        # Original inbound/console logic
        # parse metadata from the Livekit token
        mock_log_guidance = json.loads(metadata["mock_log_guidance"]) if "mock_log_guidance" in metadata else None
        modalities = metadata["modalities"] if "modalities" in metadata else "text_and_audio"
        conversation_id = metadata.get("conversation_id")

        # Gather user information from metadata, if available
        user_id = None
        user_info = {}
        tenant_id = None
        if "identity" in metadata:
            user_id = metadata["identity"]
            user_info = fetching.fetch_user_info(user_id)

        # Extract tenant_id from metadata (provided by SDK)
        if "tenant_id" in metadata:
            tenant_id = metadata["tenant_id"]

        # Connect to establish room connection
        await ctx.connect()

        # Get participants and their info
        participant: rtc.Participant = await ctx.wait_for_participant()

        is_sip_session = False
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            is_sip_session = True
            # for SIP, Livekit token doesn't exist; therefore, metadata also doesn't exist;
            user_phone_number = participant.attributes['sip.phoneNumber']  # e.g. "+15105550100"
            logger.info(f"Phone number: {user_phone_number}")
            user_id = fetching.fetch_user_id_from_phone_number(user_phone_number)
            user_info = fetching.fetch_user_info(user_id)

    # Build and start the session
    mock_log_guidance = metadata.get("mock_log_guidance", None)
    if mock_log_guidance and isinstance(mock_log_guidance, str):
        mock_log_guidance = json.loads(mock_log_guidance)

    my_session_info = session.MySessionInfo(
        conversation_id=conversation_id or common.generate_session_id(),  # Use metadata conversation_id if available
        # tenant info
        tenant_id=tenant_id,
        # for testing
        mock_log_guidance=mock_log_guidance,
        # user info
        user_id=user_id,
        all_devices=user_info["all_devices"],
        country=user_info["country"],
        app_version=user_info["app_version"],
    )
    logger.info(f"Created session info: {asdict(my_session_info)}")

    session_obj = agents.AgentSession[session.MySessionInfo](userdata=my_session_info)

    def conversation_item_handler(event: agents.ConversationItemAddedEvent):
        asyncio.create_task(session.on_conversation_item_added(event, session_obj))
    session_obj.on("conversation_item_added")(conversation_item_handler)

    logger.info(f"Joining room: {ctx.room.name}")

    # For outbound calls, always use audio mode
    modalities = metadata.get("modalities", "text_and_audio")
    if is_outbound_call or modalities != "text_only":
        room_input_options = agents.RoomInputOptions(
            text_enabled=True, audio_enabled=True, noise_cancellation=noise_cancellation.BVC()
        )
        room_output_options = agents.RoomOutputOptions(transcription_enabled=True, audio_enabled=True)
    else:
        room_input_options = agents.RoomInputOptions(text_enabled=True, audio_enabled=False)
        room_output_options = agents.RoomOutputOptions(transcription_enabled=True, audio_enabled=False)

    await session_obj.start(
        room=ctx.room,
        agent=Assistant(room=ctx.room, is_sip_session=is_sip_session),
        room_input_options=room_input_options,
        room_output_options=room_output_options
    )


if __name__ == "__main__":
    logger.info(f"Starting agent... {os.getenv("AGENT_NAME","XXX de nada XXX")}")
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint, agent_name=os.getenv("AGENT_NAME"))
    )
    