import os
import uuid
import time
import socket
import threading

from dataclasses import dataclass, field
from collections import defaultdict
from loguru import logger

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slackify_markdown import slackify_markdown
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

# Import from your refactored agents module
from patch_ai.agents import patch_agent, ChatState


# -----------------------
# Config / Constants
# -----------------------
MAX_THREAD_SIZE = 50
MAX_CACHE_LIFE_HOURS = 24
COMPLIANCE_TRIGGER = "RAZZLE DAZZLE ROOT BEER J953"

# Env toggle:
#   PATCH_BOT_MODE=slack   (default)
#   PATCH_BOT_MODE=console
MODE = os.getenv("PATCH_BOT_MODE", "slack").strip().lower()

logger.add("patch_interactions.log", rotation="500 MB")


# -----------------------
# Shared state (Slack + Console)
# -----------------------
active_sessions = set()

# Store BOTH message history AND workflow metadata per thread
thread_conversations = {}  # thread_ts -> message history list
thread_metadata = {}       # thread_ts -> metadata dict (workflow_docs, etc)
thread_last_access = defaultdict(lambda: time.time())


def cleanup_old_thread_cache():
    """Remove threads from cache that haven't been accessed in MAX_CACHE_LIFE_HOURS"""
    current_time = time.time()
    max_age_seconds = MAX_CACHE_LIFE_HOURS * 3600

    threads_to_remove = [
        thread_ts for thread_ts, last_time in thread_last_access.items()
        if current_time - last_time > max_age_seconds
    ]

    for thread_ts in threads_to_remove:
        thread_conversations.pop(thread_ts, None)
        thread_metadata.pop(thread_ts, None)
        thread_last_access.pop(thread_ts, None)
        logger.info(
            f"Removed stale thread from cache: {thread_ts} "
            f"(age: {(current_time - last_time) / 3600:.1f} hours)"
        )

    if threads_to_remove:
        logger.info(
            f"Cache cleanup: removed {len(threads_to_remove)} threads, "
            f"{len(thread_conversations)} remain"
        )


def trim_thread_history(thread_ts: str):
    """Keep only the most recent MAX_THREAD_SIZE messages in a thread.

    IMPORTANT: Never split tool_use/tool_result pairs when trimming!
    Scans forward from trim point to find a safe cut (a user message without tool results).
    """
    if thread_ts not in thread_conversations:
        return

    history = thread_conversations[thread_ts]
    if len(history) <= MAX_THREAD_SIZE:
        return  # No trimming needed

    trim_point = len(history) - MAX_THREAD_SIZE
    logger.info(f"Thread {thread_ts} has {len(history)} messages, needs trimming from position {trim_point}")

    safe_trim_point = trim_point

    for i in range(trim_point, min(trim_point + 20, len(history))):
        msg = history[i]

        # We want to start with a clean user message (ModelRequest)
        if isinstance(msg, ModelRequest):
            if hasattr(msg, "parts"):
                has_tool_result = any(
                    hasattr(part, "tool_use_id") and not isinstance(part, UserPromptPart)
                    for part in msg.parts
                )
                if not has_tool_result:
                    safe_trim_point = i
                    logger.info(f"Found safe trim point at position {i} (user message)")
                    break
            else:
                safe_trim_point = i
                logger.info(f"Found safe trim point at position {i} (legacy user message)")
                break

    if safe_trim_point == trim_point and trim_point < len(history):
        logger.warning(
            f"Could not find safe trim point within scan window, using original position {trim_point}"
        )

    old_length = len(history)
    thread_conversations[thread_ts] = history[safe_trim_point:]
    new_length = len(thread_conversations[thread_ts])

    logger.info(
        f"Trimmed thread {thread_ts} from {old_length} to {new_length} messages "
        f"(removed {old_length - new_length})"
    )


def load_thread_from_slack(client, channel: str, thread_ts: str) -> list[dict]:
    """Fetch all messages in a thread from Slack (or a FakeSlackClient in console mode)."""
    try:
        response = client.conversations_replies(channel=channel, ts=thread_ts, limit=1000)
        return response["messages"]
    except Exception as e:
        logger.error(f"Failed to fetch thread history from Slack: {e}")
        return []


def convert_slack_to_agent_history(slack_messages: list[dict], bot_user_id: str) -> list:
    """Convert Slack thread messages to agent message format."""
    history = []

    for msg in slack_messages:
        # Skip system messages and bot setup messages
        if msg.get("subtype"):
            continue

        text = msg.get("text", "")
        if not text:
            continue

        is_bot = msg.get("user") == bot_user_id or msg.get("bot_id")

        if is_bot:
            history.append(ModelResponse(parts=[TextPart(content=text)]))
        else:
            history.append(ModelRequest(parts=[UserPromptPart(content=text)]))

    return history


