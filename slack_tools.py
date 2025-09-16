"""
Slack tools for agno framework - converted from slack_conv_scraper utilities.
Provides tools for fetching messages, channels, user info, and thread data from Slack.
"""

import time
import json
import logging
import re
from datetime import timezone
from typing import Optional, Dict, Any, List
from dateutil import parser as dateparser

import requests
from agno.tools import tool

# Regex patterns for user and subteam mentions
USER_MENTION_PATTERN = re.compile(r"<@([A-Z0-9]+)>")
SUBTEAM_PATTERN = re.compile(r"<!subteam\^([A-Z0-9]+)>")

logger = logging.getLogger("slack_tools")


class SlackAPIError(Exception):
    """Raised when a Slack API call fails."""
    pass


def get_date_time(timestamp: str) -> str:
    """Convert Unix timestamp to formatted date string."""
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(timestamp)))
    except (ValueError, TypeError):
        return "Invalid timestamp"


class SlackClient:
    """Slack API client for making authenticated requests."""
    
    def __init__(self, token: str, base_url: str = "https://slack.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._user_cache = {}
        self._subteam_cache = {}
        self._channel_cache = {}

    def make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Slack API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                logger.error(f"Slack API error: {data.get('error', 'Unknown error')}")
                raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise SlackAPIError(f"Slack API request failed: {e}")

    def get_user_display_name(self, user_id: str) -> str:
        """Get user display name from Slack API with caching."""
        if user_id not in self._user_cache:
            try:
                data = self.make_request("users.info", {"user": user_id})
                if data and data.get("user"):
                    profile = data["user"].get("profile", {})
                    display_name = (
                        profile.get("display_name") or 
                        profile.get("real_name") or 
                        user_id
                    )
                    self._user_cache[user_id] = display_name
            except Exception as e:
                logger.error(f"Error fetching user display name for {user_id}: {e}")
                self._user_cache[user_id] = user_id
        return self._user_cache.get(user_id, user_id)

    def get_subteam_display_name(self, subteam_id: str) -> str:
        """Get subteam display name with caching."""
        if not self._subteam_cache:
            try:
                data = self.make_request("usergroups.list")
                if data and data.get("usergroups"):
                    for group in data["usergroups"]:
                        self._subteam_cache[group["id"]] = group.get("handle", group["id"])
            except Exception as e:
                logger.error(f"Error fetching subteams: {e}")
        
        return self._subteam_cache.get(subteam_id, subteam_id)

    def get_channel_name(self, channel_id: str) -> str:
        """Get channel name with caching."""
        if channel_id not in self._channel_cache:
            try:
                data = self.make_request("conversations.info", {"channel": channel_id})
                if data and data.get("channel"):
                    channel_name = data["channel"].get("name", channel_id)
                    self._channel_cache[channel_id] = channel_name
            except Exception as e:
                logger.error(f"Error fetching channel name for {channel_id}: {e}")
                self._channel_cache[channel_id] = channel_id
        return self._channel_cache.get(channel_id, channel_id)

    def resolve_user_mentions(self, text: str) -> str:
        """Replace user ID mentions with display names."""
        def replace_user(match):
            user_id = match.group(1)
            return f"@{self.get_user_display_name(user_id)}"
        return USER_MENTION_PATTERN.sub(replace_user, text)

    def resolve_subteam_mentions(self, text: str) -> str:
        """Replace subteam ID mentions with display names."""
        def replace_subteam(match):
            subteam_id = match.group(1)
            return f"@{self.get_subteam_display_name(subteam_id)}"
        return SUBTEAM_PATTERN.sub(replace_subteam, text)


# Global client instance (will be initialized with token)
_slack_client: Optional[SlackClient] = None


def init_slack_client(token: str) -> None:
    """Initialize the global Slack client with authentication token."""
    global _slack_client
    _slack_client = SlackClient(token)
    print(f"xxxx {_slack_client}")


def get_slack_client() -> SlackClient:
    """Get the initialized Slack client."""
    if _slack_client is None:
        raise ValueError("Slack client not initialized. Call init_slack_client() first.")
    return _slack_client


@tool
def get_slack_channels(exclude_archived: bool = True, limit: int = 50) -> List[Dict[str, str]]:
    """
    Fetch available Slack channels that the bot has access to.
    
    Args:
        exclude_archived: Whether to exclude archived channels (default: True)
        limit: Maximum number of channels to return (default: 50)
    
    Returns:
        List of simplified channel dictionaries with id, name, and member count
    """
    client = get_slack_client()
    all_channels = []
    cursor = None
    fetched_count = 0

    while fetched_count < limit:
        params = {
            "types": "public_channel",
            "exclude_archived": str(exclude_archived).lower(),
            "limit": min(100, limit - fetched_count),
        }
        if cursor:
            params["cursor"] = cursor

        data = client.make_request("conversations.list", params)
        if not data:
            break

        channels = data.get("channels", [])
        
        # Simplify channel data to reduce token usage
        simplified_channels = []
        for channel in channels:
            simplified_channels.append({
                "id": channel.get("id", ""),
                "name": channel.get("name", ""),
                "member_count": channel.get("num_members", 0),
                "purpose": channel.get("purpose", {}).get("value", "")[:100] if channel.get("purpose") else ""
            })
        
        all_channels.extend(simplified_channels)
        fetched_count += len(channels)
        
        logger.info(f"Fetched {len(channels)} channels (Total: {len(all_channels)})")

        if not data.get("has_more") or fetched_count >= limit:
            break
            
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return all_channels[:limit]


@tool
def get_slack_messages(
    channel_id: str,
    start_date: str,
    end_date: str = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Fetch messages from a Slack channel within a date range.
    
    Args:
        channel_id: The Slack channel ID
        start_date: Start date in format "YYYY-MM-DD" or parseable date string
        end_date: End date in format "YYYY-MM-DD" or parseable date string
        limit: Number of messages to fetch per API call (default: 100)
    
    Returns:
        List of message dictionaries with metadata
    """
    print(f"xxxx {channel_id, start_date, end_date, limit}")
    client = get_slack_client()
    
    # Parse dates to timestamps
    oldest = str(dateparser.parse(start_date).replace(tzinfo=timezone.utc).timestamp())
    latest = str(dateparser.parse(end_date).replace(tzinfo=timezone.utc).timestamp())
    
    all_messages = []
    cursor = None
    
    while True:
        params = {
            "channel": channel_id,
            "oldest": oldest,
            "latest": latest,
            "limit": limit,
            "inclusive": True,
        }
        if cursor:
            params["cursor"] = cursor
            
        data = client.make_request("conversations.history", params)
        if not data:
            break
            
        messages = data.get("messages", [])
        logger.info(f"Fetched {len(messages)} messages (Total: {len(all_messages)})")
        all_messages.extend(messages)
        
        if not data.get("has_more"):
            break
            
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
            
        time.sleep(1)  # Rate limiting
    
    # Add metadata to messages
    channel_name = client.get_channel_name(channel_id)
    for message in all_messages:
        message["channel_name"] = channel_name
        message["url"] = f"https://slack.com/archives/{channel_id}/p{message['ts'].replace('.', '')}"
    
    return all_messages


@tool
def get_slack_thread_replies(channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
    """
    Fetch all replies in a Slack thread.
    
    Args:
        channel_id: The Slack channel ID
        thread_ts: The timestamp of the parent message
    
    Returns:
        List of reply message dictionaries
    """
    client = get_slack_client()
    
    params = {"channel": channel_id, "ts": thread_ts}
    data = client.make_request("conversations.replies", params)
    
    if not data:
        return []
        
    messages = data.get("messages", [])
    return messages


@tool
def get_slack_user_info(user_id: str) -> Dict[str, Any]:
    """
    Get information about a Slack user.
    
    Args:
        user_id: The Slack user ID
    
    Returns:
        User information dictionary
    """
    client = get_slack_client()
    
    data = client.make_request("users.info", {"user": user_id})
    if not data:
        return {}
        
    return data.get("user", {})


@tool
def get_slack_channel_info(channel_id: str) -> Dict[str, Any]:
    """
    Get information about a Slack channel.
    
    Args:
        channel_id: The Slack channel ID
    
    Returns:
        Channel information dictionary
    """
    client = get_slack_client()
    
    data = client.make_request("conversations.info", {"channel": channel_id})
    if not data:
        return {}
        
    return data.get("channel", {})


@tool
def fetch_slack_messages_with_threads(
    channel_id: str,
    start_date: str,
    end_date: str,
    include_thread_replies: bool = True,
    resolve_mentions: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch messages from a Slack channel with optional thread replies and mention resolution.
    
    Args:
        channel_id: The Slack channel ID
        start_date: Start date in parseable format
        end_date: End date in parseable format
        include_thread_replies: Whether to fetch thread replies (default: True)
        resolve_mentions: Whether to resolve user/subteam mentions to display names (default: True)
    
    Returns:
        List of message dictionaries with threads and resolved mentions
    """
    client = get_slack_client()
    
    # Get base messages by calling the client directly
    client = get_slack_client()
    messages = client.get_messages(channel_id, start_date, end_date)
    
    # Process each message
    for message in messages:
        # Fetch thread replies if requested and available
        if include_thread_replies and message.get("reply_count", 0) > 0:
            logger.info(f"Fetching {message['reply_count']} replies for thread {message['ts']}")
            thread_replies = get_slack_thread_replies(channel_id, message["thread_ts"])
            message["thread_replies"] = thread_replies
            
            # Resolve mentions in thread replies
            if resolve_mentions:
                for reply in thread_replies:
                    if "text" in reply:
                        reply["text"] = client.resolve_user_mentions(reply["text"])
                        reply["text"] = client.resolve_subteam_mentions(reply["text"])
        
        # Resolve mentions in main message
        if resolve_mentions and "text" in message:
            message["text"] = client.resolve_user_mentions(message["text"])
            message["text"] = client.resolve_subteam_mentions(message["text"])
    
    return messages


@tool
def extract_slack_conversations(
    messages: List[Dict[str, Any]],
    resolve_reactions: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract and format conversations from raw Slack messages with threads.
    
    Args:
        messages: List of message dictionaries (typically from fetch_slack_messages_with_threads)
        resolve_reactions: Whether to resolve reaction user IDs to display names
    
    Returns:
        List of formatted conversation dictionaries
    """
    client = get_slack_client()
    conversations = []
    
    for message in messages:
        if "thread_replies" not in message:
            continue
            
        text_messages = []
        for reply in message["thread_replies"]:
            try:
                text = reply.get("text", "")
                reply_data = {
                    "text": text,
                    "ts": reply["ts"],
                    "formatted_time": get_date_time(reply["ts"]),
                }
                
                # Add user info if available
                if "user" in reply:
                    reply_data["user"] = client.get_user_display_name(reply["user"])
                
                # Resolve reactions if requested
                if resolve_reactions and "reactions" in reply:
                    reactions = []
                    for reaction in reply["reactions"]:
                        resolved_reaction = reaction.copy()
                        resolved_reaction["users"] = [
                            client.get_user_display_name(user_id) 
                            for user_id in reaction.get("users", [])
                        ]
                        reactions.append(resolved_reaction)
                    reply_data["reactions"] = reactions
                
                text_messages.append(reply_data)
            except Exception as e:
                logger.warning(f"Error processing reply: {e}")
                continue
        
        # Build conversation metadata
        conversation = {
            "channel_name": message.get("channel_name", ""),
            "url": message.get("url", ""),
            "timestamp": message["ts"],
            "formatted_timestamp": get_date_time(message["ts"]),
            "text_messages": text_messages,
        }
        
        # Add additional metadata if available
        if "latest_reply" in message:
            conversation["latest_reply"] = message["latest_reply"]
            conversation["formatted_latest_reply"] = get_date_time(message["latest_reply"])
        
        # Resolve main message reactions
        if resolve_reactions and "reactions" in message:
            reactions = []
            for reaction in message["reactions"]:
                resolved_reaction = reaction.copy()
                resolved_reaction["users"] = [
                    client.get_user_display_name(user_id) 
                    for user_id in reaction.get("users", [])
                ]
                reactions.append(resolved_reaction)
            conversation["reactions"] = reactions
        
        conversations.append(conversation)
    
    return conversations


@tool
def save_slack_data_to_json(data: Any, filename: str) -> str:
    """
    Save Slack data to a JSON file.
    
    Args:
        data: The data to save (messages, conversations, etc.)
        filename: Output filename
    
    Returns:
        Success message with file path
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved data to {filename}")
        return f"Data saved to {filename}"
    except Exception as e:
        error_msg = f"Error saving data to {filename}: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)