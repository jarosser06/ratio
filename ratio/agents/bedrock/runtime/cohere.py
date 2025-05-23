"""
Amazon Bedrock Cohere Embedding Agent

This agent generates embeddings using Cohere Embed models through Amazon Bedrock. 
It processes text inputs and optionally images to generate embedding vectors.
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


_FN_NAME = "ratio.agents.bedrock.cohere.embedding"


SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
}


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the Bedrock Cohere Embedding agent
    """
    logging.debug(f"Received request: {event}")

    # Initialize the Ratio system from the event
    system = RatioSystem.from_da_vinci_event(event)

    # Raise any errors encountered during execution
    system.raise_on_failure = True

    with system:
        texts = system.arguments.get("texts", default_return=[])

        images = system.arguments.get("images", default_return=[])

        model_id = system.arguments["model_id"]

        input_type = system.arguments.get("input_type", default_return="search_document")

        truncate = system.arguments.get("truncate", default_return="NONE")

        embedding_types = system.arguments.get("embedding_types", default_return=None)

        result_file_path = system.arguments.get("result_file_path")

        # Validate input - must have either texts or images
        if not texts and not images:
            system.failure(failure_message="Must provide either 'texts' or 'images' parameter")

            return

        if texts and images:
            system.failure(failure_message="Cannot provide both 'texts' and 'images' - choose one")

            return

        # Create Bedrock Runtime client
        bedrock_runtime = boto3.client("bedrock-runtime")

        try:
            # Prepare request body
            request_body = {
                "input_type": input_type,
                "truncate": truncate
            }

            if embedding_types:
                request_body["embedding_types"] = embedding_types

            # Handle text input
            if texts:
                request_body["texts"] = texts

            # Handle image input
            if images:
                if len(images) > 1:
                    system.failure(failure_message="Cohere embedding models support maximum 1 image per request")

                    return

                image_path = images[0]

                try:
                    # Use the helper method to get binary file but not decode since we need base64
                    binary_file = system.get_binary_file_version(file_path=image_path, decode=False)
                    
                    content_type = binary_file["content_type"]

                    if content_type not in SUPPORTED_IMAGE_TYPES:
                        system.failure(failure_message=f"Unsupported image type {content_type}. Supported: {list(SUPPORTED_IMAGE_TYPES)}")

                        return

                    # Cohere expects data URI format for images
                    image_data_uri = f"data:{content_type};base64,{binary_file['data']}"

                    request_body["images"] = [image_data_uri]

                    logging.debug(f"Loaded image {image_path} as data URI, content type: {content_type}")

                except Exception as image_error:
                    logging.debug(f"Failed to load image {image_path}: {image_error}")

                    system.failure(failure_message=f"Failed to load image {image_path}: {image_error}")

                    return

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

            # Extract embeddings
            embeddings = response_body.get("embeddings", [])
            if not embeddings:
                system.failure(failure_message="No embeddings returned from model")

                return

            # Get metadata
            num_embeddings = len(embeddings)

            embedding_dimensions = len(embeddings[0]) if embeddings else 0

            # Create result file path if not provided
            if not result_file_path:
                result_file_path = os.path.join(system.working_directory, f"cohere_embeddings_{uuid.uuid4()}.json")

            # Save embeddings to file
            try:
                result_data = {
                    "embeddings": embeddings,
                    "model_id": model_id,
                    "input_type": input_type,
                    "num_embeddings": num_embeddings,
                    "embedding_dimensions": embedding_dimensions,
                    "response_metadata": {
                        "id": response_body.get("id"),
                        "response_type": response_body.get("response_type"),
                        "texts": response_body.get("texts", []),
                        "images": response_body.get("images", [])
                    }
                }

                system.put_file(
                    file_path=result_file_path,
                    file_type="ratio::file",
                    data=json.dumps(result_data, indent=2),
                    metadata={
                        "model_id": model_id,
                        "num_embeddings": num_embeddings,
                        "embedding_dimensions": embedding_dimensions
                    }
                )

            except Exception as put_file_error:
                raise ResponseSaveError(f"Failed to save embeddings to {result_file_path}: {put_file_error}")

            # Return success with metrics
            system.success(
                response_body={
                    "model_id": model_id,
                    "num_embeddings": num_embeddings,
                    "embedding_dimensions": embedding_dimensions,
                    "response_file_path": result_file_path,
                }
            )

        except Exception as invoke_error:
            logging.error(f"Failed to invoke Cohere embedding model: {invoke_error}")

            system.failure(failure_message=f"Failed to invoke Cohere embedding model {model_id}: {invoke_error}")

            return