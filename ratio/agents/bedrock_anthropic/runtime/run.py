"""
Amazon Bedrock Anthropic Agent

This agent invokes Anthropic Claude models through Amazon Bedrock. It processes text prompts 
with optional attachments (images or PDFs) and saves responses to a file.
"""
import base64
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


class AttachmentError(Exception):
    """Exception raised for errors related to attachment handling."""
    pass


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

        attachment_path = system.arguments.get("attachment_path", default_return=None)

        attachment_type = system.arguments.get("attachment_type", default_return=None)

        result_file_path = system.arguments.get("result_file_path", default_return=None)

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
        if attachment_path and attachment_type:
            # Get the attachment data
            file_response = system.get_file_version(attachment_path)

            file_data = file_response.get("data")

            if not file_data:
                raise AttachmentError(f"Failed to get attachment data from {attachment_path}")
                
            # Handle base64 encoded data if needed
            if isinstance(file_data, str):
                attachment_data = file_data

            else:
                attachment_data = base64.b64encode(file_data).decode('utf-8')

            # Format with multimodal content
            request_body["messages"] = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": attachment_type,
                                "data": attachment_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
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

        # Return success with metrics
        system.success(
            response_body={
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "response_file_path": result_file_path,
            }
        )