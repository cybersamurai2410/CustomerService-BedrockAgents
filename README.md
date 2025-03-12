# Serverless Agentic Workflow with RAG for Customer Service using AWS Bedrock
Implemented customer service agentic workflow using foundational model via AWS Bedrock Boto3 SDK and integrated tools via AWS Lambda functions with safety guardrails and knowledge bases for context retrieval. 
- Action groups wrapping the function schema.
- Tools using Lambda functions.
- Guardrails to prevent leaking sensitive information from generated responses. 
- Knowledge base text documents for RAG.  

## Example Run
```bash
User: My name is Mike (mike@mike.com), my mug is broken and I want a refund.

Agent: 
Agent's thought process:
  Okay, let's try this again with the information provided.  The
  customer has given their name (Mike) and email address
  (mike@mike.com), indicating they are an existing customer. They are
  reporting a broken mug and requesting a refund.  I will need to look
  up the customer's account details to verify their identity and order
  history before routing this request to the support team.

Invocation Input:
  Type: ACTION_GROUP
  Action Group: customer-support-actions
  Function: customerId
  Parameters: [{'name': 'name', 'type': 'string', 'value': 'Mike'}, {'name': 'email', 'type': 'string', 'value': 'mike@mike.com'}]

Observation:
  Type: ACTION_GROUP
  Action Group Output: {'id':2077}

Agent's thought process:
  Great, I was able to look up the customer's ID based on the name and
  email provided. Now I can proceed to route this request to a human
  support agent to process the refund for the broken mug.
...
  those details.

Session ID: 2220ca00-9ef6-4592-b0dc-8fb68719fe6b
```
