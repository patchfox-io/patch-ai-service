import os
import asyncio
import uuid
import time
from collections import defaultdict
from loguru import logger
from slack_bolt import App, Args
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slackify_markdown import slackify_markdown
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

# Import from your refactored agents module
from patch_ai.agents import patch_agent, ChatState


MAX_THREAD_SIZE = 50
MAX_CACHE_LIFE_HOURS = 24


COMPLIANCE_TRIGGER = 'RAZZLE DAZZLE ROOT BEER J953'

logger.add("patch_interactions.log", rotation="500 MB")

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Track active user sessions
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
        logger.info(f"Removed stale thread from cache: {thread_ts} (age: {(current_time - last_time) / 3600:.1f} hours)")
    
    if threads_to_remove:
        logger.info(f"Cache cleanup: removed {len(threads_to_remove)} threads, {len(thread_conversations)} remain")


def trim_thread_history(thread_ts: str):
    """Keep only the most recent MAX_THREAD_SIZE messages in a thread
    
    IMPORTANT: Never split tool_use/tool_result pairs when trimming!
    Scans forward from trim point to find a safe cut (a user message without tool results).
    """
    if thread_ts not in thread_conversations:
        return
        
    history = thread_conversations[thread_ts]
    
    if len(history) <= MAX_THREAD_SIZE:
        return  # No trimming needed
    
    # Calculate initial trim point
    trim_point = len(history) - MAX_THREAD_SIZE
    
    logger.info(f"Thread {thread_ts} has {len(history)} messages, needs trimming from position {trim_point}")
    
    # Scan forward to find a safe cut point (a ModelRequest without tool results)
    safe_trim_point = trim_point
    
    for i in range(trim_point, min(trim_point + 20, len(history))):
        msg = history[i]
        
        # We want to start with a clean user message (ModelRequest)
        if isinstance(msg, ModelRequest):
            # Check if this ModelRequest has tool results (which need preceding tool uses)
            if hasattr(msg, 'parts'):
                has_tool_result = any(
                    hasattr(part, 'tool_use_id') and not isinstance(part, UserPromptPart)
                    for part in msg.parts
                )
                if not has_tool_result:
                    # This is a clean user message - safe to trim here
                    safe_trim_point = i
                    logger.info(f"Found safe trim point at position {i} (user message)")
                    break
            else:
                # Old-style message without parts - assume safe
                safe_trim_point = i
                logger.info(f"Found safe trim point at position {i} (legacy user message)")
                break
    
    # If we couldn't find a safe point in our scan window, just use the original trim point
    # and hope for the best (this shouldn't happen often)
    if safe_trim_point == trim_point and trim_point < len(history):
        logger.warning(f"Could not find safe trim point within scan window, using original position {trim_point}")
    
    # Perform the trim
    old_length = len(history)
    thread_conversations[thread_ts] = history[safe_trim_point:]
    new_length = len(thread_conversations[thread_ts])
    
    logger.info(f"Trimmed thread {thread_ts} from {old_length} to {new_length} messages (removed {old_length - new_length})")


def load_thread_from_slack(client, channel: str, thread_ts: str) -> list[dict]:
    """Fetch all messages in a thread from Slack"""
    try:
        response = client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            limit=1000
        )
        return response['messages']
    except Exception as e:
        logger.error(f"Failed to fetch thread history from Slack: {e}")
        return []


def convert_slack_to_agent_history(slack_messages: list[dict], bot_user_id: str) -> list:
    """Convert Slack thread messages to agent message format"""
    
    history = []
    
    for msg in slack_messages:
        # Skip system messages and bot setup messages
        if msg.get('subtype'):
            continue
        
        text = msg.get('text', '')
        if not text:
            continue
            
        is_bot = msg.get('user') == bot_user_id or msg.get('bot_id')
        
        if is_bot:
            # Bot's response - use TextPart
            history.append(ModelResponse(parts=[TextPart(content=text)]))
        else:
            # User's message - use UserPromptPart
            history.append(ModelRequest(parts=[UserPromptPart(content=text)]))
    
    return history


