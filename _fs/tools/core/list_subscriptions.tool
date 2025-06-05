{
  "arguments": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path to filter subscriptions by (optional)",
      "required": false
    },
    {
      "name": "owner",
      "type_name": "string",
      "description": "The owner to filter subscriptions by (optional)",
      "required": false
    }
  ],
  "description": "A T1 tool that lists subscriptions by calling the scheduler's list subscriptions API and returns structured subscription information",
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
            "name": "subscriptions",
            "type_name": "list",
            "description": "List of subscription objects",
            "required": true
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/scheduler/list_subscriptions",
        "target_service": "SCHEDULER",
        "request": {
          "file_path": "REF:arguments.file_path",
          "owner": "REF:arguments.owner"
        }
      },
      "execution_id": "list_subscriptions_request",
      "transform_responses": {
        "transforms"{
          "subscriptions": "response_body.subscriptions"
        }
      }
    }
  ],
  "response_reference_map": {
    "subscriptions": "REF:list_subscriptions_request.subscriptions"
  },
  "responses": [
    {
      "name": "subscriptions",
      "type_name": "list",
      "description": "List of subscription objects",
      "required": true
    }
  ]
}