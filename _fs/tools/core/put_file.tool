{
  "arguments": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path of the file to create",
      "required": true
    },
    {
      "name": "file_type",
      "type_name": "string",
      "description": "The type of the file",
      "required": true
    },
    {
      "name": "data",
      "type_name": "any",
      "description": "The data to write to the file (optional)",
      "required": false
    },
    {
      "name": "metadata",
      "type_name": "object",
      "description": "Additional metadata to associate with the file",
      "required": false
    },
    {
      "name": "owner",
      "type_name": "string",
      "description": "The owner of the file",
      "required": false
    },
    {
      "name": "group",
      "type_name": "string",
      "description": "The group owner of the file",
      "required": false
    },
    {
      "name": "permissions",
      "type_name": "string",
      "description": "The file permissions (default: 644)",
      "required": false,
      "default_value": "644"
    }
  ],
  "description": "A T2 tool that creates a file by calling the storage manager's put file API and optionally writes data to it",
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
        "path": "/put_file",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.file_path",
          "file_type": "REF:arguments.file_type",
          "metadata": "REF:arguments.metadata",
          "owner": "REF:arguments.owner",
          "group": "REF:arguments.group",
          "permissions": "REF:arguments.permissions"
        }
      },
      "execution_id": "put_file_request"
    },
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
        "path": "/put_file_version",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.file_path",
          "data": "REF:arguments.data",
          "metadata": "REF:arguments.metadata"
        }
      },
      "execution_id": "put_file_data_request",
      "conditions": [
          {
            "param": "REF:arguments.data",
            "operator": "exists"
          }
      ],
      "dependencies": [
        "put_file_request"
      ]
    }
  ],
  "response_reference_map": {
    "file_path": "REF:put_file_request.response_body.file_path",
    "file_type": "REF:put_file_request.response_body.file_type",
    "status_code": "REF:put_file_request.status_code",
    "response_body": "REF:put_file_request.response_body",
    "data_status_code": "REF:put_file_data_request.status_code",
    "data_response_body": "REF:put_file_data_request.response_body"
  },
  "responses": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path of the created file",
      "required": true
    },
    {
      "name": "file_type",
      "type_name": "string",
      "description": "The type of the created file",
      "required": true
    },
    {
      "name": "status_code",
      "type_name": "number",
      "description": "The responding status code from the file creation API call",
      "required": true
    },
    {
      "name": "response_body",
      "type_name": "object",
      "description": "The response body from the file creation API call",
      "required": false
    },
    {
      "name": "data_status_code",
      "type_name": "number",
      "description": "The responding status code from the file data write API call",
      "required": false
    },
    {
      "name": "data_response_body",
      "type_name": "object",
      "description": "The response body from the file data write API call",
      "required": false
    }
  ]
}