{
  "arguments": [
    {
      "name": "directory_path",
      "type_name": "string",
      "description": "The full path of the directory to list",
      "required": true
    }
  ],
  "description": "A T2 tool that lists files in a directory by calling the storage manager's list files API and returns structured file information",
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
            "name": "files",
            "type_name": "list",
            "description": "List of file objects from the directory",
            "required": true
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/list_files",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.directory_path"
        }
      },
      "execution_id": "list_files_request",
      "transform_responses": {
        "transforms": {
          "files": "response_body.files"
        }
      }
    }
  ],
  "response_reference_map": {
    "files": "REF:list_files_request.files"
  },
  "responses": [
    {
      "name": "files",
      "type_name": "list",
      "description": "List of file objects from the directory",
      "required": true
    }
  ]
}