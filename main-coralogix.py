import dotenv
import os
from textwrap import dedent
from agno.models.aws.bedrock import AwsBedrock,Session
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.agent import Agent
from slack_tools import init_slack_client, get_slack_channels, get_slack_messages, get_slack_thread_replies, get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, get_slack_client
from confluence_tools import init_confluence_client, search_confluence_content, get_confluence_page_content, search_confluence_by_title
import requests
import json
from datetime import datetime, timedelta

# Load environment variables
dotenv.load_dotenv()

AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
MODEL = os.getenv("MODEL")

print(AWS_PROFILE, AWS_REGION, MODEL)

CORALOGIX_PRIVATE_KEY =  os.getenv("CORALOGIX_PRIVATE_KEY")
CORALOGIX_QUERY_URL = "https://api.coralogix.com/api/v1/dataprime/query"

init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
init_confluence_client(os.getenv("CONFLUENCE_BASE_URL"), os.getenv("CONFLUENCE_TOKEN"), os.getenv("CONFLUENCE_EMAIL"))

session = Session(
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

agent = Agent(
    model=AwsBedrock(session=session,id=MODEL),

    instructions=dedent("""You are a highly trained SRE Operations assistant specializing in site reliability. 
    Your job is to find correlations that contribute to or are causing a current problem, primarily from recently deployed PRs. 
    You will search for errors and other keywords in Coralogix, determine which errors are new, and determine if they are realted to any recent PR.
    This is accomplished by doing the following:
    1. Search Colalogix, using Frequent Search, for the last 48 hours, using this search string: env_type:\"production\" AND _exists_:scan_id AND (level:ERROR OR (level:WARN AND message:"SCAN_ERROR"))
    2. Group messages that are similar but have information specific to only that message (like IDs, IPs, etc) and count them as one message.
    3. Consider only messages that have a significant count number, compared to other messages returned.
    4. Rank these messages by the likelihood that the message indicates a new problem with a significant impact.
    5. Return the top 5 messages.
    """),
)

# Removed from instructions=dedent, because including it broke the connection to Coralogix
# 3. Compare the last 24 hours with the previous 24 hours, and determine if count of any messagees has increased significantly.

agent.print_response("""
Display the following information from Coralogix in table format:
component | level | message | count_last_24_hours | count_previous_24_hours | increase_percentage
""")
