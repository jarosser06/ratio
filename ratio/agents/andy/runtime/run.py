"""
Andy Dwyer a.k.a Agent Burt Macklin, FBI

This is a very simple agent that is used for initial testing of the agent execution system.
"""
import logging

from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.exception_trap.client import ExceptionReporter

from da_vinci.event_bus.client import fn_event_response

from ratio.agents.agent_lib import RatioSystem


_FN_NAME = "ratio.agents.andy"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the dumb agent
    """
    logging.debug(f"Received request: {event}")

    system = RatioSystem.from_da_vinci_event(event)

    with system:
        file_to_review = system.arguments.get("file_for_review")

        base_message = f"This is special agent Burt Macklin, badge number {system.process_id}"

        if file_to_review:
            response_message = "I\'ve recieved your file for review. Evil doers beware, Burt Macklin on the case!"

        else:
            response_message = "I never recieved instructions to review. Therefore, I will be reopening the case of the Peach Pit Turd!"

        full_response = base_message + "\n\n" + response_message

        system.success(
            response_body={
                "response": full_response
            }
        )