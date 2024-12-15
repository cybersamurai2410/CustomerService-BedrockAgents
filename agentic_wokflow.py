import os
import boto3
import uuid
import json
from utilities import wait_for_agent_status, wait_for_agent_alias_status, wait_for_action_group_status
from guardrails import create_guardrail, create_guardrail_version, attach_guardrail_to_agent, update_agent_alias

# Environment Variables Setup
AGENT_ID = os.environ.get('BEDROCK_AGENT_ID')
AGENT_ALIAS_ID = os.environ.get('BEDROCK_AGENT_ALIAS_ID')
REGION_NAME = 'us-west-2'
LAMBDA_FUNCTION_ARN = os.environ.get('LAMBDA_FUNCTION_ARN')
ACTION_GROUP_ID = os.environ.get('ACTION_GROUP_ID')
ROLE_ARN = os.environ.get('ROLE_ARN')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')

# Initialize Bedrock Agent Client
bedrock_agent = boto3.client(service_name='bedrock-agent', region_name=REGION_NAME)

# 1. Create and Prepare the Agent
def create_and_prepare_agent():
    response = bedrock_agent.create_agent(
        agentName='mugs-customer-support-agent',
        foundationModel='anthropic.claude-3-haiku-20240307-v1:0',
        instruction="""
        You are an advanced AI agent acting as a front-line customer support agent.
        """,
        agentResourceRoleArn=ROLE_ARN
    )
    agent_id = response['agent']['agentId']
    wait_for_agent_status(agentId=agent_id, targetStatus='NOT_PREPARED')

    bedrock_agent.prepare_agent(agentId=agent_id)
    wait_for_agent_status(agentId=agent_id, targetStatus='PREPARED')
    return agent_id


# 2. Create Agent Alias
def create_agent_alias(agent_id):
    response = bedrock_agent.create_agent_alias(
        agentId=agent_id,
        agentAliasName='MyAgentAlias',
    )
    alias_id = response['agentAlias']['agentAliasId']
    wait_for_agent_alias_status(agentId=agent_id, agentAliasId=alias_id, targetStatus='PREPARED')
    return alias_id


# 3. Create Agent Action Group
def create_action_group(agent_id, lambda_arn):
    response = bedrock_agent.create_agent_action_group(
        actionGroupName='customer-support-actions',
        agentId=agent_id,
        actionGroupExecutor={'lambda': lambda_arn},
        functionSchema={
            'functions': [
                {
                    'name': 'customerId',
                    'description': 'Get a customer ID based on available details.',
                    'parameters': {
                        'email': {'description': 'Email address', 'required': False, 'type': 'string'},
                        'name': {'description': 'Customer name', 'required': False, 'type': 'string'},
                        'phone': {'description': 'Phone number', 'required': False, 'type': 'string'},
                    },
                },
                {
                    'name': 'sendToSupport',
                    'description': 'Escalate to the support team.',
                    'parameters': {
                        'custId': {'description': 'Customer ID', 'required': True, 'type': 'string'},
                        'supportSummary': {'description': 'Summary of the issue', 'required': True, 'type': 'string'},
                    },
                },
            ]
        },
        agentVersion='DRAFT',
    )
    action_group_id = response['agentActionGroup']['actionGroupId']
    wait_for_action_group_status(agentId=agent_id, actionGroupId=action_group_id, targetStatus='ENABLED')
    return action_group_id


# 4. Update Action Group
def update_action_group(agent_id, lambda_arn, action_group_id):
    bedrock_agent.update_agent_action_group(
        actionGroupName='customer-support-actions',
        actionGroupState='ENABLED',
        actionGroupId=action_group_id,
        agentId=agent_id,
        agentVersion='DRAFT',
        actionGroupExecutor={'lambda': lambda_arn},
        functionSchema={
            'functions': [
                {
                    'name': 'purchaseSearch',
                    'description': 'Search for purchase details for raising support requests.',
                    'parameters': {
                        'custId': {'description': 'Customer ID', 'required': True, 'type': 'string'},
                        'productDescription': {'description': 'Product description', 'required': True, 'type': 'string'},
                        'purchaseDate': {'description': 'Purchase date (YYYY-MM-DD)', 'required': True, 'type': 'string'},
                    },
                },
            ]
        },
    )


# 5. Describe the Agent
def describe_agent(agent_id):
    response = bedrock_agent.get_agent(agentId=agent_id)
    print(json.dumps(response, indent=4, default=str))


# 6. Knowledge Base Retrieval
def get_knowledge_base(knowledge_base_id):
    response = bedrock_agent.get_knowledge_base(knowledgeBaseId=knowledge_base_id)
    print(json.dumps(response, indent=4, default=str))


# 7. Invoke Agent for Inference
def invoke_agent_inference(agent_id, agent_alias_id, input_text):
    bedrock_agent_runtime = boto3.client(service_name='bedrock-agent-runtime', region_name=REGION_NAME)
    session_id = str(uuid.uuid4())

    response = bedrock_agent_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        inputText=input_text,
        sessionId=session_id,
        endSession=False,
        enableTrace=True,
    )

    print("--- Inference Response ---")
    print(json.dumps(response, indent=4, default=str))
    return response


# Main Execution Flow
if __name__ == '__main__':
    # Create and prepare agent
    agent_id = create_and_prepare_agent()
    print(f"Agent Created and Prepared. ID: {agent_id}")

    # Create agent alias
    alias_id = create_agent_alias(agent_id)
    print(f"Agent Alias Created. Alias ID: {alias_id}")

    # Create and update action group
    action_group_id = create_action_group(agent_id, LAMBDA_FUNCTION_ARN)
    update_action_group(agent_id, LAMBDA_FUNCTION_ARN, action_group_id)
    print(f"Action Group Created and Updated. ID: {action_group_id}")

    # Create guardrails and attach them
    guardrail_id, guardrail_arn = create_guardrail()
    guardrail_version = create_guardrail_version(guardrail_id)
    attach_guardrail_to_agent(agent_id, guardrail_id, guardrail_version)
    print(f"Guardrails Attached. ID: {guardrail_id}, Version: {guardrail_version}")

    # Update agent alias
    update_agent_alias(agent_id, AGENT_ALIAS_ID)
    print("Agent Alias Updated.")

    # Describe agent
    describe_agent(agent_id)

    # Retrieve knowledge base details
    get_knowledge_base(KNOWLEDGE_BASE_ID)

    # Invoke agent for inference
    test_message = "Hello, I bought a mug from your store yesterday, and it broke. I want to return it."
    invoke_agent_inference(agent_id, alias_id, test_message)
