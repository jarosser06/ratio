{
  "description": "Loads multiple files and combines their content into a single string, optionally saving to an output file",
  "arguments": [
    {
      "name": "content_list",
      "type_name": "list",
      "description": "List of content strings to load and combine",
      "required": false
    },
    {
      "name": "file_paths",
      "type_name": "list",
      "description": "List of file paths to load and combine",
      "required": false
    },
    {
      "name": "separator",
      "type_name": "string",
      "description": "Separator to use between file contents",
      "default_value": "\n\n",
      "required": false
    },
    {
      "name": "output_file_path",
      "type_name": "string",
      "description": "Optional path to save the combined content",
      "required": false
    },
    {
      "name": "output_file_type",
      "type_name": "string",
      "description": "File type for the output file",
      "default_value": "ratio::text",
      "required": false
    }
  ],
  "responses": [
    {
      "name": "combined_content",
      "type_name": "string",
      "description": "The combined content from all files",
      "required": true
    },
    {
      "name": "output_file_path",
      "type_name": "string",
      "description": "Path where the combined content was saved (if output_file_path was provided)",
      "required": false
    },
    {
      "name": "items_processed",
      "type_name": "number",
      "description": "Number of items that were successfully processed",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::tool::combine_content::execution"
}