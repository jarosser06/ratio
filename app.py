import os

from da_vinci_cdk.application import Application, ResourceDiscoveryStorageSolution
from da_vinci_cdk.stack import Stack

from ratio.core.api.stack import RatioAPIStack

from ratio.tools.bedrock.stack import RatioBedrockTools
from ratio.tools.combine_content.stack import RatioCombineContentTool
from ratio.tools.internal_api.stack import RatioInternalAPITool
from ratio.tools.math.stack import RatioMathTool
from ratio.tools.render_template.stack import RatioRenderTemplateTool

base_dir = Stack.absolute_dir(__file__)

ratio = Application(
    app_entry=base_dir,
    app_name='ratio',
    create_hosted_zone=False,
    deployment_id=os.getenv('RATIO_DEPLOYMENT_ID', 'dev'),
    disable_docker_image_cache=True,
    enable_exception_trap=True,
    enable_event_bus=True,
    log_level=os.getenv('RATIO_LOG_LEVEL', 'DEBUG'),
    resource_discovery_storage_solution=ResourceDiscoveryStorageSolution.DYNAMODB,
)

ratio.add_uninitialized_stack(RatioAPIStack)

ratio.add_uninitialized_stack(RatioInternalAPITool)

ratio.add_uninitialized_stack(RatioBedrockTools)

ratio.add_uninitialized_stack(RatioCombineContentTool)

ratio.add_uninitialized_stack(RatioMathTool)

ratio.add_uninitialized_stack(RatioRenderTemplateTool)

ratio.synth()