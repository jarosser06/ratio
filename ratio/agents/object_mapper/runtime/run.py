"""
Object Mapper Agent Execution Code
"""
import logging

from typing import Dict, List

from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody, ObjectBodySchema

from da_vinci.event_bus.client import fn_event_response

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.agents.agent_lib import RatioSystem

from ratio.agents.object_mapper.runtime.mapper import (
    DEFAULT_MAPPING_FUNCTIONS,
    MappingError,
    ObjectMapper,
)


def object_mapper_agent(original_object: Dict, object_map: Dict, response_schema: List[Dict]) -> Dict:
    """
    Agent entry point for the object mapper agent.

    Keyword arguments:
    original_object -- The original object to be transformed
    object_map -- The mapping rules to apply
    response_schema -- The schema to validate the transformed object against

    Returns:
        The transformed and validated object structure
    """
    try:
        # Create the mapper with default functions
        mapper = ObjectMapper(DEFAULT_MAPPING_FUNCTIONS)

        # Create schema dictionary in the format expected by ObjectBodySchema
        schema_dict = {
            "attributes": response_schema,
            "vanity_types": {
                "file": "string",  # Map any vanity types to their base types
            }
        }

        # Perform the mapping using our custom logic
        mapped_result = mapper.map_object(original_object, object_map, response_schema)
        
        # Validate against the schema using ObjectBody
        schema = ObjectBodySchema.from_dict("response_schema", schema_dict)

        validated_object = ObjectBody(mapped_result, schema)

        # Return the validated result
        return validated_object.to_dict()

    except Exception as e:
        # Convert any errors to a standardized format
        if isinstance(e, MappingError):
            raise

        raise MappingError(f"Failed to map object: {str(e)}")


_FN_NAME = "ratio.agents.object_mapper"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the Agent
    """
    logging.debug(f"Received request: {event}")

    # Initialize the Ratio system from the event
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        if not system.response_schema:
            raise ValueError("No response schema provided ... nothing to map to")

        original_object = system.arguments["original_object"]

        if isinstance(original_object, ObjectBody):
            original_object = original_object.to_dict()

        object_map = system.arguments["object_map"]

        if isinstance(object_map, ObjectBody):
            object_map = object_map.to_dict()

        logging.debug(f"Mapping original_object: {original_object} with object_map: {object_map}")

        response_schema_dict = system.response_schema.to_dict()

        response_attrs = response_schema_dict.get("attributes", [])

        mapped_result = object_mapper_agent(original_object, object_map, response_attrs)

        system.success(response_body=mapped_result)