def get_or_load_thread_history(client, channel: str, thread_ts: str, is_threaded: bool) -> tuple[list, dict]:
    """Get thread history AND metadata from cache or load from Slack if needed.

    Returns:
        (message_history, metadata_dict)
    """
    thread_last_access[thread_ts] = time.time()

    if thread_ts in thread_conversations:
        logger.debug(f"Cache hit for thread: {thread_ts}")
        return thread_conversations[thread_ts], thread_metadata.get(thread_ts, {})

    if is_threaded:
        logger.info(f"Cache miss - loading thread from Slack: {thread_ts}")
        slack_messages = load_thread_from_slack(client, channel, thread_ts)

        if slack_messages:
            bot_info = client.auth_test()
            history = convert_slack_to_agent_history(slack_messages, bot_info["user_id"])
            thread_conversations[thread_ts] = history

            thread_metadata[thread_ts] = {}
            logger.info(f"Loaded {len(slack_messages)} Slack messages, reconstructed {len(history)} user messages")
            logger.info("Workflow metadata initialized empty (will rebuild from tool calls)")
        else:
            thread_conversations[thread_ts] = []
            thread_metadata[thread_ts] = {}
    else:
        logger.debug(f"New conversation thread: {thread_ts}")
        thread_conversations[thread_ts] = []
        thread_metadata[thread_ts] = {}

    return thread_conversations[thread_ts], thread_metadata[thread_ts]


# -----------------------
# Core logic (shared by Slack + Console)
# -----------------------
def process_user_message(*, user_id: str, channel_id: str, text: str, thread_ts: str, is_threaded: bool, client, say):
    """Core processing for a user message (transport-agnostic)."""

    is_first_message = user_id not in active_sessions

    # Generate a unique request ID for this user message
    request_id = str(uuid.uuid4())

    if is_first_message:
        try:
            chat_state = ChatState(
                slack_client=client,
                slack_channel=channel_id,
                slack_thread_ts=thread_ts,
                current_request_id=request_id,
            )

            # Run compliance check
            r = patch_agent.run_sync(COMPLIANCE_TRIGGER, deps=chat_state)
            logger.info(f"Compliance check result: {r}")

            # DON'T save compliance to thread - start fresh for user's question
            thread_conversations[thread_ts] = []
            thread_metadata[thread_ts] = {}

            active_sessions.add(user_id)

            # Generate NEW request ID for the actual user message
            request_id = str(uuid.uuid4())

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            say(
                ":dizzy_face: Something went wrong with initialization! Try again to retry initialization...",
                thread_ts=thread_ts,
            )
            return

    logger.debug(f"> {text}")
    logger.info(f"Processing request {request_id} for user {user_id}")

    chat_state = None
    try:
        cleanup_old_thread_cache()

        history, metadata = get_or_load_thread_history(
            client=client,
            channel=channel_id,
            thread_ts=thread_ts,
            is_threaded=is_threaded,
        )

        chat_state = ChatState(
            slack_client=client,
            slack_channel=channel_id,
            slack_thread_ts=thread_ts,
            current_request_id=request_id,
            metadata=metadata,
        )

        logger.info(f"Restored metadata for thread {thread_ts}: {list(metadata.keys())}")

        # result = patch_agent.run_sync(
        #     text,
        #     deps=chat_state,
        #     message_history=history,
        # )

        try:
            result = patch_agent.run_sync(text, deps=chat_state, message_history=history)
        except Exception as e:
            if MODE == "console" and "Server disconnected without sending a response" in str(e):
                result = patch_agent.run_sync(text, deps=chat_state, message_history=history)
            else:
                raise


        # --- Post tool-generated markdown tables (if any) ---
        tool_tables = chat_state.metadata.pop("last_md_tables", [])
        for idx, table_md in enumerate(tool_tables, start=1):
            say(slackify_markdown(table_md), thread_ts=thread_ts)
            logger.info(f"Posted markdown table #{idx}")

        # --- Post model's main text output (if any) ---
        if result.output and str(result.output).strip():
            slackified_result = slackify_markdown(str(result.output))
            say(slackified_result, thread_ts=thread_ts)
            logger.debug(f"< {slackified_result}")

        # Upload chart if generated (noop in console fake client)
        if getattr(chat_state, "chart_data", None):
            chart_data = chat_state.chart_data

            points = (
                chart_data.get("data_points")
                or chart_data.get("meta", {}).get("points")
                or (
                    chart_data.get("meta", {}).get("n_series", 1)
                    * chart_data.get("meta", {}).get("n_categories", 0)
                )
            )

            client.files_upload_v2(
                channel=channel_id,
                file=chart_data["image_bytes"],
                filename=chart_data["filename"],
                title=chart_data["title"],
                initial_comment=f"📊 {chart_data['title']}" + (f" ({points} data points)" if points else ""),
                thread_ts=thread_ts,
            )
            logger.info("Uploaded chart to Slack (or printed in console mode)")

        if request_id in getattr(chat_state, "status_messages", {}):
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=chat_state.status_messages[request_id],
                    text="✅ *COMPLETE*",
                    thread_ts=thread_ts,
                )
                logger.info(f"Updated status to COMPLETE for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to update final status: {e}")

        # Extract ONLY the latest user/bot exchange (NO tool execution details)
        new_messages = result.all_messages()

        last_user_msg = None
        last_bot_response = None

        for msg in reversed(new_messages):
            if isinstance(msg, ModelResponse) and last_bot_response is None:
                text_parts = [p for p in msg.parts if isinstance(p, TextPart)]
                if text_parts:
                    last_bot_response = ModelResponse(parts=text_parts)

            elif isinstance(msg, ModelRequest) and last_user_msg is None:
                prompt_parts = [p for p in msg.parts if isinstance(p, UserPromptPart)]
                if prompt_parts:
                    last_user_msg = ModelRequest(parts=prompt_parts)

            if last_user_msg and last_bot_response:
                break

        if last_user_msg and last_bot_response:
            thread_conversations[thread_ts].extend([last_user_msg, last_bot_response])
        else:
            logger.warning("Could not extract clean user/bot exchange from result")

        thread_metadata[thread_ts] = chat_state.metadata
        logger.info(f"Saved metadata for thread {thread_ts}: {list(chat_state.metadata.keys())}")

        trim_thread_history(thread_ts)

        logger.info(f"Completed request {request_id}")

    except Exception as e:
        logger.error(f"Caught exception for request {request_id}: {e}", exc_info=True)

        if chat_state and request_id in getattr(chat_state, "status_messages", {}):
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=chat_state.status_messages[request_id],
                    text="❌ *ERROR*",
                    thread_ts=thread_ts,
                )
                logger.error(f"Updated status to ERROR for request {request_id}")
            except Exception as e2:
                logger.error(f"Failed to update error status: {e2}")

        say(
            f":dizzy_face: Something went wrong! Error: {str(e)}\n\nTry again...",
            thread_ts=thread_ts,
        )


