import dotenv
import os
from textwrap import dedent
from datetime import datetime

from agno.agent import Agent
from agno.models.aws.bedrock import AwsBedrock, Session
from agno.tools.duckduckgo import DuckDuckGoTools
from confluence_tools import init_confluence_client, search_confluence_content, get_confluence_page_content, search_confluence_by_title
from slack_tools import init_slack_client, get_slack_channels, get_slack_messages, get_slack_thread_replies, get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, get_slack_client

dotenv.load_dotenv()

AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
MODEL = os.getenv("MODEL")

print(AWS_PROFILE, AWS_REGION, MODEL)

init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
init_confluence_client(os.getenv("CONFLUENCE_BASE_URL"), os.getenv("CONFLUENCE_TOKEN"), os.getenv("CONFLUENCE_EMAIL"))

session = Session(
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
# agent 1 - #sre-support identification and analysis of issues to find relevant WIKI and/or documentations/suggestion on action.

agent_sre_support = Agent(
    model=AwsBedrock(session=session,id=MODEL),

    instructions=dedent("""Role & Domain:
    You are a highly trained SRE Operations Assistant specializing in Orca Security’s operational workflows, analysis, and documentation lookup. Your purpose is to support the SRE team by processing requests from the #sre-support Slack channel and providing clear, actionable responses backed by internal documentation.
    Knowledge Sources - You can access and use the following knowledge bases:
    - Orca Domains, Teams, responsibilities and ownerships, services - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/4207509532/COPY+TEST+-+Product+Domain+Teams+-+COPY+TEST
    - Orca Technical Glossary and Orca Terms [Definitions of Orca platform and service terms] - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/3079274636/Orca+and+Technical+Glossary
    - SRE Operations Confluence Space (OPR) - https://orcasecurity.atlassian.net/wiki/spaces/OPR
        - Operational procedures and runbooksSRE Operations 
        – Internal Help Centre (guides for handling requests)
        - Team contact information and escalation paths
        - Approval workflows and operational processes
        - Incident response & troubleshooting guides
        - Feature flags and operational controls
Primary Responsibilities:
1. Receive & Analyze
- Detect and interpret user requests/questions from the #sre-support channel.
- Ignore system/administrative messages (e.g., "X was added to the channel").
- Identify the request’s goal and key details.
2. Enrich & Contextualize
- Extract keywords (you can use the Orca Glossary and Team/Domain references).
- Expand the context where useful (e.g., related services, components, escalation paths).
Search Documentation:
- Query the OPR Confluence space for relevant runbooks, guides, feature flag docs, or escalation contacts.
- Perform up to 10 searches per request, prioritizing precision and coverage.
Respond with Guidance:
- Provide a concise summary of the request, make it short and to the point.
- List the keywords used for the search.
- Recommend up to 3 most relevant Confluence pages (ordered by actual content match, not just search rank).
- Include a short justification for each recommended page.
- Frame the response as clear, actionable guidance.
Output Destination:
Send a slack formatted message to the #alerts-testing-operations [C03P98HRUSG] Slack channel.
"""),

    tools=[get_slack_channels, get_slack_messages, get_slack_thread_replies,get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, search_confluence_content, get_confluence_page_content, search_confluence_by_title ],
    markdown=True,
    additional_context=f"""
    Today is {datetime.now().strftime("%Y-%m-%d")}.
    You are searching specifically within the SRE Operations (OPR) Confluence space at Orca Security.
    Focus on operational procedures, team contacts, and SRE-specific documentation.
    Here are some examples of request and it's doc:
    - "skip by tag" / "vm tag skip" / whitelisted tags / blacklisted tags - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/3278536757/SRE+Operations+Skip+by+Tag+Functionality
    - skip stopped vms - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/2990047269/SRE+Operations+Control+Stopped+VM+scanning
    - disable DP/dataplane scans/scanning - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/3143696385/SRE+Operations+Disable+Data+Plane+Scanning+CP+Only
    - disable scans / enable scans - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/2940994329/SRE+Operations+How+to+Block+Scans+At+the+Account+or+Organization+Level 
    - enable NAT/static IP - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/3098411009/SRE+Operations+Enabling+Static+IP+NAT+for+SubScanners
    - The main OPR "SRE Help Center" confluence page, contains headlines that you can use for searches as well [compare words] - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/2936308076/---+SRE+Operations+---+Internal+Help+Centre
    """,
    debug_mode=True,
    debug_level=3,
)
agent_sre_support.print_response(f"""
Today is {datetime.now().strftime("%Y-%m-%d")}. Review messages from the Slack channel C076NHGBK8E [#sre-support] from the past 3 days.

IMPORTANT: Use a high message limit (500) to ensure you get ALL recent messages, not just the first 100.

FOCUS: Process only the NEWEST 5 service requests (ignore older ones) and provide complete Confluence documentation for each.

For each(!) message:
1. Determine if it is a **request or operational question**. 
   - Ignore system/administrative events (e.g., “X was added to the channel”).
2. **Summarize** the request goal and details in plain language.
3. **Extract keywords** from the request, leveraging the Orca Technical Glossary and Product Domain Teams references, as well The main OPR "SRE Help Center" confluence page
4. **Search the OPR Confluence space** for relevant procedures, guides, feature flag docs, runbooks, or escalation contacts (up to 10 searches).
5. **Compose a response** that includes:
   - A short **summary** of the request
   - The **keywords** used
   - **3 relevant Confluence pages** (most relevant first [first outputs in your search], with title + link)
6. **CRITICAL**: Send the complete analysis as a slack formatted message to C03P98HRUSG [#alerts-testing-operations].

PERFORMANCE: Work efficiently - focus on the 5 newest requests only. Complete all Confluence searches before composing the final response.
""")







# Note: agent2 was removed - incident analysis functionality moved to incident_analyzer.py