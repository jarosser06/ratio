"""
Amazon Bedrock Anthropic Agent

This agent invokes Anthropic Claude models through Amazon Bedrock. It processes text prompts 
with optional attachments (images or PDFs) and saves responses to a file.
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


_FN_NAME = "ratio.agents.bedrock.anthropic"


class ResponseSaveError(Exception):
    """Exception raised for errors related to saving responses."""
    pass


SUPPORTED_IMAGE_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png", 
    "image/webp",
}


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the Bedrock Anthropic agent
    """
    logging.debug(f"Received request: {event}")

    # Initialize the Ratio system from the event
    system = RatioSystem.from_da_vinci_event(event)

    # Raise any errors encountered during execution
    system.raise_on_failure = True

    with system:
        prompt = system.arguments["prompt"]

        model_id = system.arguments["model_id"]

        temperature = system.arguments.get("temperature", default_return=0.7)

        max_tokens = system.arguments.get("max_tokens", default_return=1000)

        top_p = system.arguments.get("top_p", default_return=0.9)

        attachment_paths = system.arguments.get("attachment_paths", default_return=[])

        attachment_type = system.arguments.get("attachment_content_type")

        result_file_path = system.arguments.get("result_file_path")

        # Create Bedrock Runtime client
        bedrock_runtime = boto3.client("bedrock-runtime")

        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }

        # Handle different formats for Claude models
        if attachment_paths:
            # Validate attachment count (Bedrock limit is 20 images)
            if len(attachment_paths) > 20:
                logging.debug(f"Too many attachments: {len(attachment_paths)} (limit is 20)")
                system.failure(failure_message=f"Too many attachments: {len(attachment_paths)}. Maximum allowed is 20.")
                return

            content_blocks = []

            # Process each attachment
            for i, attachment_path in enumerate(attachment_paths):
                try:
                    logging.debug(f"Processing attachment {i+1}/{len(attachment_paths)}: {attachment_path}")

                    # Use the helper method to get binary file as base64
                    binary_file = system.get_binary_file_version(attachment_path)

                    attachment_data = binary_file["data"]

                    if attachment_type:
                        content_type = attachment_type

                    else:
                        content_type = binary_file["content_type"]

                    # Validate supported image types
                    if content_type not in SUPPORTED_IMAGE_TYPES:
                        logging.debug(f"Attachment content type {content_type} is not supported for {attachment_path}")

                        system.failure(failure_message=f"Attachment content type {content_type} is not supported for {attachment_path}")

                        return

                    # Add image to content blocks
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": attachment_data
                        }
                    })

                    logging.debug(f"Loaded {binary_file['original_format']} file as base64, content type: {content_type}")

                except Exception as attach_error:
                    logging.debug(f"Failed to load attachment {attachment_path}: {attach_error}")
                    system.failure(failure_message=f"Failed to load attachment {attachment_path}: {attach_error}")
                    return

            # Add text prompt at the end
            content_blocks.append({
                "type": "text",
                "text": prompt
            })

            # Format with multimodal content
            request_body["messages"] = [
                {
                    "role": "user",
                    "content": content_blocks
                }
            ]

        else:
            # Text-only content
            request_body["messages"] = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt
                        }
                    ]
                }
            ]

        # Invoke the model
        response = bedrock_runtime.invoke_model(
            accept="application/json",
            body=json.dumps(request_body),
            contentType="application/json",
            modelId=model_id,
        )

        # Process the response
        response_body = json.loads(response.get('body').read())

        # Extract content from the response
        model_response = ""

        if "content" in response_body and isinstance(response_body["content"], list):
            for content_item in response_body["content"]:
                if content_item.get("type") == "text":
                    model_response += content_item.get("text", "")

        # Get token usage
        input_tokens = response_body.get("usage", {}).get("input_tokens", 0)

        output_tokens = response_body.get("usage", {}).get("output_tokens", 0)

        # Create result file path if not provided
        if not result_file_path:
            result_file_path = os.path.join(system.working_directory, f"response_{uuid.uuid4()}.txt")

        # Save response to file
        try:
            system.put_file(
                file_path=result_file_path,
                file_type="ratio::file",
                data=model_response,
                metadata={
                    "model_id": model_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                }
            )

        except Exception as put_file_error:
            raise ResponseSaveError(f"Failed to save response to {result_file_path}: {put_file_error}")

        # Return success with metrics
        system.success(
            response_body={
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "response_file_path": result_file_path,
            }
        )