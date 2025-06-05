{
  "arguments": [
    {
      "name": "directory_path",
      "type_name": "string",
      "description": "The full path of the directory to delete",
      "required": true
    },
    {
      "name": "force",
      "type_name": "boolean",
      "description": "Force deletion even if the directory contains files with lineage",
      "required": false,
      "default_value": false
    }
  ],
  "description": "A T2 tool that deletes a directory and all its contents by calling the storage manager's delete file API with recursive option",
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
        "path": "/storage/delete_file",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.directory_path",
          "force": "REF:arguments.force",
          "recursive": true
        }
      },
      "execution_id": "delete_directory_request"
    }
  ],
  "response_reference_map": {
    "status_code": "REF:delete_directory_request.status_code",
    "response_body": "REF:delete_directory_request.response_body"
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