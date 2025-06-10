import os

from da_vinci_cdk.application import Application, ResourceDiscoveryStorageSolution
from da_vinci_cdk.stack import Stack

from ratio.core.services.auth.stack import AuthStack
from ratio.core.services.process_manager.stack import ProcessManagerStack
from ratio.core.services.scheduler.stack import SchedulerStack
from ratio.core.services.storage_manager.stack import StorageManagerStack

from ratio.tools.bedrock.stack import RatioBedrockTools
from ratio.tools.combine_content.stack import RatioCombineContentTool
from ratio.tools.internal_api.stack import RatioInternalAPITool
from ratio.tools.math.stack import RatioMathTool
from ratio.tools.render_template.stack import RatioRenderTemplateTool

base_dir = Stack.absolute_dir(__file__)

default_oauth_callback_urls = [
    "http://localhost:1618/auth/callback", # MCP Server (Locally Run)
]

ratio = Application(
    app_entry=base_dir,
    app_name="ratio",
    create_hosted_zone=False,
    custom_context={
        "oauth_callback_urls": default_oauth_callback_urls,
        "token_validity_hours": 8,
    },
    deployment_id=os.getenv("RATIO_DEPLOYMENT_ID", "dev"),
    disable_docker_image_cache=True,
    enable_exception_trap=True,
    enable_event_bus=True,
    log_level=os.getenv("RATIO_LOG_LEVEL", "DEBUG"),
    resource_discovery_storage_solution=ResourceDiscoveryStorageSolution.DYNAMODB,
)

# Services
ratio.add_uninitialized_stack(AuthStack)

ratio.add_uninitialized_stack(StorageManagerStack)

ratio.add_uninitialized_stack(ProcessManagerStack)

ratio.add_uninitialized_stack(SchedulerStack)

# Tools
ratio.add_uninitialized_stack(RatioInternalAPITool)

ratio.add_uninitialized_stack(RatioBedrockTools)

ratio.add_uninitialized_stack(RatioCombineContentTool)

ratio.add_uninitialized_stack(RatioMathTool)

ratio.add_uninitialized_stack(RatioRenderTemplateTool)

ratio.synth()