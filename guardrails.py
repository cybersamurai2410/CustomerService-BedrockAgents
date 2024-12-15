import os
import boto3
from helper import wait_for_agent_status, wait_for_agent_alias_status

# Environment Variables Setup
REGION_NAME = 'us-west-2'
AGENT_ID = os.environ.get('BEDROCK_AGENT_ID')
AGENT_ALIAS_ID = os.environ.get('BEDROCK_AGENT_ALIAS_ID')

# Initialize Bedrock Clients
bedrock = boto3.client(service_name='bedrock', region_name=REGION_NAME)
bedrock_agent = boto3.client(service_name='bedrock-agent', region_name=REGION_NAME)

def create_guardrail(name="support-guardrails", description="Guardrails for customer support agent."):
    """
    Creates a guardrail with topic, content, and contextual grounding policies.
    """
    response = bedrock.create_guardrail(
        name=name,
        description=description,
        topicPolicyConfig={
            'topicsConfig': [
                {
                    "name": "Internal Customer Information",
                    "definition": "Information relating to internal customer IDs and details.",
                    "examples": [],
                    "type": "DENY"
                }
            ]
        },
        contentPolicyConfig={
            'filtersConfig': [
                {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
            ]
        },
        contextualGroundingPolicyConfig={
            'filtersConfig': [
                {"type": "GROUNDING", "threshold": 0.7},
                {"type": "RELEVANCE", "threshold": 0.7}
            ]
        },
        blockedInputMessaging="Sorry, the model cannot answer this question.",
        blockedOutputsMessaging="Sorry, the model cannot answer this question."
    )
    return response['guardrailId'], response['guardrailArn']


def create_guardrail_version(guardrail_id):
    """
    Creates a version of the guardrail.
    """
    response = bedrock.create_guardrail_version(guardrailIdentifier=guardrail_id)
    return response['version']


def attach_guardrail_to_agent(agent_id, guardrail_id, guardrail_version):
    """
    Attaches the created guardrail to the specified Bedrock agent.
    """
    agent_details = bedrock_agent.get_agent(agentId=agent_id)

    # Update agent configuration with guardrail
    bedrock_agent.update_agent(
        agentId=agent_id,
        agentName=agent_details['agent']['agentName'],
        agentResourceRoleArn=agent_details['agent']['agentResourceRoleArn'],
        instruction=agent_details['agent']['instruction'],
        foundationModel=agent_details['agent']['foundationModel'],
        guardrailConfiguration={
            'guardrailIdentifier': guardrail_id,
            'guardrailVersion': guardrail_version
        }
    )
    # Prepare the agent
    bedrock_agent.prepare_agent(agentId=agent_id)
    wait_for_agent_status(agentId=agent_id, targetStatus='PREPARED')


def update_agent_alias(agent_id, agent_alias_id, alias_name="MyAgentAlias"):
    """
    Updates the agent alias to reflect changes after attaching guardrails.
    """
    bedrock_agent.update_agent_alias(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        agentAliasName=alias_name,
    )
    wait_for_agent_alias_status(agentId=agent_id, agentAliasId=agent_alias_id, targetStatus='PREPARED')
