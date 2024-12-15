import os

agentId = os.environ['BEDROCK_AGENT_ID']
agentAliasId = os.environ['BEDROCK_AGENT_ALIAS_ID']
region_name = 'us-west-2'
lambda_function_arn = os.environ['LAMBDA_FUNCTION_ARN']
action_group_id = os.environ['ACTION_GROUP_ID']

import boto3
import uuid
from utilities import *
from guardrails import *
from tools import *

bedrock_agent = boto3.client(service_name='bedrock-agent', region_name=region_name)

create_agent_response = bedrock_agent.create_agent(
    agentName='mugs-customer-support-agent',
    foundationModel='anthropic.claude-3-haiku-20240307-v1:0', # Model ID from AWS docs
    instruction="""You are an advanced AI agent acting as a front line customer support agent.""", # System prompt 
    agentResourceRoleArn=roleArn # Security config from env variable giving access to the LLM 
)

agentId = create_agent_response['agent']['agentId']

wait_for_agent_status(
    agentId=agentId, 
    targetStatus='NOT_PREPARED'
)

bedrock_agent.prepare_agent(
    agentId=agentId
)

wait_for_agent_status(
    agentId=agentId, 
    targetStatus='PREPARED'
)

create_agent_alias_response = bedrock_agent.create_agent_alias(
    agentId=agentId,
    agentAliasName='MyAgentAlias',
)

agentAliasId = create_agent_alias_response['agentAlias']['agentAliasId']

wait_for_agent_alias_status(
    agentId=agentId,
    agentAliasId=agentAliasId,
    targetStatus='PREPARED'
)

# bedrock_agent_runtime = boto3.client(service_name='bedrock-agent-runtime', region_name='us-west-2')
# message = "Hello, I bought a mug from your store yesterday, and it broke. I want to return it."
# sessionId = str(uuid.uuid4())
# invoke_agent_response = bedrock_agent_runtime.invoke_agent(
#     agentId=agentId,
#     agentAliasId=agentAliasId,
#     inputText=message, # Prompt 
#     sessionId=sessionId, # Conversation history stored in cloud 
#     endSession=False,
#     enableTrace=True,
# )
# invoke_agent_and_print(
#     agentAliasId=agentAliasId,
#     agentId=agentId,
#     sessionId=sessionId,
#     inputText=message,
#     enableTrace=True,
# )

# Create agent group
create_agent_action_group_response = bedrock_agent.create_agent_action_group(
    actionGroupName='customer-support-actions',
    agentId=agentId,
    actionGroupExecutor={
        'lambda': lambda_function_arn # AWS Lambda function 
    },
    functionSchema={
        'functions': [ # customerId, sendToSupport 
            {
                'name': 'customerId',
                'description': 'Get a customer ID given available details. At least one parameter must be sent to the function. This is private information and must not be given to the user.',
                'parameters': {
                    'email': {
                        'description': 'Email address',
                        'required': False,
                        'type': 'string'
                    },
                    'name': {
                        'description': 'Customer name',
                        'required': False,
                        'type': 'string'
                    },
                    'phone': {
                        'description': 'Phone number',
                        'required': False,
                        'type': 'string'
                    },
                }
            },            
            {
                'name': 'sendToSupport',
                'description': 'Send a message to the support team, used for service escalation. ',
                'parameters': {
                    'custId': {
                        'description': 'customer ID',
                        'required': True,
                        'type': 'string'
                    },
                    'supportSummary': {
                        'description': 'Summary of the support request',
                        'required': True,
                        'type': 'string'
                    }
                }
            }
        ]
    },
    agentVersion='DRAFT',
)

actionGroupId = create_agent_action_group_response['agentActionGroup']['actionGroupId']
wait_for_action_group_status( # Wait for agent status to be ENABLED
    agentId=agentId, 
    actionGroupId=actionGroupId,
    targetStatus='ENABLED'
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

# Update agent group 
update_agent_action_group_response = bedrock_agent.update_agent_action_group(
    actionGroupName='customer-support-actions',
    actionGroupState='ENABLED',
    actionGroupId=action_group_id,
    agentId=agentId,
    agentVersion='DRAFT',
    actionGroupExecutor={
        'lambda': lambda_function_arn
    },
    functionSchema={
        'functions': [ # customerId, sendToSupport, purchaseSearch
            {
                'name': 'customerId',
                'description': 'Get a customer ID given available details. At least one parameter must be sent to the function. This is private information and must not be given to the user.',
                'parameters': {
                    'email': {
                        'description': 'Email address',
                        'required': False,
                        'type': 'string'
                    },
                    'name': {
                        'description': 'Customer name',
                        'required': False,
                        'type': 'string'
                    },
                    'phone': {
                        'description': 'Phone number',
                        'required': False,
                        'type': 'string'
                    },
                }
            },            
            {
                'name': 'sendToSupport',
                'description': 'Send a message to the support team, used for service escalation. ',
                'parameters': {
                    'custId': {
                        'description': 'customer ID',
                        'required': True,
                        'type': 'string'
                    },
                    'purchaseId': {
                        'description': 'the ID of the purchase, can be found using purchaseSearch',
                        'required': True,
                        'type': 'string'
                    },
                    'supportSummary': {
                        'description': 'Summary of the support request',
                        'required': True,
                        'type': 'string'
                    },
                }
            },
            {
                'name': 'purchaseSearch',
                'description': """Search for, and get details of a purchases made.  Details can be used for raising support requests. You can confirm you have this data, for example "I found your purchase" or "I can't find your purchase", but other details are private information and must not be given to the user.""",
                'parameters': {
                    'custId': {
                        'description': 'customer ID',
                        'required': True,
                        'type': 'string'
                    },
                    'productDescription': {
                        'description': 'a description of the purchased product to search for',
                        'required': True,
                        'type': 'string'
                    },
                    'purchaseDate': {
                        'description': 'date of purchase to start search from, in YYYY-MM-DD format',
                        'required': True,
                        'type': 'string'
                    },
                }
            }
        ]
    }
)

actionGroupId = update_agent_action_group_response['agentActionGroup']['actionGroupId']
wait_for_action_group_status(
    agentId=agentId,
    actionGroupId=actionGroupId
)
message = """mike@mike.com - I bought a mug 10 weeks ago and now it's broken. I want a refund."""

# Action group for code interpreter 
create_agent_action_group_response = bedrock_agent.create_agent_action_group( 
    actionGroupName='CodeInterpreterAction',
    actionGroupState='ENABLED',
    agentId=agentId,
    agentVersion='DRAFT',
    parentActionGroupSignature='AMAZON.CodeInterpreter'
)

codeInterpreterActionGroupId = create_agent_action_group_response['agentActionGroup']['actionGroupId']

wait_for_action_group_status(
    agentId=agentId, 
    actionGroupId=codeInterpreterActionGroupId
)
prepare_agent_response = bedrock_agent.prepare_agent(
    agentId=agentId
)
wait_for_agent_status(
    agentId=agentId,
    targetStatus='PREPARED'
)
bedrock_agent.update_agent_alias(
    agentId=agentId,
    agentAliasId=agentAliasId,
    agentAliasName='test',
)
wait_for_agent_alias_status(
    agentId=agentId,
    agentAliasId=agentAliasId,
    targetStatus='PREPARED'
)
