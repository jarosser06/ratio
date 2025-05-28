import os

from da_vinci_cdk.application import Application, ResourceDiscoveryStorageSolution
from da_vinci_cdk.stack import Stack

from ratio.core.api.stack import RatioAPIStack

from ratio.agents.bedrock.stack import RatioBedrockAgents
from ratio.agents.combine_content.stack import RatioCombineContentAgent
from ratio.agents.internal_api.stack import RatioAgentInternalAPI
from ratio.agents.math.stack import RatioMathAgent
from ratio.agents.object_mapper.stack import RatioObjectMapperAgent
from ratio.agents.render_template.stack import RatioRenderTemplateAgent
from ratio.agents.string_concatenation.stack import RatioStringConcatenationAgent

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

ratio.add_uninitialized_stack(RatioAgentInternalAPI)

ratio.add_uninitialized_stack(RatioBedrockAgents)

ratio.add_uninitialized_stack(RatioCombineContentAgent)

ratio.add_uninitialized_stack(RatioMathAgent)

ratio.add_uninitialized_stack(RatioObjectMapperAgent)

ratio.add_uninitialized_stack(RatioRenderTemplateAgent)

ratio.add_uninitialized_stack(RatioStringConcatenationAgent)

ratio.synth()