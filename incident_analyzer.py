import os
from textwrap import dedent
from datetime import datetime, timedelta

import dotenv
from agno.agent import Agent
from agno.models.aws.bedrock import AwsBedrock, Session
from github_tools_lightweight import init_github_client, get_recent_github_merged_prs, get_recent_github_deployments, analyze_github_deployment_correlation
from launchdarkly_tools_lightweight import init_launchdarkly_client, check_launchdarkly_feature_flag
from slack_tools import init_slack_client, get_slack_messages

# Load environment variables
dotenv.load_dotenv()

# Initialize clients
init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
init_github_client(os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_ORG"), os.getenv("GITHUB_REPO"))
init_launchdarkly_client(os.getenv("LAUNCHDARKLY_SDK_KEY"))

session = Session(
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def create_fresh_incident_agent():
    """Create a fresh agent instance with clean memory"""
    return Agent(
        model=AwsBedrock(session=session, id=os.getenv("MODEL")),

        instructions=dedent("""
        Analyze incidents and correlate with deployments efficiently.

        WORKFLOW:
        1. Find incidents in scan-officer channel (GQS8W231C)
        2. Check deployment channels: gradual-rollouts (C02PKC70HEZ), production (CJP11G7UK)
        3. Check GitHub for related deployments
        4. Correlate timeline

        Process each channel/incident only ONCE. Provide brief summary with correlations."""),

        tools=[
            get_slack_messages,
            get_recent_github_merged_prs,
            get_recent_github_deployments,
            analyze_github_deployment_correlation,
            check_launchdarkly_feature_flag
        ],
        markdown=True
    )

def analyze_incidents_efficiently():
    """Analyze incidents with efficient, non-duplicative approach and fresh memory"""
    print("🔍 Efficient incident correlation analysis...")
    print("📊 Channels: scan-officer + gradual-rollouts + production + GitHub")
    print("🧠 Creating fresh agent instance to avoid memory overflow...")

    # Create fresh agent instance for clean memory
    incident_agent = create_fresh_incident_agent()

    # Calculate dates dynamically
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        response = incident_agent.print_response(f"""
        Analyze incidents from {yesterday} to {today}.

        1. Check scan-officer (GQS8W231C) for incidents
        2. Check deployment channels: gradual-rollouts (C02PKC70HEZ), production (CJP11G7UK)
        3. Check GitHub for recent changes
        4. Create timeline correlation

        Process systematically, avoid duplication, provide concise analysis.
        """)

        print("✅ Analysis completed successfully")
        return response

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return None

    finally:
        # Explicitly clear agent memory
        print("🧹 Clearing agent memory...")
        del incident_agent

if __name__ == "__main__":
    analyze_incidents_efficiently()