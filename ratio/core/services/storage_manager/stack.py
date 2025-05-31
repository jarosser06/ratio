from os import path

from aws_cdk import (
    Duration,
    RemovalPolicy,
)

from constructs import Construct

from aws_cdk.aws_s3 import Bucket, BucketEncryption

from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.global_setting import GlobalSetting
from da_vinci_cdk.constructs.service import SimpleRESTService

from da_vinci_cdk.framework_stacks.services.event_bus.stack import EventBusStack

from ratio.core.stack import RatioCoreStack

from ratio.core.services.storage_manager.tables.files.stack import File, FilesTableStack
from ratio.core.services.storage_manager.tables.file_lineage.stack import (
    FileLineageEntry,
    FileLineageTableStack,
)
from ratio.core.services.storage_manager.tables.file_versions.stack import (
    FileVersion,
    FileVersionsTableStack,
)
from ratio.core.services.storage_manager.tables.file_types.stack import FileType, FileTypesTableStack

from ratio.core.services.storage_manager.cdk.filesystem import RegisteredFile, RegisteredFileType


class StorageManagerStack(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str,
                 deployment_id: str, stack_name: str, scope: Construct):
        """
        Storage Manager Stack

        Keyword Arguments:
            app_name: The name of the app.
            app_base_image: The base image for the app.
            architecture: The architecture of the app.
            deployment_id: The deployment ID.
            stack_name: The name of the stack.
            scope: The scope of the stack.
        """

        super().__init__(
            app_name=app_name,
            app_base_image=app_base_image,
            architecture=architecture,
            requires_exceptions_trap=True,
            required_stacks=[
                EventBusStack,
                FileLineageTableStack,
                FilesTableStack,
                FileTypesTableStack,
                FileVersionsTableStack,
                RatioCoreStack,
            ],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        self.runtime_path = path.join(base_dir, 'runtime')

        self.raw_bucket = Bucket(
            self,
            "raw_bucket",
            encryption=BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
        )

        self.raw_bucket_setting = GlobalSetting(
            namespace="ratio::storage",
            setting_key="raw_bucket",
            setting_value=self.raw_bucket.bucket_name,
            scope=self,
        )

        self.storage_manager = SimpleRESTService(
            base_image=self.app_base_image,
            description="Manages the underlying data storage",
            entry=self.runtime_path,
            index="api.py",
            handler="handler",
            memory_size=512,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="event_bus",
                    resource_type=ResourceType.ASYNC_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name=File.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name=FileLineageEntry.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name=FileVersion.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name=FileType.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="internal_signing_kms_key_id",
                    resource_type="KMS_KEY",
                    policy_name="default",
                ),
            ],
            scope=self,
            service_name="storage_manager",
            timeout=Duration.seconds(90),
        )

        self.raw_bucket.grant_read_write(self.storage_manager.handler.function)

        RegisteredFileType(
            scope=self,
            type_name="ratio::root",
            description="Root FS Directory",
            is_directory_type=True,
        )

        RegisteredFile(
            scope=self,
            file_name="/",
            file_path="/",
            file_type="ratio::root",
            owner="system",
            group="system",
            is_directory=True,
            description="Root FS Directory",
            permissions="755",
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::directory",
            description="FS Directory",
            is_directory_type=True,
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::file",
            description="FS Basic File",
            is_directory_type=False,
            content_type="application/octet-stream"
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::text",
            description="FS Text File",
            is_directory_type=False,
            content_type="text/plain"
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::gif",
            description="FS GIF Image File",
            is_directory_type=False,
            content_type="image/gif"
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::jpeg",
            description="FS JPEG Image File",
            is_directory_type=False,
            content_type="image/jpeg"
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::markdown",
            description="Markdown File",
            is_directory_type=False,
            content_type="text/markdown"
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::png",
            description="FS PNG Image File",
            is_directory_type=False,
            content_type="image/png"
        )

        RegisteredFileType(
            scope=self,
            type_name="ratio::webp",
            description="FS WEBP Image File",
            is_directory_type=False,
            content_type="image/webp"
        )

        RegisteredFile(
            scope=self,
            file_path="/home",
            file_type="ratio::directory",
            owner="system",
            group="system",
            is_directory=True,
            description="Entity Default Home Directory",
            permissions="755",
        )