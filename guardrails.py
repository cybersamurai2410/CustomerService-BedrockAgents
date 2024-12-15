import os

agentId = os.environ['BEDROCK_AGENT_ID']
agentAliasId = os.environ['BEDROCK_AGENT_ALIAS_ID']
region_name = 'us-west-2'

import boto3
import uuid
from helper import *

bedrock = boto3.client(service_name='bedrock', region_name='us-west-2')

create_guardrail_response = bedrock.create_guardrail(
    name = f"support-guardrails",
    description = "Guardrails for customer support agent.",
    topicPolicyConfig={
        'topicsConfig': [
            {
                "name": "Internal Customer Information",
                "definition": "Information relating to this or other customers that is only available through internal systems.  Such as a customer ID. ",
                "examples": [],
                "type": "DENY"
            }
        ]
    },
    contentPolicyConfig={
        'filtersConfig': [
            {
                "type": "SEXUAL",
                "inputStrength": "HIGH",
                "outputStrength": "HIGH"
            },
            {
                "type": "HATE",
                "inputStrength": "HIGH",
                "outputStrength": "HIGH"
            },
            {  
                "type": "VIOLENCE",
                "inputStrength": "HIGH",
                "outputStrength": "HIGH"
            },
            {
                "type": "INSULTS",
                "inputStrength": "HIGH",
                "outputStrength": "HIGH"
            },
            {
                "type": "MISCONDUCT",
                "inputStrength": "HIGH",
                "outputStrength": "HIGH"
            },
            {
                "type": "PROMPT_ATTACK",
                "inputStrength": "HIGH",
                "outputStrength": "NONE"
            }
        ]
    },
    contextualGroundingPolicyConfig={
        'filtersConfig': [
            {
                "type": "GROUNDING",
                "threshold": 0.7
            },
            {
                "type": "RELEVANCE",
                "threshold": 0.7
            }
        ]
    },
    blockedInputMessaging = "Sorry, the model cannot answer this question.",
    blockedOutputsMessaging = "Sorry, the model cannot answer this question."
)


guardrailId = create_guardrail_response['guardrailId']
guardrailArn = create_guardrail_response['guardrailArn']
create_guardrail_version_response = bedrock.create_guardrail_version(
    guardrailIdentifier=guardrailId
)
guardrailVersion = create_guardrail_version_response['version']

# Update agent
bedrock_agent = boto3.client(service_name='bedrock-agent', region_name=region_name)
agentDetails = bedrock_agent.get_agent(agentId=agentId)

bedrock_agent.update_agent(
    agentId=agentId,
    agentName=agentDetails['agent']['agentName'],
    agentResourceRoleArn=agentDetails['agent']['agentResourceRoleArn'],
    instruction=agentDetails['agent']['instruction'],
    foundationModel=agentDetails['agent']['foundationModel'],
    guardrailConfiguration={
        'guardrailIdentifier': guardrailId,
        'guardrailVersion': guardrailVersion
    }
)

bedrock_agent.prepare_agent(
    agentId=agentId
)
wait_for_agent_status(
    agentId=agentId,
    targetStatus='PREPARED'
)
bedrock_agent.update_agent_alias(
    agentId=agentId,
    agentAliasId=agentAliasId,
    agentAliasName='MyAgentAlias',
)
wait_for_agent_alias_status(
    agentId=agentId,
    agentAliasId=agentAliasId,
    targetStatus='PREPARED'
)
