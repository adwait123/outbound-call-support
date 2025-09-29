import datetime
import textwrap
import random
import logging
import asyncio
from dotenv import load_dotenv
from livekit.plugins import openai
from livekit import agents

from .session import DeviceInfo

load_dotenv()

logger: logging.Logger = logging.getLogger("Mocker")


def now_iso():
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


class Mock:
    def __init__(self) -> None:
        self.mocker_llm = openai.LLM(model="gpt-4.1-mini")

        self.countries = ["DE", "US", "FR"]
        self.app_versions = ["v1", "v2", "v3"]
        self.device_firmware_version = ["v1", "v2", "v3"]

        self.scenes = {
            # Source: https://docs.google.com/document/d/1QfX6mUXgKLcIYiOZwVsJM-BWX6MnskLQBXbnuHrefWc/edit?tab=t.94sgbyr5325b
            0: "Customer is attempting to play a new figurine, but it doesn't play. The support agent detects from the logs that the Tonie is not connected to the WiFi. Customer mentions they are in a hotel. Agent points out from the support documentation that Tonie cannot connect to open networks and recommends using a personal hotspot. This resolves the issue and the new figurine plays.",
            1: "Customer complains that the Tonie is not playing and has a green flashing LED. The agent notices from the logs that the Tonie is playing and that the volume is at 50% and suspects an issue with the speaker. The agent asks the customer to try with a headphone. When that doesn't work, the agent ask the customer to restart the Tonie. The customer wants to return the box and the agent raises a ticket.",

            # Source: https://docs.google.com/document/d/1gjKo41zRoJjrJldHu3wFd35MY6eRkBgPWkiMxESFIXU/edit?tab=t.cbnrrp5v6jpp#heading=h.7rpouertcwms
            #  1. Basic Setup Help – Device Not Appearing in App
            2: "A customer is attempting to set up a new Toniebox; it's flashing blue but isn't appearing in the app. The support agent identifies that the app is trying to scan on the customer's home Wi-Fi instead of the Tonniebox's temporary setup network. The agent instructs the customer to connect their phone to the Tonniebox's temporary Wi-Fi network first, which then allows the device to be detected by the app for setup completion.",
            # 2. Setup Troubleshooting – Figurine Doesn't Play
            3: "A customer's Toniebox is set up with a solid green light, but a new Tonie figurine fails to play content. The support agent determines the content is not authorized for the customer's region. The agent advises the customer on checking figurine compatibility and available resolution options for regional content issues.",
            # 3. Post-Setup Usage Issues – Device Stopped Responding
            4: "A customer's Toniebox worked for about a week but is now completely unresponsive. The support agent identifies a pattern of unstable power supply. The agent recommends troubleshooting the power source and charging equipment to resolve the issue.",
            # 4A. Problematic User Patterns – Repeated Setup Attempts Without Success
            5: "A customer is repeatedly unable to connect their Toniebox to Wi-Fi, consistently receiving 'Incorrect Password' or 'Connection Failed' errors. The support agent identifies that an incorrect Wi-Fi password is being entered. The agent advises the customer to carefully re-enter the password and confirm their network type.",
            # 4B. Problematic Device Patterns – Weak WiFi, Unstable Power, or Other Hardware Anomalies
            6: "A customer's Toniebox frequently cuts out during playback, with audio stopping and the LED briefly turning red, despite being moved closer to the router. The support agent identifies a weak and unstable Wi-Fi connection leading to device instability and crashes. The agent suggests troubleshooting environmental interference, restarting the router, or considering a device replacement if network optimization is unsuccessful."
        }

    def mock_user_info(self) -> dict:
        user_info = {
            "all_devices": {
                "TB-22112": DeviceInfo(device_id="TB-22112", device_firmware_version=random.choice(self.device_firmware_version)),
                "TB-77221": DeviceInfo(device_id="TB-77221", device_firmware_version=random.choice(self.device_firmware_version))
            },
            "country": random.choice(self.countries),
            "app_version": random.choice(self.app_versions),
        }
        logger.info(f"Mock user_info: {user_info}")
        return user_info

    def mock_business_rules(self) -> str:
        business_rules = """"""
        return business_rules

    async def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Evaluate if content is appropriate using a separate LLM."""
        messages = agents.llm.ChatContext([
            agents.llm.ChatMessage(
                type="message",
                role="system",
                content=[system_prompt]
            ),
            agents.llm.ChatMessage(type="message", role="user", content=[user_prompt])
        ])

        response = ""
        async with self.mocker_llm.chat(chat_ctx=messages) as stream:
            async for chunk in stream:
                if not chunk:
                    continue
                content = getattr(chunk.delta, 'content', None) if hasattr(chunk, 'delta') else str(chunk)
                if content:
                    response += content

        return response.strip()

    def get_last_n_messages(self, context: agents.RunContext, n: int) -> list:
        last_n_messages, n_messages = [], 0
        for chat_item in context.session.history.items[::-1]:
            if isinstance(chat_item, agents.llm.ChatMessage):
                if n_messages == n:
                    break
                n_messages += 1
                last_n_messages.append({"role": chat_item.role, "content": chat_item.content})
        return last_n_messages[::-1]

    async def get_scene_from_messages(self, last_n_messages: list) -> str:
        scene_number = await self.call_llm(
            system_prompt=textwrap.dedent(f"""
                You are given the last few messages from a conversation between a Tonies customer and a Tonies customer support agent.
                Your job is to classify the conversation into one of the scenes below.
                {self.scenes}
                
                Output only the number.
            """),
            user_prompt=f"Here are the last few messages: {last_n_messages[::-1]}."
        )

        logger.info(f"Following scene detected: {scene_number}")

        return scene_number

    async def mock_logs_from_scenario(self, scene: str, ongoing_conversation: list, attempt_number: int = 1) -> str:
        # mock logs that are relevant to the current context
        mock_logs = await self.call_llm(
            system_prompt=textwrap.dedent(f"""
                You are a real-time Tonies log server, who generates mock logs from Tonies device and Tonies App.
                You will be given a scene like this:
                {self.scenes[1]}
                Given the scene and an ongoing conversation between a customer and a support agent, you will generate logs that lead the conversation in the direction of the scene.
                Use your knowledge about how Tonies works. And be mindful of the sequence of logs (they should align with the sequence described in the scene).
                """ + """
                Some sample events
                sample_events = [
                    {"level": "INFO", "event": "wifi_connected", "message": "Successfully connected to WiFi network 'HomeNetwork'", "details": {"signal_strength": -45, "network": "HomeNetwork"}},
                    {"level": "INFO", "event": "tonie_placed", "message": "Tonie figure detected on box", "details": {"tonie_id": "gruffalo_001", "audio_length": "12:34"}},
                    {"level": "INFO", "event": "audio_playback_started", "message": "Started audio playback", "details": {"file": "gruffalo_story.mp3", "duration": 754}},
                    {"level": "INFO", "event": "battery_status", "message": "Battery level check", "details": {"level": 85, "charging": False, "voltage": 3.7}},
                    {"level": "INFO", "event": "firmware_check", "message": "Firmware version check completed", "details": {"current": "v3", "latest": "v3", "update_available": False}},
                    {"level": "WARN", "event": "wifi_signal_weak", "message": "WiFi signal strength is weak", "details": {"signal_strength": -75, "recommended_action": "move_closer_to_router"}},
                    {"level": "INFO", "event": "tonie_removed", "message": "Tonie figure removed from box", "details": {"play_duration": 180}},
                    {"level": "INFO", "event": "system_startup", "message": "Toniebox system initialized", "details": {"boot_time": 8.2, "memory_free": 78}},
                    {"level": "ERROR", "event": "audio_playback_failed", "message": "Failed to start audio playback", "details": {"error": "file_not_found", "file": "missing_audio.mp3"}},
                    {"level": "INFO", "event": "power_on", "message": "Device powered on", "details": {"startup_reason": "user_interaction"}}
                ]
                
                Don't generate any other text before of after the logs.
                """ + f"""
                Following device firmware versions exist: {self.device_firmware_version}
                Following App versions exist: {self.app_versions}
            """),
            user_prompt=textwrap.dedent(f"""
                This is the scene:
                {scene}
                This is an ongoing conversation between a customer and a support agent
                {ongoing_conversation}
                This is attempt #{attempt_number} to check the logs in this conversation.

                Can you mock 2 to 5 logs that lead the conversation in the direction of the scene?

                IMPORTANT: If this is attempt #2 or higher, generate logs that show the progression/results of previous troubleshooting attempts. For example:
                - Attempt #1: Initial problem logs (wifi_disconnected, playback_error)
                - Attempt #2: Logs after user tried first solution (wifi_connected, but new_error_discovered)
                - Attempt #3: Logs after user tried second solution (different_state_or_new_findings)
            """)
        )

        logger.info(f"Mock logs for scene, \n{scene} \nLogs\n{mock_logs}")

        return mock_logs

    async def mock_logs_from_guidance(self, mock_log_guidance: dict, ongoing_conversation: list, attempt_number: int = 1):
        """
        Mocks logs based on mock_log_guidance
        mock_log_guidance = {
            "test_scenario": "Tonie doesn't play because the speaker is not working",
            "guidance_to_mock_logs": "Logs should indicate that the charge is at 100%, the Tonie is playing, the volume is at 100%, and a malfunction with speakers"
        }

        :param attempt_number:
        :param ongoing_conversation:
        :param mock_log_guidance:
        :return:
        """
        mock_logs = await self.call_llm(
            system_prompt=textwrap.dedent("""
                You are a real-time Tonies log server, who generates mock logs from Tonies device and Tonies App.
                You will be given a test scenario high-level guidance on what to generate in the mock logs.
                For example, a test scenario might be 
                "Tonie doesn't play because the speaker is not working and"
                a high-level guidance could be 
                "Logs should indicate that the charge is at 100%, the Tonie is playing, the volume is at 100%, and a malfunction with speakers"

                You job is to generate a sequence of 5 realistic log events.

                Some sample events
                [
                    {"level": "INFO", "event": "wifi_connected", "message": "Successfully connected to WiFi network 'HomeNetwork'", "details": {"signal_strength": -45, "network": "HomeNetwork"}},
                    {"level": "INFO", "event": "tonie_placed", "message": "Tonie figure detected on box", "details": {"tonie_id": "gruffalo_001", "audio_length": "12:34"}},
                    {"level": "INFO", "event": "audio_playback_started", "message": "Started audio playback", "details": {"file": "gruffalo_story.mp3", "duration": 754}},
                    {"level": "INFO", "event": "battery_status", "message": "Battery level check", "details": {"level": 85, "charging": False, "voltage": 3.7}},
                    {"level": "INFO", "event": "firmware_check", "message": "Firmware version check completed", "details": {"current": "v3", "latest": "v3", "update_available": False}},
                    {"level": "WARN", "event": "wifi_signal_weak", "message": "WiFi signal strength is weak", "details": {"signal_strength": -75, "recommended_action": "move_closer_to_router"}},
                    {"level": "INFO", "event": "tonie_removed", "message": "Tonie figure removed from box", "details": {"play_duration": 180}},
                    {"level": "INFO", "event": "system_startup", "message": "Toniebox system initialized", "details": {"boot_time": 8.2, "memory_free": 78}},
                    {"level": "ERROR", "event": "audio_playback_failed", "message": "Failed to start audio playback", "details": {"error": "file_not_found", "file": "missing_audio.mp3"}},
                    {"level": "INFO", "event": "power_on", "message": "Device powered on", "details": {"startup_reason": "user_interaction"}}
                ]

                Generate the logs as a list. Don't generate any other text before of after the logs.                    
                Use your knowledge about how Tonies works. And be mindful that the sequence of logs should make logical sense.                
            """),
            user_prompt=textwrap.dedent(f"""
                Test scenario:
                {mock_log_guidance["test_scenario"]}
                Guidance to generate mock logs:
                {mock_log_guidance["guidance_to_mock_logs"]}

                Current ongoing conversation:
                {ongoing_conversation}
                This is attempt #{attempt_number} to check the logs in this conversation.
                
                Generate a sequence of 2 to 5 realistic logs.

                IMPORTANT: If this is attempt #2 or higher, generate logs that show the progression/results of previous troubleshooting attempts. For example:
                - Attempt #1: Initial problem logs (wifi_disconnected, playback_error)
                - Attempt #2: Logs after user tried first solution (wifi_connected, but new_error_discovered)
                - Attempt #3: Logs after user tried second solution (different_state_or_new_findings)
            """)
        )

        logger.info(f"Mock logs:\n{mock_logs}")

        return mock_logs

    async def mock_device_and_app_logs(self, context: agents.RunContext, mock_log_guidance: dict | None) -> str:
        logger.info(f"Mock log guidance: {mock_log_guidance}")

        # Get attempt number for enhanced log generation
        attempt_number = context.session.userdata.log_access_count

        if mock_log_guidance is None:
            ### Current workflow - keep it for backward compatibility ###
            # Classify the conversation into one of the known scenarios and then generate logs

            last_n_messages = self.get_last_n_messages(context=context, n=10)
            scene_number = await self.get_scene_from_messages(last_n_messages)

            try:
                scene_number = int(scene_number)
                if scene_number not in self.scenes.keys():
                    return ""
            except Exception as e:
                logger.exception(str(e))
                return ""

            logs = await self.mock_logs_from_scenario(self.scenes[scene_number], last_n_messages, attempt_number)

        else:
            ### New workflow, where mock logs are generated based on guidance ###
            try:
                # Obtain the scenario and high-level guidance of what log to generate
                last_n_messages = self.get_last_n_messages(context=context, n=5)
                logs = await self.mock_logs_from_guidance(mock_log_guidance, last_n_messages, attempt_number)
            except Exception as e:
                logger.exception(str(e))
                return ""

        return logs


async def main():
    mock = Mock()

    # Test mock_user_info
    user_info = mock.mock_user_info()

    # Test scenario
    last_few_messages_t1 = [
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "We got a new figurine Elsa. But, it is not playing."},
    ]
    scenario_t1 = await mock.get_scene_from_messages(last_few_messages_t1)

    # Test scenario
    last_few_messages_t2 = [
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "We got a new figurine Elsa. But, it is not playing."},
        {"role": "assistant", "content": "I checked the logs. Your WiFi is not working. Can you try connecting to the WiFi?"},
        {"role": "user", "content": "It doesn't connect. We are in a hotel."},
    ]
    scenario_t2 = await mock.get_scene_from_messages(last_few_messages_t2)

    # Test scenario
    last_few_messages_t3 = [
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "We got a new figurine Elsa. But, it is not playing."},
        {"role": "assistant", "content": "I checked the logs. Your WiFi is not working. Can you try connecting to the WiFi?"},
        {"role": "user", "content": "It doesn't connect. We are in a hotel."},
        {"role": "assistant", "content": "You cannot connect the Tonie to an open networks. Try connecting to a personal hotspot from your phone."},
        {"role": "user", "content": "Hotspot worked. And the figurine plays too. Thanks!"},
    ]
    scenario_t3 = await mock.get_scene_from_messages(last_few_messages_t3)

    # Test mock logs
    logs = await mock.mock_logs_from_scenario(mock.scenes[0], last_few_messages_t2, 1)
    mock_log_guidance = {
        "test_scenario": "Tonie doesn't play because the speaker is not working",
        "guidance_to_mock_logs": "Logs should indicate that the charge is at 100%, the Tonie is playing, the volume is at 100%, and a malfunction with speakers"
    }
    logs = await mock.mock_logs_from_guidance(mock_log_guidance, last_few_messages_t1, 1)
    print(logs)


if __name__ == "__main__":
    asyncio.run(main())


