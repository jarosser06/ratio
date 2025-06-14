{
  "arguments": [
    {
      "name": "file_path",
      "type_name": "string",
      "description": "The full path of the file to describe the version for",
      "required": true
    },
    {
      "name": "version_id",
      "type_name": "string",
      "description": "The version ID to describe. If not provided, describes the latest version",
      "required": false
    },
    {
      "name": "include_lineage",
      "type_name": "boolean",
      "description": "Whether to include lineage information in the response",
      "required": false,
      "default_value": false
    }
  ],
  "description": "An tool that describes a specific version of a file by calling the storage manager's describe file version API",
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
            "name": "version_id",
            "type_name": "string",
            "description": "The version ID of the file",
            "required": true
          },
          {
            "name": "metadata",
            "type_name": "object",
            "description": "Additional metadata associated with the file version",
            "required": false
          },
          {
            "name": "originator_id",
            "type_name": "string",
            "description": "The ID of the originator who created this version",
            "required": true
          },
          {
            "name": "origin",
            "type_name": "string",
            "description": "The origin of the file version (internal/external)",
            "required": true
          },
          {
            "name": "added_on",
            "type_name": "string",
            "description": "When the file version was added",
            "required": true
          },
          {
            "name": "previous_version_id",
            "type_name": "string",
            "description": "The version ID of the previous version",
            "required": false
          },
          {
            "name": "next_version_id",
            "type_name": "string",
            "description": "The version ID of the next version",
            "required": false
          }
        ],
        "system_event_endpoint": "ratio::tool::internal_api::execution"
      },
      "arguments": {
        "path": "/storage/describe_file_version",
        "target_service": "STORAGE",
        "request": {
          "file_path": "REF:arguments.file_path",
          "version_id": "REF:arguments.version_id",
          "include_lineage": "REF:arguments.include_lineage"
        }
      },
      "execution_id": "describe_file_version_request",
      "transform_responses": {
        "transforms": {
          "file_path": "response_body.file_path",
          "file_name": "response_body.file_name",
          "version_id": "response_body.version_id",
          "metadata": "response_body.metadata",
          "originator_id": "response_body.originator_id",
          "origin": "response_body.origin",
          "added_on": "response_body.added_on",
          "previous_version_id": "response_body.previous_version_id",
          "next_version_id": "response_body.next_version_id"
        }
      }
    }
  ],
  "response_reference_map": {
    "file_path": "REF:describe_file_version_request.file_path",
    "file_name": "REF:describe_file_version_request.file_name",
    "version_id": "REF:describe_file_version_request.version_id",
    "metadata": "REF:describe_file_version_request.metadata",
    "originator_id": "REF:describe_file_version_request.originator_id",
    "origin": "REF:describe_file_version_request.origin",
    "added_on": "REF:describe_file_version_request.added_on",
    "previous_version_id": "REF:describe_file_version_request.previous_version_id",
    "next_version_id": "REF:describe_file_version_request.next_version_id"
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
      "name": "version_id",
      "type_name": "string",
      "description": "The version ID of the file",
      "required": true
    },
    {
      "name": "metadata",
      "type_name": "object",
      "description": "Additional metadata associated with the file version",
      "required": false
    },
    {
      "name": "originator_id",
      "type_name": "string",
      "description": "The ID of the originator who created this version",
      "required": true
    },
    {
      "name": "origin",
      "type_name": "string",
      "description": "The origin of the file version (internal/external)",
      "required": true
    },
    {
      "name": "added_on",
      "type_name": "string",
      "description": "When the file version was added",
      "required": true
    },
    {
      "name": "previous_version_id",
      "type_name": "string",
      "description": "The version ID of the previous version",
      "required": false
    },
    {
      "name": "next_version_id",
      "type_name": "string",
      "description": "The version ID of the next version",
      "required": false
    }
  ]
}