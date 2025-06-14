{
  "arguments": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path of the file to describe",
      "required": true
    }
  ],
  "description": "A T2 tool that describes a file by calling the storage manager's describe file API and returns structured file information",
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
          },
          {
            "name": "file_path",
            "type_name": "string",
            "description": "The full path of the file",
            "required": true
          },
          {
            "name": "file_name",
            "type_name": "string",
            "description": "The name of the file",
            "required": true
          },
          {
            "name": "file_type",
            "type_name": "string",
            "description": "The type of the file",
            "required": true
          },
          {
            "name": "is_directory",
            "type_name": "boolean",
            "description": "True if the file is a directory",
            "required": true
          },
          {
            "name": "description",
            "type_name": "string",
            "description": "Description of the file",
            "required": false
          },
          {
            "name": "owner",
            "type_name": "string",
            "description": "The owner of the file",
            "required": true
          },
          {
            "name": "group",
            "type_name": "string",
            "description": "The group owner of the file",
            "required": true
          },
          {
            "name": "permissions",
            "type_name": "string",
            "description": "The file permissions",
            "required": true
          },
          {
            "name": "metadata",
            "type_name": "object",
            "description": "Additional metadata associated with the file",
            "required": false
          },
          {
            "name": "added_on",
            "type_name": "string",
            "description": "When the file was added",
            "required": true
          },
          {
            "name": "last_updated_on",
            "type_name": "string",
            "description": "When the file was last updated",
            "required": true
          },
          {
            "name": "last_accessed_on",
            "type_name": "string",
            "description": "When the file was last accessed",
            "required": false
          },
          {
            "name": "last_read_on",
            "type_name": "string",
            "description": "When the file was last read",
            "required": false
          },
          {
            "name": "latest_version_id",
            "type_name": "string",
            "description": "The ID of the latest version of the file",
            "required": false
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/storage/describe_file",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.file_path"
        }
      },
      "execution_id": "describe_file_request",
      "transform_responses": {
        "transforms": {
          "file_path": "response_body.file_path",
          "file_name": "response_body.file_name",
          "file_type": "response_body.file_type",
          "is_directory": "response_body.is_directory",
          "description": "response_body.description",
          "owner": "response_body.owner",
          "group": "response_body.group",
          "permissions": "response_body.permissions",
          "metadata": "response_body.metadata",
          "added_on": "response_body.added_on",
          "last_updated_on": "response_body.last_updated_on",
          "last_accessed_on": "response_body.last_accessed_on",
          "last_read_on": "response_body.last_read_on",
          "latest_version_id": "response_body.latest_version_id"
        }
      }
    }
  ],
  "response_reference_map": {
    "file_path": "REF:describe_file_request.file_path",
    "file_name": "REF:describe_file_request.file_name",
    "file_type": "REF:describe_file_request.file_type",
    "is_directory": "REF:describe_file_request.is_directory",
    "description": "REF:describe_file_request.description",
    "owner": "REF:describe_file_request.owner",
    "group": "REF:describe_file_request.group",
    "permissions": "REF:describe_file_request.permissions",
    "metadata": "REF:describe_file_request.metadata",
    "added_on": "REF:describe_file_request.added_on",
    "last_updated_on": "REF:describe_file_request.last_updated_on",
    "last_accessed_on": "REF:describe_file_request.last_accessed_on",
    "last_read_on": "REF:describe_file_request.last_read_on",
    "latest_version_id": "REF:describe_file_request.latest_version_id"
  },
  "responses": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path of the file",
      "required": true
    },
    {
      "name": "file_name",
      "type_name": "string",
      "description": "The name of the file",
      "required": true
    },
    {
      "name": "file_type",
      "type_name": "string",
      "description": "The type of the file",
      "required": true
    },
    {
      "name": "is_directory",
      "type_name": "boolean",
      "description": "True if the file is a directory",
      "required": true
    },
    {
      "name": "description",
      "type_name": "string",
      "description": "Description of the file",
      "required": false
    },
    {
      "name": "owner",
      "type_name": "string",
      "description": "The owner of the file",
      "required": true
    },
    {
      "name": "group",
      "type_name": "string",
      "description": "The group owner of the file",
      "required": true
    },
    {
      "name": "permissions",
      "type_name": "string",
      "description": "The file permissions",
      "required": true
    },
    {
      "name": "metadata",
      "type_name": "object",
      "description": "Additional metadata associated with the file",
      "required": false
    },
    {
      "name": "added_on",
      "type_name": "string",
      "description": "When the file was added",
      "required": true
    },
    {
      "name": "last_updated_on",
      "type_name": "string",
      "description": "When the file was last updated",
      "required": true
    },
    {
      "name": "last_accessed_on",
      "type_name": "string",
      "description": "When the file was last accessed",
      "required": false
    },
    {
      "name": "last_read_on",
      "type_name": "string",
      "description": "When the file was last read",
      "required": false
    },
    {
      "name": "latest_version_id",
      "type_name": "string",
      "description": "The ID of the latest version of the file",
      "required": false
    }
  ]
}