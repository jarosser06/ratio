"""
Amazon Bedrock Titan Embedding Agent

This agent generates embeddings using Amazon Titan Text Embedding models through Amazon Bedrock. 
It processes text inputs to generate embedding vectors.
"""
import boto3
import json
import logging
import os
import uuid

from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.event_bus.client import fn_event_response

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.agents.agent_lib import RatioSystem

from ratio.agents.bedrock.runtime.exceptions import ResponseSaveError


_FN_NAME = "ratio.agents.bedrock.titan.embedding"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the Bedrock Titan Embedding agent
    """
    logging.debug(f"Received request: {event}")

    # Initialize the Ratio system from the event
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        input_text = system.arguments["input_text"]

        model_id = system.arguments["model_id"]

        dimensions = system.arguments.get("dimensions", default_return=1024)

        normalize = system.arguments.get("normalize", default_return=True)

        embedding_types = system.arguments.get("embedding_types", default_return=None)

        result_file_path = system.arguments.get("result_file_path")

        # Create Bedrock Runtime client
        bedrock_runtime = boto3.client("bedrock-runtime")

        try:
            # Prepare request body for Titan embedding models
            request_body = {
                "inputText": input_text,
                "dimensions": dimensions,
                "normalize": normalize
            }

            # Add embedding types if specified (V2 model feature)
            if embedding_types:
                request_body["embeddingTypes"] = embedding_types

            # Invoke the model
            response = bedrock_runtime.invoke_model(
                accept="application/json",
                body=json.dumps(request_body),
                contentType="application/json",
                modelId=model_id,
            )

            # Process the response
            response_body = json.loads(response.get('body').read())

            logging.debug(f"Model response: {response_body}")

            # Extract embedding and metadata
            embedding = response_body.get("embedding", [])

            if not embedding:
                system.failure(failure_message="No embedding returned from model")

                return

            input_token_count = response_body.get("inputTextTokenCount", 0)

            embedding_dimensions = len(embedding)

            # Handle different response formats (V1 vs V2)
            embeddings_by_type = response_body.get("embeddingsByType", {})

            # Create result file path if not provided
            if not result_file_path:
                result_file_path = os.path.join(system.working_directory, f"titan_embedding_{uuid.uuid4()}.json")

            # Save embedding to file
            try:
                result_data = {
                    "embedding": embedding,
                    "model_id": model_id,
                    "input_text": input_text,
                    "input_token_count": input_token_count,
                    "embedding_dimensions": embedding_dimensions,
                    "dimensions": dimensions,
                    "normalize": normalize
                }

                # Include embeddings by type if available (V2 model)
                if embeddings_by_type:
                    result_data["embeddings_by_type"] = embeddings_by_type

                system.put_file(
                    file_path=result_file_path,
                    file_type="ratio::file",
                    data=json.dumps(result_data, indent=2),
                    metadata={
                        "model_id": model_id,
                        "input_token_count": input_token_count,
                        "embedding_dimensions": embedding_dimensions
                    }
                )

            except Exception as put_file_error:
                raise ResponseSaveError(f"Failed to save embedding to {result_file_path}: {put_file_error}")

            # Return success with metrics
            system.success(
                response_body={
                    "model_id": model_id,
                    "input_token_count": input_token_count,
                    "embedding_dimensions": embedding_dimensions,
                    "response_file_path": result_file_path,
                }
            )

        except Exception as invoke_error:
            logging.error(f"Failed to invoke Titan embedding model: {invoke_error}")

            system.failure(failure_message=f"Failed to invoke Titan embedding model {model_id}: {invoke_error}")

            return