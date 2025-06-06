{
  "description": "An tool that generates embeddings using Amazon Titan Text Embedding models through Amazon Bedrock. It processes text inputs to generate embedding vectors for semantic search, RAG, classification, and clustering applications.",
  "arguments": [
    {
      "name": "input_text",
      "type_name": "string",
      "description": "The text to convert to an embedding",
      "required": true
    },
    {
      "name": "model_id",
      "type_name": "string",
      "description": "The Titan embedding model ID to use",
      "default_value": "amazon.titan-embed-text-v2:0",
      "required": false
    },
    {
      "name": "dimensions",
      "type_name": "number",
      "description": "Number of dimensions for the output embedding",
      "enum": [256, 512, 1024],
      "default_value": 1024,
      "required": false
    },
    {
      "name": "normalize",
      "type_name": "boolean",
      "description": "Whether to normalize the output embedding",
      "default_value": true,
      "required": false
    },
    {
      "name": "embedding_types",
      "type_name": "list",
      "description": "Types of embeddings to return (float, binary)",
      "required": false
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
      "name": "response_file_path",
      "type_name": "file",
      "description": "Path to the file containing the embedding vector",
      "required": true
    },
    {
      "name": "embedding_dimensions",
      "type_name": "number",
      "description": "Number of dimensions in the embedding",
      "required": true
    },
    {
      "name": "input_token_count",
      "type_name": "number",
      "description": "Number of tokens in the input text",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::tool::bedrock::titan_embedding::execution"
}