def get_or_load_thread_history(client, channel: str, thread_ts: str, is_threaded: bool) -> tuple[list, dict]:
    """Get thread history AND metadata from cache or load from Slack if needed
    
    Returns:
        tuple: (message_history, metadata_dict)
    """
    
    # Update last access time
    thread_last_access[thread_ts] = time.time()
    
    # Already in cache - return both history and metadata
    if thread_ts in thread_conversations:
        logger.debug(f"Cache hit for thread: {thread_ts}")
        return thread_conversations[thread_ts], thread_metadata.get(thread_ts, {})
    
    # Cache miss - try to load from Slack if it's a threaded conversation
    if is_threaded:
        logger.info(f"Cache miss - loading thread from Slack: {thread_ts}")
        slack_messages = load_thread_from_slack(client, channel, thread_ts)
        
        if slack_messages:
            bot_info = client.auth_test()
            # Only user messages - workflow metadata is preserved separately
            history = convert_slack_to_agent_history(
                slack_messages,
                bot_info['user_id']
            )
            thread_conversations[thread_ts] = history
            
            # Initialize empty metadata - will be populated as Claude navigates workflow
            thread_metadata[thread_ts] = {}
            
            logger.info(f"Loaded {len(slack_messages)} Slack messages, reconstructed {len(history)} user messages")
            logger.info(f"Workflow metadata initialized empty (will rebuild from tool calls)")
        else:
            thread_conversations[thread_ts] = []
            thread_metadata[thread_ts] = {}
    else:
        # Not a thread, start fresh
        logger.debug(f"New conversation thread: {thread_ts}")
        thread_conversations[thread_ts] = []
        thread_metadata[thread_ts] = {}
    
    return thread_conversations[thread_ts], thread_metadata[thread_ts]


