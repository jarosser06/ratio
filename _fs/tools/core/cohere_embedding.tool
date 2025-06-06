{
  "description": "An tool that generates embeddings using Cohere Embed models through Amazon Bedrock. It processes text inputs and optionally images to generate embedding vectors for semantic search, classification, clustering, and RAG applications.",
  "arguments": [
    {
      "name": "texts",
      "type_name": "list",
      "description": "Array of strings to embed (required if images not provided)",
      "required": false,
      "required_conditions": [
        {
          "param": "images",
          "operator": "not_exists"
        }
      ]
    },
    {
      "name": "images",
      "type_name": "list", 
      "description": "Array of image paths to embed (required if texts not provided. MAX 1 IMAGE)",
      "required": false,
      "required_conditions": [
        {
          "param": "texts",
          "operator": "not_exists"
        }
      ]
    },
    {
      "name": "model_id",
      "type_name": "string",
      "description": "The Cohere embedding model ID to use",
      "default_value": "cohere.embed-english-v3",
      "required": false
    },
    {
      "name": "input_type",
      "type_name": "string",
      "description": "Type of input to prepend special tokens",
      "enum": ["search_document", "search_query", "classification", "clustering", "image"],
      "default_value": "search_document",
      "required": false
    },
    {
      "name": "truncate",
      "type_name": "string",
      "description": "How to handle inputs longer than maximum token length",
      "enum": ["NONE", "START", "END"],
      "default_value": "NONE",
      "required": false
    },
    {
      "name": "embedding_types",
      "type_name": "list",
      "description": "Types of embeddings to return (float, binary, ubinary)",
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
      "description": "Path to the file containing the embedding vectors",
      "required": true
    },
    {
      "name": "embedding_dimensions",
      "type_name": "number",
      "description": "Number of dimensions in each embedding",
      "required": true
    },
    {
      "name": "num_embeddings",
      "type_name": "number", 
      "description": "Number of embeddings generated",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::tool::bedrock::cohere_embedding::execution"
}