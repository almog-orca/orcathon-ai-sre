import dotenv
import os
from textwrap import dedent

from agno.agent import Agent
from agno.models.aws.bedrock import AwsBedrock, Session
from agno.tools.duckduckgo import DuckDuckGoTools
from confluence_tools import init_confluence_client, search_confluence_content, get_confluence_page_content, search_confluence_by_title
from github_tools import init_github_client, get_recent_github_merged_prs, get_recent_github_deployments, get_recent_github_commits, analyze_github_deployment_correlation
from launchdarkly_tools import init_launchdarkly_client, get_all_launchdarkly_feature_flags, check_launchdarkly_feature_flag, enable_launchdarkly_maintenance_mode, get_launchdarkly_alert_thresholds
from slack_tools import init_slack_client, get_slack_channels, get_slack_messages, get_slack_thread_replies, get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, get_slack_client

dotenv.load_dotenv()

AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
MODEL = os.getenv("MODEL")

print(AWS_PROFILE, AWS_REGION, MODEL)

init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
init_confluence_client(os.getenv("CONFLUENCE_BASE_URL"), os.getenv("CONFLUENCE_TOKEN"), os.getenv("CONFLUENCE_EMAIL"))
init_launchdarkly_client(os.getenv("LAUNCHDARKLY_SDK_KEY"))
init_github_client(os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_ORG"), os.getenv("GITHUB_REPO"))

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
    additional_context="""
    Today is 2025-09-17.
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
def run_agent_sre_support(user_message=None):
    """
    Run the SRE support agent with either a custom message or the default behavior.
    
    Args:
        user_message (str, optional): Custom message to process. If None, uses the default behavior.
    
    Returns:
        str: The agent's response
    """
    if user_message:
        print(f"Processing custom user message: {user_message}")
        # Process custom user message
        prompt = f"""
        Today is 2025-09-17. A user has sent the following SPECIFIC message in the #sre-support channel:
        
        "{user_message}"
        
        IMPORTANT: Process ONLY this specific message. Do NOT review other messages or perform default behaviors.
        
        Please:
        1. Determine if this is a **request or operational question**.
        2. **Summarize** the request goal and details in plain language.
        3. **Extract keywords** from the request, leveraging the Orca Technical Glossary and Product Domain Teams references.
        4. **Search the OPR Confluence space** for relevant procedures, guides, feature flag docs, runbooks, or escalation contacts (up to 10 searches).
        5. **Compose a response** that includes:
           - A short **summary** of the request
           - The **keywords** used
           - **3 relevant Confluence pages** (most relevant first, with title + link)
        6. Format the response for Slack but DO NOT send any messages to Slack channels.
        
        Process ONLY this specific user message and do not perform any additional tasks or reviews.
        Return the formatted response without sending it anywhere.
        """
        agent_sre_support.print_response(prompt)
    else:
        # Default behavior - review past 3 days of messages
        agent_sre_support.print_response("""
Today is 2025-09-17. Review messages from the Slack channel C076NHGBK8E [#sre-support] from the past 3 days. 

For each(!) message:
1. Determine if it is a **request or operational question**. 
   - Ignore system/administrative events (e.g., "X was added to the channel").
2. **Summarize** the request goal and details in plain language.
3. **Extract keywords** from the request, leveraging the Orca Technical Glossary and Product Domain Teams references, as well The main OPR "SRE Help Center" confluence page
4. **Search the OPR Confluence space** for relevant procedures, guides, feature flag docs, runbooks, or escalation contacts (up to 10 searches).
5. **Compose a response** that includes:
   - A short **summary** of the request
   - The **keywords** used
   - **3 relevant Confluence pages** (most relevant first [first outputs in your search], with title + link)
6. Format the response for Slack but DO NOT send any messages to Slack channels. Return the formatted response only.
""")

# Keep the original behavior when running this file directly
if __name__ == "__main__":
    # Use print_response for console output when running directly
    agent_sre_support.print_response("""
Today is 2025-09-17. Review messages from the Slack channel C076NHGBK8E [#sre-support] from the past 3 days. 

For each(!) message:
1. Determine if it is a **request or operational question**. 
   - Ignore system/administrative events (e.g., "X was added to the channel").
2. **Summarize** the request goal and details in plain language.
3. **Extract keywords** from the request, leveraging the Orca Technical Glossary and Product Domain Teams references, as well The main OPR "SRE Help Center" confluence page
4. **Search the OPR Confluence space** for relevant procedures, guides, feature flag docs, runbooks, or escalation contacts (up to 10 searches).
5. **Compose a response** that includes:
   - A short **summary** of the request
   - The **keywords** used
   - **3 relevant Confluence pages** (most relevant first [first outputs in your search], with title + link)
6. Send all as a slack formatted message, to C03P98HRUSG [#alerts-testing-operations].
""")







# agent 2 - for #rollout-awareness identification and analysis of issues to find relevant WIKI and/or documentations/suggestion on action.
agent2 = Agent(
    model=AwsBedrock(session=session,id=MODEL),

    instructions=dedent("""You are a highly trained SRE Operations Assistant specializing in Orca Security's workflows. 
Your role is to support incident investigations by gathering context, correlating signals, and narrowing down potential causes. 
Do not attempt to provide a single definitive root cause.

Knowledge Sources - You can access and use the following knowledge bases:
- Orca Domains, Teams, responsibilities and ownerships, services - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/4207509532/COPY+TEST+-+Product+Domain+Teams+-+COPY+TEST
- Orca Technical Glossary and Orca Terms [Definitions of Orca platform and service terms] - https://orcasecurity.atlassian.net/wiki/spaces/OPR/pages/3079274636/Orca+and+Technical+Glossary
- SRE Operations Confluence Space (OPR) - https://orcasecurity.atlassian.net/wiki/spaces/OPR
                        
    Follow this workflow when assisting:
    1. Read and interpret Slack messages that report issues. Extract key details such as exception type, region, cloud provider, impact scope, and possible root cause hints.  
    2. Review the last 10 rollout messages in the designated channel. For each rollout, capture details such as:
        - Feature flag name and description  
        - Start time and duration  
        - Affected orgs/accounts/vendors/regions  
        - Expected impact  
    3. Perform deployment-aware incident analysis:
        - Correlate the reported issue with recent rollouts, PRs, and feature flag changes.  
        - Use logs from Coralogix to check for degradations or anomalies that align with the issue.  
        - Verify whether the affected feature flag is active for the impacted accounts.  
        - Compare rollout intent (e.g., decreasing chunk size) with the observed failure (e.g., exceptions in chunk processing).  
    4. Review related PRs for feature flags or deployments and highlight relevant code changes.  
    5. Manage and monitor feature flags via LaunchDarkly to confirm their current state and possible impact.  
    6. Use company-specific terminology (from Confluence or internal context). For example, "AD" = Asset Discovery. Apply these terms correctly in your reasoning.  
    7. Summarize your findings by providing several plausible contributing factors. Focus on narrowing down the most likely areas to investigate further, rather than declaring a single root cause.  

    You have access to the OPR team's Confluence space which contains:
        - The company context, shortcuts, and explination.

    You have access to LaunchDarkly feature flags to:
        - Check maintenance mode status before performing operations
        - Monitor feature flags and operational controls
        - Review alert thresholds and configuration flags
        - Track operational events and flag usage

    You have access to Coralogix to:
        - Fetch and analyze relevant logs for incident investigations
        - Detect performance degradations and anomalies
        - Correlate logs with recent rollouts, feature flags, or PRs
        - Provide evidence to support or eliminate potential causes

    **CRITICAL: DEPLOYMENT CORRELATION ANALYSIS**
    You have GitHub integration to track deployments and correlate with incidents:
    - When users report issues in specific regions/services, IMMEDIATELY check recent deployments, PRs, and commits
    - Look for correlations between incident timing and recent code changes
    - Check if any feature flags were modified around the incident time
    - Provide timeline-based analysis showing what changed before the incident
    - Use analyze_github_deployment_correlation() function for comprehensive correlation analysis

    ### Incident Analysis Workflow
    1. When an incident is reported, extract incident time, service, and region from Slack
    2. Review rollout details from the last 10 rollout messages
    3. Run deployment correlation analysis against recent PRs and commits
    4. Check LaunchDarkly feature flag states for affected accounts and regions
    5. Fetch and analyze logs from Coralogix for anomalies or degradations
    6. Apply company-specific terminology and runbooks from Confluence
    7. Summarize findings with:
       - Observed symptoms
       - Correlated changes (rollouts, feature flags, PRs)
       - Supporting evidence (logs, anomalies, configurations)
       - Plausible contributing factors to narrow investigation paths
    
    ### Incident Analysis Summary
    - **Symptoms observed:** …
    - **Correlated changes:** …
    - **Supporting evidence:** …
    - **Plausible contributing factors:** …
    - **Next areas to investigate:** …

    ### Tool Access – Slack
    - Read and interpret incident reports
    - Extract exception type, region, cloud provider, impact scope, and possible cause hints
    - Review the last 10 rollout messages in the rollout channel
    - Capture feature flag name, description, start time, duration, affected orgs/accounts/vendors/regions, and expected impact

    ### Tool Access – Confluence
    - Access the OPR team's documentation
    - Use company-specific context, acronyms, and explanations (e.g., AD = Asset Discovery)
    - Look up runbooks for affected services

    ### Tool Access – LaunchDarkly
    - Check maintenance mode status before operations
    - Monitor feature flags and operational controls
    - Review alert thresholds and configuration flags
    - Track operational events and flag usage

    ### Tool Access – Coralogix
    - Fetch and analyze relevant logs
    - Detect performance degradations and anomalies
    - Correlate logs with rollouts, feature flags, or PRs
    - Provide evidence to support or eliminate potential causes

    ### Tool Access – GitHub
    - Track deployments and review PRs and commits
    - Correlate incident timing with recent code changes
    - Identify feature flag changes around the incident time
    - Provide a timeline of changes leading up to the incident
    """),
    tools=[DuckDuckGoTools(), get_slack_channels, get_slack_messages, get_slack_thread_replies, get_slack_user_info, get_slack_channel_info, fetch_slack_messages_with_threads, search_confluence_content, get_confluence_page_content, search_confluence_by_title, get_all_launchdarkly_feature_flags, check_launchdarkly_feature_flag, enable_launchdarkly_maintenance_mode, get_launchdarkly_alert_thresholds, get_recent_github_merged_prs, get_recent_github_deployments, get_recent_github_commits, analyze_github_deployment_correlation ],
    markdown=True,
    additional_context="""
    Today is 2025-09-17.
    You are searching specifically within the SRE Operations (OPR) Confluence space at Orca Security.
    Focus on operational procedures, team contacts, and SRE-specific documentation.
    """,
    debug_mode=True,
    debug_level=3,
)