# -----------------------
# Slack mode wiring
# -----------------------
def build_slack_app() -> App:
    """Create Bolt App (Slack mode only)."""
    if "SLACK_BOT_TOKEN" not in os.environ:
        raise RuntimeError("SLACK_BOT_TOKEN is required for PATCH_BOT_MODE=slack")
    return App(token=os.environ["SLACK_BOT_TOKEN"])


# Initialize Slack app only if needed
app = build_slack_app() if MODE == "slack" else None


if app is not None:
    @app.event("message")
    def handle_message_events(body, say, client, ack, logger):
        """Handle all message events - filter out subtypes and bot messages"""
        ack()

        event = body.get("event", {})
        subtype = event.get("subtype")

        if subtype is not None:
            logger.debug(f"Ignoring message with subtype: {subtype}")
            return

        if event.get("bot_id") is not None:
            logger.debug("Ignoring bot message")
            return

        user_id = event["user"]
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])
        is_threaded = "thread_ts" in event

        process_user_message(
            user_id=user_id,
            channel_id=channel_id,
            text=event["text"],
            thread_ts=thread_ts,
            is_threaded=is_threaded,
            client=client,
            say=say,
        )

    @app.event("app_mention")
    def handle_mention(event, say, logger):
        """Handle @mentions of the bot"""
        user = event["user"]
        text = event["text"]
        thread_ts = event.get("thread_ts", event["ts"])

        logger.info(f"Bot mentioned by {user}: {text}")
        say(
            f"Hi <@{user}>! I'm Patch, your PatchFox assistant. How can I help you?",
            thread_ts=thread_ts,
        )

    @app.event("reaction_added")
    def handle_reaction(event, logger):
        """Log reactions for analytics/feedback"""
        logger.info(f"Reaction added: {event['reaction']} by {event['user']}")


