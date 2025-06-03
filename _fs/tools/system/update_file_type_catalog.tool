{
  "description": "Syncs file types to markdown catalog",
  "instructions": [
    {
      "execution_id": "fetch_file_types",
      "tool_definition_path": "/tools/core/internal_api.tool",
      "arguments": {
        "path": "/list_file_types",
        "target_service": "STORAGE",
        "request": {}
      }
    },
    {
      "execution_id": "render_catalog",
      "tool_definition_path": "/tools/core/render_template.tool",
      "arguments": {
        "template": "# Ratio File Types Catalog\n\n*Auto-generated on {{ timestamp }}*\n\n## Available File Types\n\n{% for file_type in file_types %}### `{{ file_type.type_name }}`\n\n**Description:** {{ file_type.description or 'No description provided' }}\n\n- **Directory Type:** {{ 'Yes' if file_type.is_directory_type else 'No' }}\n- **Content Type:** {{ file_type.content_type or 'Not specified' }}\n- **Added:** {{ file_type.added_on }}\n\n---\n{% endfor %}\n\n*Total file types: {{ file_types|length }}*"
      },
      "transform_arguments": {
        "variables": {
          "file_types_data": "REF:fetch_file_types.response_body.file_types"
        },
        "transforms": {
          "variables": "pipeline(\"\", [datetime_now(), create_object(file_types=file_types_data, timestamp=current)])" 
        }
      }
    },
    {
      "execution_id": "update_catalog",
      "tool_definition_path": "/tools/core/put_file.tool",
      "arguments": {
        "file_path": "/system/catalog/file_types.md",
        "file_type": "ratio::markdown",
        "data": "REF:render_catalog.rendered_string",
        "owner": "system",
        "group": "system",
        "permissions": "644",
        "origin": "internal"
      }
    }
  ],
  "responses": [
    {
      "name": "catalog_path",
      "type_name": "string",
      "required": true
    }
  ],
  "response_reference_map": {
    "catalog_path": "REF:update_catalog.file_path"
  }
}