"""
Combine Content Tool
"""
import logging

from typing import Dict

import requests

from da_vinci.event_bus.client import fn_event_response

from ratio.tools.tool_lib import RatioSystem


@fn_event_response()
def handler(event: Dict, context: Dict):
    """
    Handler for the Combine Content Tool.
    """
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        file_paths = system.arguments.get("file_paths", default_return=None)

        content_list = system.arguments.get("content_list", default_return=None)

        separator = system.arguments.get("separator", default_return="\n\n")

        output_file_path = system.arguments.get("output_file_path", default_return=None)

        output_file_type = system.arguments.get("output_file_type", default_return="ratio::text")

        if not file_paths and not content_list:
            system.failure("No input provided, must provide either file_paths or content_list")

            return

        combined_contents = []

        items_processed = 0

        # First, process file paths if provided
        if file_paths:
            logging.info(f"Loading {len(file_paths)} files")

            for file_path in file_paths:
                logging.debug(f"Loading file: {file_path}")

                # Get the pre-signed URL
                direct_resp = system._storage_request(
                    path="/get_direct_file_version",
                    request={
                        "file_path": file_path
                    }
                )

                if direct_resp.status_code != 200:
                    logging.warning(f"Failed to get direct URL for {file_path}: {direct_resp.status_code}")

                    continue

                # Track lineage
                system.add_source_file(source_file_path=file_path)

                pre_signed_url = direct_resp.response_body["download_url"]

                # Fetch content directly from pre-signed URL
                response = requests.get(pre_signed_url)

                response.raise_for_status()

                content = response.text

                if content:  # Only add non-empty content
                    combined_contents.append(content)

                items_processed += 1

        # Then, add direct content if provided
        if content_list:
            logging.info(f"Adding {len(content_list)} direct content items")

            for content in content_list:
                if content:  # Only add non-empty content
                    combined_contents.append(str(content))

                items_processed += 1

        # Join all contents with separator
        combined_content = separator.join(combined_contents)

        total_sources = (len(file_paths) if file_paths else 0) + (len(content_list) if content_list else 0)

        logging.info(f"Successfully combined {items_processed}/{total_sources} items into {len(combined_content)} characters")

        response_data = {
            "combined_content": combined_content,
            "items_processed": items_processed
        }

        # Optionally save to output file
        if output_file_path:
            logging.info(f"Saving combined content to {output_file_path}")

            input_methods = []

            if file_paths:
                input_methods.append("file_paths")

            if content_list:
                input_methods.append("content_list")

            system.put_file(
                file_path=output_file_path,
                file_type=output_file_type,
                data=combined_content,
                metadata={
                    "created_by": "combine_content_tool",
                    "source_items_count": items_processed,
                    "total_content_length": len(combined_content),
                    "input_methods": input_methods
                }
            )

            response_data["output_file_path"] = output_file_path

        system.success(response_data)