"""
Template Renderer Tool

This tool renders Jinja templates with provided variables to generate formatted strings.
"""
from typing import Dict


from jinja2 import Environment, meta, StrictUndefined, Undefined

from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody

from da_vinci.exception_trap.client import ExceptionReporter
from da_vinci.event_bus.client import fn_event_response

from ratio.tools.tool_lib import RatioSystem


_FN_NAME = "ratio.tools.render_template"


class TemplateRenderError(Exception):
    """Exception raised for errors during template rendering."""
    pass


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the Template Renderer tool
    """
    # Initialize the Ratio system from the event
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        template_str = system.arguments["template"]

        variables = system.arguments["variables"]

        if isinstance(variables, ObjectBody):
            variables = variables.to_dict()

        strict_undefined = system.arguments.get("strict_undefined", default_return=False)

        autoescape = system.arguments.get("autoescape", default_return=True)

        trim_blocks = system.arguments.get("trim_blocks", default_return=True)

        file_path = system.arguments.get("file_path", default_return=None)

        try:
            # Configure Jinja environment
            env = Environment(
                autoescape=autoescape,
                trim_blocks=trim_blocks,
                lstrip_blocks=True,  # Common setting to pair with trim_blocks
                undefined=StrictUndefined if strict_undefined else Undefined
            )

            ast = env.parse(template_str)

            used_vars = list(meta.find_undeclared_variables(ast))

            template = env.from_string(template_str)

            rendered_string = template.render(**variables)

            # Build response
            response = {
                "rendered_string": rendered_string,
                "used_variables": used_vars,
            }

            if file_path:
                response["file_path"] = file_path

                # Save the rendered string to a file
                system.put_file(
                    file_path=file_path,
                    file_type="ratio::text",
                    data=rendered_string,
                    metadata={
                        "description": "Rendered template output",
                    }
                )

            system.success(response_body=response)

        except Exception as e:
            raise TemplateRenderError(f"Failed to render template: {str(e)}")