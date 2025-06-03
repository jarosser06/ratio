{
  "arguments": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path of the file to list versions for",
      "required": true
    }
  ],
  "description": "A T2 tool that lists all versions of a file by calling the storage manager's list file versions API",
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
            "name": "versions",
            "type_name": "list",
            "description": "List of file version objects",
            "required": true
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/list_file_versions",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.file_path"
        }
      },
      "execution_id": "list_file_versions_request",
      "transform_responses": {
        "transforms": {
          "versions": "response_body.versions"
        }
      }
    }
  ],
  "response_reference_map": {
    "versions": "REF:list_file_versions_request.versions"
  },
  "responses": [
    {
      "name": "versions",
      "type_name": "list",
      "description": "List of file version objects",
      "required": true
    }
  ]
}