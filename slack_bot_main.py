#!/usr/bin/env python3
"""
Slack Bot that listens to mention events and prints the messages.

This bot uses the Slack Events API to listen for app_mention events
and prints the message content when the bot is mentioned.

Usage:
    uv run slack_bot_main.py

Environment Variables Required:
    SLACK_BOT_TOKEN - Bot User OAuth Token (starts with xoxb-)
    SLACK_SIGNING_SECRET - Signing Secret for verifying requests
    PORT - Port to run the Flask server on (default: 3000)
"""

import os
import logging
from flask import Flask, request, jsonify
import hashlib
import hmac
import time
from dotenv import load_dotenv
from slack_tools import init_slack_client, get_slack_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Get environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
PORT = int(os.getenv("PORT", 3000))

if not SLACK_BOT_TOKEN:
    logger.error("SLACK_BOT_TOKEN environment variable is required")
    exit(1)

if not SLACK_SIGNING_SECRET:
    logger.warning("SLACK_SIGNING_SECRET not configured - request verification will be skipped (not recommended for production)")
    SLACK_SIGNING_SECRET = "dummy-secret"

# Initialize Slack client
init_slack_client(SLACK_BOT_TOKEN)


def verify_slack_request(request_data, timestamp, signature):
    """
    Verify that the request is coming from Slack using the signing secret.
    """
    # Create the signature base string
    sig_basestring = f'v0:{timestamp}:{request_data}'
    
    # Create the signature using HMAC SHA256
    computed_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(computed_signature, signature)


@app.route('/slack/events', methods=['POST'])
def slack_events():
    """
    Handle Slack Events API requests.
    """
    # Get request data
    request_data = request.get_data(as_text=True)
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    
    # Verify the request timestamp (should be within 5 minutes)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        logger.warning("Request timestamp is too old")
        return jsonify({'error': 'Request timestamp is too old'}), 400
    
    # Verify the request signature (skip if using dummy secret)
    if os.getenv("SLACK_SIGNING_SECRET") and not verify_slack_request(request_data, timestamp, signature):
        logger.warning("Invalid request signature")
        return jsonify({'error': 'Invalid request signature'}), 400
    
    # Parse JSON data
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Handle URL verification challenge
    if data.get('type') == 'url_verification':
        logger.info("Handling URL verification challenge")
        return jsonify({'challenge': data.get('challenge')})
    
    # Handle event callbacks
    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        event_type = event.get('type')
        
        if event_type == 'app_mention':
            handle_app_mention(event)
        else:
            logger.info(f"Received unhandled event type: {event_type}")
    
    return jsonify({'status': 'ok'})


def handle_app_mention(event):
    """
    Handle app mention events and print the message.
    """
    try:
        # Extract event data
        user_id = event.get('user')
        channel_id = event.get('channel')
        text = event.get('text', '')
        timestamp = event.get('ts')
        
        # Get Slack client
        client = get_slack_client()
        
        # Get user display name
        user_name = client.get_user_display_name(user_id) if user_id else 'Unknown User'
        
        # Get channel name
        channel_name = client.get_channel_name(channel_id) if channel_id else 'Unknown Channel'
        
        # Format timestamp
        readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(timestamp)))
        
        # Print the mention details
        print("\n" + "="*80)
        print("🤖 BOT MENTIONED!")
        print("="*80)
        print(f"📅 Time: {readable_time}")
        print(f"👤 User: {user_name} ({user_id})")
        print(f"📢 Channel: #{channel_name} ({channel_id})")
        print(f"💬 Message: {text}")
        print(f"🔗 Timestamp: {timestamp}")
        print("="*80)
        
        # Log the mention
        logger.info(f"Bot mentioned by {user_name} in #{channel_name}: {text}")
        
    except Exception as e:
        logger.error(f"Error handling app mention: {e}")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    return jsonify({
        'status': 'healthy',
        'bot_token_configured': bool(SLACK_BOT_TOKEN),
        'signing_secret_configured': bool(SLACK_SIGNING_SECRET)
    })


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint with basic info.
    """
    return jsonify({
        'message': 'Slack Mention Bot is running!',
        'endpoints': {
            '/slack/events': 'Slack Events API endpoint',
            '/health': 'Health check endpoint'
        },
        'version': '1.0.0'
    })


if __name__ == '__main__':
    logger.info("Starting Slack Mention Bot...")
    logger.info(f"Bot Token: {'✓ Configured' if SLACK_BOT_TOKEN else '✗ Missing'}")
    logger.info(f"Signing Secret: {'✓ Configured' if SLACK_SIGNING_SECRET else '✗ Missing'}")
    logger.info(f"Server will run on port {PORT}")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=True
    )
