{
  "arguments": [
    {
      "name": "tool_definition",
      "type_name": "string",
      "description": "The path to the tool that will be executed for the subscription",
      "required": true
    },
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path to the file or directory to subscribe to",
      "required": true
    },
    {
      "name": "file_event_type",
      "type_name": "string",
      "description": "The type of file system event to subscribe to (e.g. create, delete, update)",
      "required": true
    },
    {
      "name": "execution_working_directory",
      "type_name": "string",
      "description": "The optional working directory for the tool execution",
      "required": false
    },
    {
      "name": "expiration",
      "type_name": "string",
      "description": "The optional datetime the subscription will expire",
      "required": false
    },
    {
      "name": "file_type",
      "type_name": "string",
      "description": "The optional type of file to subscribe to (only supported for directory subscriptions)",
      "required": false
    },
    {
      "name": "owner",
      "type_name": "string",
      "description": "The owner of the subscription (defaults to creator if not specified)",
      "required": false
    },
    {
      "name": "single_use",
      "type_name": "boolean",
      "description": "Whether the subscription is single use or not",
      "required": false,
      "default_value": false
    }
  ],
  "description": "A T1 tool that creates a subscription to file system events by calling the scheduler's create subscription API",
  "instructions": [
    {
      "tool_definition": {
        "arguments": [
          {
            "name": "path",
            "type_name": "string",
            "description": "The API path for the request",
            "required": true
          },
          {
            "name": "fail_on_error",
            "type_name": "boolean",
            "description": "Whether the tool run should fail in the case of an error",
            "default_value": true,
            "required": false
          },
          {
            "name": "request",
            "type_name": "object",
            "description": "The API request object",
            "required": true
          },
          {
            "name": "target_service",
            "type_name": "string",
            "enum": ["PROCESS", "SCHEDULER", "STORAGE"],
            "description": "The internal service to send the request to",
            "required": true
          }
        ],
        "responses": [
          {
            "name": "status_code",
            "type_name": "number",
            "description": "The responding status code from the API call",
            "required": true
          },
          {
            "name": "response_body",
            "type_name": "object",
            "description": "The response body from the API call",
            "required": false
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/scheduler/create_subscription",
        "target_service": "SCHEDULER",
        "request": {
          "tool_definition": "REF:arguments.tool_definition",
          "execution_working_directory": "REF:arguments.execution_working_directory",
          "expiration": "REF:arguments.expiration",
          "file_path": "REF:arguments.file_path",
          "file_type": "REF:arguments.file_type",
          "file_event_type": "REF:arguments.file_event_type",
          "owner": "REF:arguments.owner",
          "single_use": "REF:arguments.single_use"
        }
      },
      "execution_id": "create_subscription_request"
    }
  ],
  "response_reference_map": {
    "status_code": "REF:create_subscription_request.status_code",
    "response_body": "REF:create_subscription_request.response_body"
  },
  "responses": [
    {
      "name": "status_code",
      "type_name": "number",
      "description": "The responding status code from the API call",
      "required": true
    },
    {
      "name": "response_body",
      "type_name": "object",
      "description": "The response body from the API call",
      "required": false
    }
  ]
}