@app.event("message")
def handle_message_events(body, say, client, ack, logger):
    """Handle all message events - filter out subtypes and bot messages"""
    ack()
    
    event = body.get('event', {})
    subtype = event.get('subtype')
    
    # Ignore all message subtypes (edits, deletes, etc.)
    if subtype is not None:
        logger.debug(f"Ignoring message with subtype: {subtype}")
        return
    
    # Ignore bot messages
    if event.get('bot_id') is not None:
        logger.debug("Ignoring bot message")
        return
    
    # Now process as a regular user message
    logger.debug(f'event is: {event}')
    
    user_id = event['user']
    channel_id = event['channel']
    thread_ts = event.get('thread_ts', event['ts'])
    is_threaded = 'thread_ts' in event
    is_first_message = user_id not in active_sessions
    
    # Generate a unique request ID for this user message
    request_id = str(uuid.uuid4())
    
    if is_first_message:
        try:
            # Create initial ChatState for compliance check
            chat_state = ChatState(
                slack_client=client,
                slack_channel=channel_id,
                slack_thread_ts=thread_ts,
                current_request_id=request_id
            )
            
            # say(
            #     f"Hello! :fox_face: :wave:"
            #     "\n\nAs this is the start of our conversation I need to initialize. One moment... ",
            #     thread_ts=thread_ts
            # )
            
            # Run compliance check
            r = patch_agent.run_sync(COMPLIANCE_TRIGGER, deps=chat_state)
            logger.info(f'Compliance check result: {r}')
            
            # DON'T save compliance to thread - start fresh for user's question
            thread_conversations[thread_ts] = []  # Clear it
            thread_metadata[thread_ts] = {}

            # say("Done! :rocket:", thread_ts=thread_ts)
            
            # Mark user as having an active session
            active_sessions.add(user_id)
            
            # Generate NEW request ID for the actual user message
            request_id = str(uuid.uuid4())
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            say(
                ":dizzy_face: Something went wrong with initialization! Try again to retry initialization...",
                thread_ts=thread_ts
            )
            return
    
    # Process the actual message
    logger.debug(f"> {event['text']}")
    logger.info(f"Processing request {request_id} for user {user_id}")
    
    try:
        # Get thread history AND metadata
        history, metadata = get_or_load_thread_history(
            client,
            channel_id,
            thread_ts,
            is_threaded
        )
        
        # Create ChatState with restored metadata AND Slack context
        chat_state = ChatState(
            slack_client=client,
            slack_channel=channel_id,
            slack_thread_ts=thread_ts,
            current_request_id=request_id,
            metadata=metadata  # Restore workflow state (workflow_docs, etc)
        )
        
        logger.info(f"Restored metadata for thread {thread_ts}: {list(metadata.keys())}")
        
        # Run with conversation history and restored workflow state
        result = patch_agent.run_sync(
            event["text"], 
            deps=chat_state,
            message_history=history
        )

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
            
        # Upload chart if generated
        if chat_state.chart_data:
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
                file=chart_data['image_bytes'],
                filename=chart_data['filename'],
                title=chart_data['title'],
                initial_comment=f"📊 {chart_data['title']}" + (f" ({points} data points)" if points else ""),
                thread_ts=thread_ts
            )

            # client.files_upload_v2(
            #     channel=channel_id,
            #     file=chart_data['image_bytes'],
            #     filename=chart_data['filename'],
            #     title=chart_data['title'],
            #     initial_comment=f"📊 {chart_data['title']} ({chart_data['data_points']} data points)",
            #     thread_ts=thread_ts
            # )
            logger.info("Uploaded chart to Slack")
        
        if request_id in chat_state.status_messages:
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=chat_state.status_messages[request_id],
                    text="✅ *COMPLETE*",
                    thread_ts=thread_ts
                )
                logger.info(f"Updated status to COMPLETE for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to update final status: {e}")
        
        # Extract ONLY the latest user/bot exchange (NO tool execution details)
        new_messages = result.all_messages()
        
        # Find the last user message and last bot text response
        last_user_msg = None
        last_bot_response = None

        for msg in reversed(new_messages):
            if isinstance(msg, ModelResponse) and last_bot_response is None:
                # Get only text parts from the response
                text_parts = [p for p in msg.parts if isinstance(p, TextPart)]
                if text_parts:
                    last_bot_response = ModelResponse(parts=text_parts)
            elif isinstance(msg, ModelRequest) and last_user_msg is None:
                # Get the user's prompt (only UserPromptPart, not tool results)
                prompt_parts = [p for p in msg.parts if isinstance(p, UserPromptPart)]
                if prompt_parts:
                    last_user_msg = ModelRequest(parts=prompt_parts)
            
            if last_user_msg and last_bot_response:
                break
        
        # Append only the conversational exchange to history (no tool calls)
        if last_user_msg and last_bot_response:
            thread_conversations[thread_ts].extend([last_user_msg, last_bot_response])
        else:
            logger.warning(f"Could not extract clean user/bot exchange from result")
        
        # Save accumulated workflow state
        thread_metadata[thread_ts] = chat_state.metadata
        
        logger.info(f"Saved metadata for thread {thread_ts}: {list(chat_state.metadata.keys())}")
        
        trim_thread_history(thread_ts)

        logger.info(f"Completed request {request_id}")
        
    except Exception as e:
        logger.error(f'Caught exception for request {request_id}: {e}', exc_info=True)
        
        if request_id in chat_state.status_messages:
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=chat_state.status_messages[request_id],
                    text="❌ *ERROR*",
                    thread_ts=thread_ts
                )
                logger.error(f"Updated status to ERROR for request {request_id}")
            except Exception as e2:
                logger.error(f"Failed to update error status: {e2}")
        
        say(
            f":dizzy_face: Something went wrong! Error: {str(e)}\n\nTry again...",
            thread_ts=thread_ts
        )


# Optional: Handle app mentions
@app.event("app_mention")
def handle_mention(event, say, logger):
    """Handle @mentions of the bot"""
    user = event['user']
    text = event['text']
    thread_ts = event.get('thread_ts', event['ts'])
    
    logger.info(f"Bot mentioned by {user}: {text}")
    say(
        f"Hi <@{user}>! I'm Patch, your PatchFox assistant. How can I help you?",
        thread_ts=thread_ts
    )


# Optional: Handle reaction events for feedback
@app.event("reaction_added")
def handle_reaction(event, logger):
    """Log reactions for analytics/feedback"""
    logger.info(f"Reaction added: {event['reaction']} by {event['user']}")


if __name__ == "__main__":
    logger.info("Starting Patch AI Slack Bot...")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()