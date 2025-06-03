{
  "description": "An tool that renders Jinja templates with provided variables to generate formatted strings",
  "arguments": [
    {
      "name": "template",
      "type_name": "string",
      "description": "The Jinja template string with placeholders (e.g., 'Hello {{ name }}!')",
      "required": true
    },
    {
      "name": "variables",
      "type_name": "object",
      "description": "Dictionary of variables to inject into the template",
      "required": true
    },
    {
      "name": "file_path",
      "type_name": "file",
      "description": "An optional file path to save the results to",
      "required": false
    },
    {
      "name": "strict_undefined",
      "type_name": "boolean",
      "description": "Whether to raise an error for undefined variables (true) or treat them as empty strings (false)",
      "default_value": false,
      "required": false
    },
    {
      "name": "autoescape",
      "type_name": "boolean",
      "description": "Whether to automatically escape HTML/XML in output (recommended for web content)",
      "default_value": true,
      "required": false
    },
    {
      "name": "trim_blocks",
      "type_name": "boolean",
      "description": "Whether to trim blocks of whitespace after control statements",
      "default_value": true,
      "required": false
    }
  ],
  "responses": [
    {
      "name": "rendered_string",
      "type_name": "string",
      "description": "The template rendered with the provided variables",
      "required": true
    },
    {
      "name": "file_path",
      "type_name": "file",
      "description": "The optional file path to save the results to",
      "required": false
    },
    {
      "name": "used_variables",
      "type_name": "list",
      "description": "List of variable names that were actually used in the template",
      "required": false
    }
  ],
  "system_event_endpoint": "ratio::tool::render_template::execution"
}