"""
Math Agent Runtime

Simple agent that uses the MathProcessor class to evaluate formulas.
"""
import json
import os
import uuid

from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.event_bus.client import fn_event_response

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.agents.agent_lib import RatioSystem

from ratio.agents.math.runtime.math import MathProcessor


_FN_NAME = "ratio.agents.math"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """Execute the Math agent"""
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        formula = system.arguments["formula"]

        values = system.arguments["values"] 

        function_definitions = system.arguments.get("function_definitions", default_return={})

        result_file_path = system.arguments.get("result_file_path")

        # Do MAHT :)
        processor = MathProcessor(function_definitions)

        result = processor.evaluate(values, formula)

        # Save result to file
        if not result_file_path:
            result_file_path = os.path.join(system.working_directory, f"math_result_{uuid.uuid4()}.json")

        result_data = {
            "formula": formula,
            "result": result,
            "values": values
        }

        system.put_file(
            file_path=result_file_path,
            file_type="ratio::file",
            data=json.dumps(result_data, default=str)
        )

        # Return result
        system.success(response_body={
            "result": result,
            "result_file_path": result_file_path,
            "formula_used": formula,
            "functions_available": len(processor.get_available_functions())
        })