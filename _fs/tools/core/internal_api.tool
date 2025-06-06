{
  "description": "",
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
      "description": "Whether the tool run should fail in the case of ",
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
}