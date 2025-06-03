{
  "arguments": [
    {
      "name": "subscription_id",
      "type_name": "string",
      "description": "The ID of the subscription to describe",
      "required": true
    }
  ],
  "description": "A T1 tool that describes a subscription by calling the scheduler's describe subscription API and returns structured subscription information",
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
          },
          {
            "name": "subscription_id",
            "type_name": "string",
            "description": "The ID of the subscription",
            "required": true
          },
          {
            "name": "tool_definition",
            "type_name": "string",
            "description": "The path to the tool that will be executed",
            "required": true
          },
          {
            "name": "file_path",
            "type_name": "string",
            "description": "The full path to the file or directory being monitored",
            "required": true
          },
          {
            "name": "file_event_type",
            "type_name": "string",
            "description": "The type of file system event being monitored",
            "required": true
          },
          {
            "name": "execution_working_directory",
            "type_name": "string",
            "description": "The working directory for tool execution",
            "required": false
          },
          {
            "name": "expiration",
            "type_name": "string",
            "description": "The datetime the subscription expires",
            "required": false
          },
          {
            "name": "file_type",
            "type_name": "string",
            "description": "The type of file being monitored",
            "required": false
          },
          {
            "name": "owner",
            "type_name": "string",
            "description": "The owner of the subscription",
            "required": true
          },
          {
            "name": "single_use",
            "type_name": "boolean",
            "description": "Whether the subscription is single use",
            "required": true
          },
          {
            "name": "created_on",
            "type_name": "string",
            "description": "When the subscription was created",
            "required": false
          },
          {
            "name": "status",
            "type_name": "string",
            "description": "The current status of the subscription",
            "required": false
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/describe_subscription",
        "target_service": "SCHEDULER",
        "request": {
          "subscription_id": "REF:arguments.subscription_id"
        }
      },
      "execution_id": "describe_subscription_request",
      "transform_responses": {
        "transforms": {
          "subscription_id": "response_body.subscription_id",
          "tool_definition": "response_body.tool_definition",
          "file_path": "response_body.file_path",
          "file_event_type": "response_body.file_event_type",
          "execution_working_directory": "response_body.execution_working_directory",
          "expiration": "response_body.expiration",
          "file_type": "response_body.file_type",
          "owner": "response_body.owner",
          "single_use": "response_body.single_use",
          "created_on": "response_body.created_on",
          "status": "response_body.status"
        }
      }
    }
  ],
  "response_reference_map": {
    "subscription_id": "REF:describe_subscription_request.subscription_id",
    "tool_definition": "REF:describe_subscription_request.tool_definition",
    "file_path": "REF:describe_subscription_request.file_path",
    "file_event_type": "REF:describe_subscription_request.file_event_type",
    "execution_working_directory": "REF:describe_subscription_request.execution_working_directory",
    "expiration": "REF:describe_subscription_request.expiration",
    "file_type": "REF:describe_subscription_request.file_type",
    "owner": "REF:describe_subscription_request.owner",
    "single_use": "REF:describe_subscription_request.single_use",
    "created_on": "REF:describe_subscription_request.created_on",
    "status": "REF:describe_subscription_request.status"
  },
  "responses": [
    {
      "name": "subscription_id",
      "type_name": "string",
      "description": "The ID of the subscription",
      "required": true
    },
    {
      "name": "tool_definition",
      "type_name": "string",
      "description": "The path to the tool that will be executed",
      "required": true
    },
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path to the file or directory being monitored",
      "required": true
    },
    {
      "name": "file_event_type",
      "type_name": "string",
      "description": "The type of file system event being monitored",
      "required": true
    },
    {
      "name": "execution_working_directory",
      "type_name": "string",
      "description": "The working directory for tool execution",
      "required": false
    },
    {
      "name": "expiration",
      "type_name": "string",
      "description": "The datetime the subscription expires",
      "required": false
    },
    {
      "name": "file_type",
      "type_name": "string",
      "description": "The type of file being monitored",
      "required": false
    },
    {
      "name": "owner",
      "type_name": "string",
      "description": "The owner of the subscription",
      "required": true
    },
    {
      "name": "single_use",
      "type_name": "boolean",
      "description": "Whether the subscription is single use",
      "required": true
    },
    {
      "name": "created_on",
      "type_name": "string",
      "description": "When the subscription was created",
      "required": false
    },
    {
      "name": "status",
      "type_name": "string",
      "description": "The current status of the subscription",
      "required": false
    }
  ]
}