"""
String Concatenation Agent
"""
from da_vinci.event_bus.client import fn_event_response

from ratio.agents.agent_lib import RatioSystem


@fn_event_response()
def handler(event, context):
    """Concatenate strings."""
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        result = system.arguments["string1"] + system.arguments.get("separator", default_return="") + system.arguments["string2"]

        system.success({
            "concatenated_string": result
        })