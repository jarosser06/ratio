{
  "description": "An tool that invokes Anthropic Claude models through Amazon Bedrock. It processes text prompts with optional attachments (images or PDFs) and saves responses to a file. This tool is specifically designed for Anthropic model formats and parameters.",
  "arguments": [
    {
      "name": "prompt",
      "type_name": "string",
      "description": "The text prompt to send to the model",
      "required": true
    },
    {
      "name": "model_id",
      "type_name": "string",
      "description": "The Anthropic model ID to use (e.g., 'anthropic.claude-3-sonnet-20240229-v1')",
      "default_value": "anthropic.claude-3-5-haiku-20241022-v1:0",
      "required": false
    },
    {
      "name": "temperature",
      "type_name": "number",
      "description": "Controls randomness in output generation (0.0-1.0)",
      "default_value": 0.7,
      "required": false
    },
    {
      "name": "max_tokens",
      "type_name": "number",
      "description": "Maximum number of tokens to generate in the response",
      "default_value": 1000,
      "required": false
    },
    {
      "name": "top_p",
      "type_name": "number",
      "description": "Nucleus sampling parameter (0.0-1.0)",
      "required": false,
      "default_value": 0.9
    },
    {
      "name": "attachment_paths",
      "type_name": "list",
      "description": "Paths to an optional attachment image files to include with the prompt",
      "required": false
    },
    {
      "name": "attachment_content_type",
      "type_name": "string",
      "description": "type_name of the attachment file",
      "required": false,
      "enum": ["image/jpeg", "image/png", "image/gif", "image/webp"]
    },
    {
      "name": "result_file_path",
      "type_name": "string",
      "description": "Path where the result should be saved. If not provided, a file will be created in the working directory",
      "required": false
    }
  ],
  "responses": [
    {
      "name": "model_id",
      "type_name": "string",
      "description": "The model ID that was executed to generate the request",
      "required": true
    },
    {
      "name": "response",
      "type_name": "string",
      "description": "The direct response from the model",
      "required": true
    },
    {
      "name": "response_file_path",
      "type_name": "file",
      "description": "Path to the file containing the model's response",
      "required": false
    },
    {
      "name": "input_tokens",
      "type_name": "number",
      "description": "Number of tokens in the input prompt",
      "required": true
    },
    {
      "name": "output_tokens",
      "type_name": "number",
      "description": "Number of tokens in the output response",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::tool::bedrock::text::execution"
}