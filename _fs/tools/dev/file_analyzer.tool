{
  "description": "Loads a file and analyzes it with a given prompt using an LLM",
  "arguments": [
    {
      "name": "file_to_analyze",
      "type_name": "file",
      "description": "File to analyze with the LLM",
      "required": true
    },
    {
      "name": "analysis_prompt",
      "type_name": "string", 
      "description": "The prompt/question to ask about the file content",
      "required": true
    },
    {
      "name": "model_id",
      "type_name": "string",
      "description": "The model to use for analysis",
      "default_value": "anthropic.claude-3-5-haiku-20241022-v1:0",
      "required": false
    },
    {
      "name": "max_tokens",
      "type_name": "number",
      "description": "Maximum tokens in response",
      "default_value": 1500,
      "required": false
    },
    {
      "name": "temperature", 
      "type_name": "number",
      "description": "Temperature for response generation",
      "default_value": 0.1,
      "required": false
    }
  ],
  "instructions": [
    {
      "execution_id": "analyze_with_llm",
      "tool_definition_path": "/tools/core/bedrock_text.tool",
      "transform_arguments": {
        "variables": {
          "prompt_parts": ["REF:arguments.analysis_prompt", "REF:arguments.file_to_analyze"],
          "separator": "\n\n"
        },
        "transforms": {
          "prompt": "join(array=prompt_parts, separator=separator)"
        }
      },
      "arguments": {
        "model_id": "REF:arguments.model_id", 
        "max_tokens": "REF:arguments.max_tokens",
        "temperature": "REF:arguments.temperature"
      }
    }
  ],
  "responses": [
    {
      "name": "analysis_result",
      "type_name": "string",
      "description": "The LLM's analysis of the file",
      "required": true
    },
    {
      "name": "analyzed_file_path",
      "type_name": "string",
      "description": "Path of the file that was analyzed", 
      "required": true
    }
  ],
  "response_reference_map": {
    "analysis_result": "REF:analyze_with_llm.response",
    "analyzed_file_path": "REF:arguments.file_to_analyze.path"
  }
}