"""
Amazon Bedrock Text Agent

This agent invokes text generation models through Amazon Bedrock Converse API. It processes text prompts 
with optional attachments and saves responses to a file.
"""
import logging

from typing import Dict

import boto3

from da_vinci.core.logging import Logger

from da_vinci.event_bus.client import fn_event_response

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.agents.agent_lib import RatioSystem

from ratio.agents.bedrock.runtime.exceptions import ResponseSaveError


_FN_NAME = "ratio.agents.bedrock.text"


SUPPORTED_IMAGE_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png", 
    "image/webp",
}


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the Bedrock Text agent
    """
    # Initialize the Ratio system from the event
    system = RatioSystem.from_da_vinci_event(event)

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

        try:
            # Handle attachments if provided
            if attachment_paths:
                # Validate attachment count (Bedrock limit is 20 images)
                if len(attachment_paths) > 20:
                    logging.debug(f"Too many attachments: {len(attachment_paths)} (limit is 20)")

                    system.failure(failure_message=f"Too many attachments: {len(attachment_paths)}. Maximum allowed is 20.")

                    return

                content_blocks = []

                # Add text prompt first
                content_blocks.append({"text": prompt})

                # Process each attachment
                for i, attachment_path in enumerate(attachment_paths):
                    try:
                        logging.debug(f"Processing attachment {i+1}/{len(attachment_paths)}: {attachment_path}")

                        file_response = system.get_binary_file_version(file_path=attachment_path)

                        attachment_data = file_response["data"]

                        # Get content type from file details
                        file_details = system.get_file_details(attachment_path)

                        if attachment_type:
                            content_type = attachment_type

                        else:
                            content_type = file_details["content_type"]

                        # Validate supported image types
                        if content_type not in SUPPORTED_IMAGE_TYPES:
                            logging.debug(f"Attachment content type {content_type} is not supported for {attachment_path}")

                            system.failure(failure_message=f"Attachment content type {content_type} is not supported for {attachment_path}")

                            return

                        # Convert content type to format
                        image_format = content_type.split("/")[1]

                        if image_format == "jpg":
                            image_format = "jpeg"

                        system.add_source_file(source_file_path=attachment_path, source_file_version=file_response["version_id"])

                        # Add image to content blocks (Converse API format)
                        content_blocks.append({
                            "image": {
                                "format": image_format,
                                "source": {
                                    "bytes": attachment_data
                                }
                            }
                        })

                    except Exception as attach_error:
                        logging.debug(f"Failed to load attachment {attachment_path}: {attach_error}")

                        raise Exception(f"Failed to load attachment {attachment_path}") from attach_error

                # Use converse API with multimodal content
                response = bedrock_runtime.converse(
                    modelId=model_id,
                    messages=[{
                        "role": "user",
                        "content": content_blocks
                    }],
                    inferenceConfig={
                        "temperature": temperature,
                        "maxTokens": max_tokens,
                        "topP": top_p
                    }
                )

            else:
                # Text-only content
                response = bedrock_runtime.converse(
                    modelId=model_id,
                    messages=[{
                        "role": "user",
                        "content": [{"text": prompt}]
                    }],
                    inferenceConfig={
                        "temperature": temperature,
                        "maxTokens": max_tokens,
                        "topP": top_p
                    }
                )

            # Extract content from the response
            model_response = ""

            if "output" in response and "message" in response["output"]:
                content = response["output"]["message"].get("content", [])

                for content_item in content:
                    if "text" in content_item:
                        model_response += content_item["text"]

            # Get token usage
            usage = response["usage"]

            input_tokens = usage.get("inputTokens", 0)

            output_tokens = usage.get("outputTokens", 0)

            response_body={
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "response": model_response,
            }

            # Create result file path if not provided
            if result_file_path:
                # Save response to file
                try:
                    system.put_file(
                        file_path=result_file_path,
                        file_type="ratio::text",
                        data=model_response,
                        metadata={
                            "model_id": model_id,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens
                        }
                    )

                    response_body["response_file_path"] = result_file_path

                except Exception as put_file_error:
                    raise ResponseSaveError(f"Failed to save response to {result_file_path}: {put_file_error}")

            system.success(response_body=response_body)

        except Exception as invoke_error:
            logging.error(f"Failed to invoke Bedrock model: {invoke_error}")

            raise Exception(f"Failed to invoke Bedrock model {model_id}: {invoke_error}") from invoke_error