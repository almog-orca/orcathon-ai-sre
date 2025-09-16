import dotenv
import os
from textwrap import dedent
from agno.models.aws.bedrock import AwsBedrock,Session
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.agent import Agent
from slack_tools import init_slack_client, get_slack_channels, get_slack_messages, get_slack_thread_replies, get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, get_slack_client
from confluence_tools import init_confluence_client, search_confluence_content, get_confluence_page_content, search_confluence_by_title
from launchdarkly_tools import init_launchdarkly_client, get_all_feature_flags, check_feature_flag, enable_maintenance_mode, get_alert_thresholds

dotenv.load_dotenv()

AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
MODEL = os.getenv("MODEL")

print(AWS_PROFILE, AWS_REGION, MODEL)

init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
init_confluence_client(os.getenv("CONFLUENCE_BASE_URL"), os.getenv("CONFLUENCE_TOKEN"), os.getenv("CONFLUENCE_EMAIL"))
init_launchdarkly_client(os.getenv("LAUNCHDARKLY_SDK_KEY"))

session = Session(
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

agent = Agent(
    model=AwsBedrock(session=session,id=MODEL),

    instructions=dedent("""You are a highly trained SRE Operations assistant specializing in Orca Security's operational procedures. Your primary job is to help users by:
    1. Monitoring Slack channels for user requests and operational questions
    2. Searching the SRE Operations (OPR) Confluence space for relevant procedures, contacts, and documentation
    3. Providing clear, actionable guidance based on existing SRE operational documentation
    4. Managing and monitoring feature flags via LaunchDarkly for operational controls

    You have access to the OPR team's Confluence space which contains:
    - SRE Operations procedures and runbooks
    - Team contact information and escalation paths
    - Operational workflows and approval processes
    - Incident response and troubleshooting guides

    You also have access to LaunchDarkly feature flags to:
    - Check maintenance mode status before performing operations
    - Monitor SRE-specific feature flags and operational controls
    - Check alert thresholds and system configuration flags
    - Track operational events and flag usage

    When you find requests in Slack, search the OPR documentation for related procedures and check relevant feature flags before providing responses.
    Write your responses in a clear, organized format with specific operational context."""),
    tools=[DuckDuckGoTools(), get_slack_channels, get_slack_messages, get_slack_thread_replies,get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, search_confluence_content, get_confluence_page_content, search_confluence_by_title, get_all_feature_flags, check_feature_flag, enable_maintenance_mode, get_alert_thresholds ],
    markdown=True,
    additional_context="""
    Today is 2025-09-16.
    You are searching specifically within the SRE Operations (OPR) Confluence space at Orca Security.
    Focus on operational procedures, team contacts, and SRE-specific documentation.
    """,
    debug_mode=True,
    debug_level=3,
)
agent.print_response("""
Search the C076NHGBK8E Slack channel for user requests and questions. Today is 2025-09-16.
Review messages from the last 24 hours, looking for:

1. **Direct questions** - Users asking "how do I...", "what's the process for...", "where can I find..."
2. **Help requests** - Users needing assistance with procedures, tools, or processes
3. **Process inquiries** - Questions about workflows, approvals, or standard procedures

For each request you find, do the following:
1. **Extract key terms** from the request (tools, processes, systems mentioned)
2. **Search company wikis** using those key terms to find relevant documentation
3. **Analyze wiki content** to identify step-by-step procedures or guidance
4. **Provide response** with links to relevant documentation
Use different keywords until a wiki is found, up to 10 search attempts.

For each request found, provide:
- **Requester**: Who asked the question
- **Request**: What they're asking for (summarized)
- **Wiki Results**: Relevant pages found with links and brief descriptions
- **Procedure Summary**: Key steps or guidance from the documentation
- **Status**: Whether complete guidance was found or if escalation is needed

Focus on actionable requests where you can provide helpful guidance from existing documentation.
""")