# -----------------------
# Console mode wiring (Fake Slack)
# -----------------------
@dataclass
class FakeSlackClient:
    """
    Minimal Slack client surface area to satisfy your code paths:
      - auth_test
      - conversations_replies
      - chat_update
      - files_upload_v2
    """
    threads: dict = field(default_factory=dict)  # (channel, thread_ts) -> list[dict]
    bot_user_id: str = "U_CONSOLE_BOT"
    sender = None  # set per connection

    def chat_postMessage(self, channel, text, thread_ts=None, **kwargs):
        ts = str(time.time())
        # console mode: never emit status messages
        if text and ("*WORKING*" in text or "*COMPLETE*" in text or "*ERROR*" in text):
            return {"ok": True, "ts": ts}
        try:
            if self.sender:
                self.sender(text)
        except Exception:
            pass
        return {"ok": True, "ts": ts}

    def auth_test(self):
        return {"user_id": self.bot_user_id}

    def conversations_replies(self, channel: str, ts: str, limit: int = 1000):
        msgs = self.threads.get((channel, ts), [])
        return {"messages": msgs[:limit]}

    def chat_update(self, channel: str, ts: str, text: str, thread_ts: str = None, **kwargs):
        # console mode: never emit status messages
        if text and ("*WORKING*" in text or "*COMPLETE*" in text or "*ERROR*" in text):
            return {"ok": True, "ts": ts}
        try:
            if self.sender:
                self.sender(text)
        except Exception:
            pass
        return {"ok": True, "ts": ts}

    def files_upload_v2(self, channel: str, file, filename: str, title: str, initial_comment: str, thread_ts: str = None):
        # No upload in console; just announce
        print(f"[file] channel={channel} thread={thread_ts} :: {title} ({filename})")
        if initial_comment:
            print(initial_comment)


def make_console_say(client: FakeSlackClient, channel_id: str):
    def say(text: str, thread_ts: str = None):
        # print
        loc = f"{channel_id}/{thread_ts}" if thread_ts else channel_id
        print(f"[{loc}] BOT: {text}")

        # store in fake thread history in Slack-like shape
        if thread_ts:
            client.threads.setdefault((channel_id, thread_ts), []).append(
                {"user": client.bot_user_id, "text": text, "ts": str(time.time())}
            )
    return say


def run_console_mode():
    client = FakeSlackClient()

    user_id = os.getenv("PATCH_CONSOLE_USER", "U_CONSOLE_USER")
    channel_id = os.getenv("PATCH_CONSOLE_CHANNEL", "C_CONSOLE")

    # one “thread” for this session (or set PATCH_CONSOLE_THREAD)
    thread_ts = os.getenv("PATCH_CONSOLE_THREAD", str(time.time()))
    is_threaded = True

    say = make_console_say(client, channel_id)

    print("Patch console mode. Type messages; Ctrl+C to exit.\n")
    print(f"(mode={MODE}, channel={channel_id}, thread={thread_ts}, user={user_id})\n")

    while True:
        text = input("> ").strip()
        if not text:
            continue

        # store user msg in fake thread history (so your loader works)
        client.threads.setdefault((channel_id, thread_ts), []).append(
            {"user": user_id, "text": text, "ts": str(time.time())}
        )

        process_user_message(
            user_id=user_id,
            channel_id=channel_id,
            text=text,
            thread_ts=thread_ts,
            is_threaded=is_threaded,
            client=client,
            say=say,
        )



# -----------------------
# for console loopback (in place of slack)
# -----------------------
def start_console_listener():
    def run():
        s = socket.socket()
        s.bind(("127.0.0.1", 8765))
        s.listen(1)
        logger.info("Console chat listener on 127.0.0.1:8765")

        def say(text, thread_ts=None):
            conn.sendall((text + "\n").encode())

        while True:
            conn, _ = s.accept()
            with conn:
                f = conn.makefile("r")
                def say(text, thread_ts=None):
                    conn.sendall((text + "\n").encode())
                    console_client.sender = lambda t: conn.sendall((t + "\n").encode())
                for line in f:
                    data = line.strip()
                    if not data:
                        continue

                    process_user_message(
                        user_id="U_CONSOLE",
                        channel_id="C_CONSOLE",
                        text=data,
                        thread_ts="T_CONSOLE",
                        is_threaded=True,
                        client=console_client,
                        say=say,
                    )


    threading.Thread(target=run, daemon=True).start()





# -----------------------
# Entrypoint
# -----------------------
if __name__ == "__main__":
    logger.info(f"Starting Patch AI bot in mode={MODE!r}")

    if MODE == "console":
        console_client = FakeSlackClient()
        start_console_listener()
        while True:
            time.sleep(3600)
    elif MODE == "slack":
        if "SLACK_APP_TOKEN" not in os.environ:
            raise RuntimeError("SLACK_APP_TOKEN is required for PATCH_BOT_MODE=slack (Socket Mode).")
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
    else:
        raise RuntimeError("Unknown PATCH_BOT_MODE. Use 'slack' or 'console'.")
