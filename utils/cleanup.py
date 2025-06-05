import boto3

from botocore.exceptions import ClientError

from da_vinci.event_bus.tables.event_bus_responses import EventBusResponses
from da_vinci.core.tables.global_settings import GlobalSettings

# Import API Tables
from ratio.core.tables.entities.client import EntitiesTableClient
from ratio.core.tables.groups.client import GroupsTableClient

# Import Storage Manager Tables
from ratio.core.services.storage_manager.tables.files.client import FilesTableClient
from ratio.core.services.storage_manager.tables.file_lineage.client import FileLineageTableClient
from ratio.core.services.storage_manager.tables.file_versions.client import FileVersionsTableClient
from ratio.core.services.storage_manager.tables.file_types.client import FileTypeTableClient
from ratio.core.services.process_manager.tables.processes.client import ProcessTableClient


def delete_all_objects_in_versioned_bucket(bucket_name: str):
    """
    Deletes all objects, versions, and delete markers in a versioned S3 bucket.
    
    Keyword arguments:
    bucket_name -- the name of the S3 bucket to be wiped
    """
    try:
        # Create S3 client
        s3_client = boto3.client('s3')

        # Check if versioning is enabled
        try:
            versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)

            versioning_status = versioning.get('Status', 'Disabled')

            print(f"Bucket versioning status: {versioning_status}")

        except ClientError as e:
            print(f"Error checking versioning status: {e}")

            return False

        # Initialize pagination
        paginator = s3_client.get_paginator('list_object_versions')

        page_iterator = paginator.paginate(Bucket=bucket_name)

        # Iterate through all pages of object versions
        for page in page_iterator:
            # Prepare lists for batch deletion
            objects_to_delete = []

            # Process versions
            if 'Versions' in page:
                for version in page['Versions']:
                    objects_to_delete.append({
                        'Key': version['Key'],
                        'VersionId': version['VersionId']
                    })

            # Process delete markers
            if 'DeleteMarkers' in page:
                for delete_marker in page['DeleteMarkers']:
                    objects_to_delete.append({
                        'Key': delete_marker['Key'],
                        'VersionId': delete_marker['VersionId']
                    })

            # Delete objects in batches (up to 1000 per request)
            if objects_to_delete:
                # Split into batches of 1000 (S3 API limit)
                batch_size = 1000

                for i in range(0, len(objects_to_delete), batch_size):
                    batch = objects_to_delete[i:i + batch_size]

                    try:
                        response = s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={
                                'Objects': batch,
                                'Quiet': True  # Set to False for detailed response
                            }
                        )

                        # Check for errors in batch deletion
                        if 'Errors' in response:
                            for error in response['Errors']:
                                print(f"Error deleting {error['Key']} (version {error.get('VersionId', 'null')}): {error['Message']}")

                        else:
                            print(f"Successfully deleted batch of {len(batch)} objects")

                    except ClientError as e:
                        print(f"Error in batch deletion: {e}")
                        return False

        print(f"Successfully deleted all objects in bucket: {bucket_name}")

        return True

    except ClientError as e:
        print(f"AWS Client Error: {e}")

        return False

    except Exception as e:
        print(f"Unexpected error: {e}")

        return False

# Example usage
if __name__ == "__main__":
    settings_client = GlobalSettings()

    # Clear Raw Bucket
    raw_bucket_name = settings_client.get(
        namespace="ratio::storage",
        setting_key="raw_bucket",
    )

    success = delete_all_objects_in_versioned_bucket(bucket_name=raw_bucket_name.setting_value)
    
    if success:
        print("Bucket wiped successfully!")

    else:
        print("Failed to wipe bucket. Check the error messages above.")

    # Reset the initialization flag
    init_setting = settings_client.get(namespace="ratio::core", setting_key="installation_initialized")

    if not init_setting:
        raise ValueError("Installation initialization setting not found.")

    # Set the installation initialization setting to False
    init_setting.setting_value = "False"

    settings_client.put(setting=init_setting)

    # Dlete all file lineage
    print("Clearing file lineage table...")

    file_lineage_client = FileLineageTableClient()

    all_file_lineage = file_lineage_client._all_objects()

    for file_lineage in all_file_lineage:

        file_lineage_client.delete(file_lineage)

    # Delete all file versions
    print("Clearing file versions table...")

    file_versions_client = FileVersionsTableClient()

    all_file_versions = file_versions_client._all_objects()
    for file_version in all_file_versions:

        file_versions_client.delete(file_version)

    # Delete all files
    print("Clearing files table...")

    files_client = FilesTableClient()

    all_files = files_client._all_objects()

    SKIP_FILES = ["/", "/home"]

    for file in all_files:
        if file.full_path in SKIP_FILES:
            print(f"Skipping file deletion: {file.full_path}")

            continue

        files_client.delete(file)

    # Delete all file types
    print("Clearing file types table...")

    file_types_client = FileTypeTableClient()

    all_file_types = file_types_client._all_objects()

    SKIP_FILE_TYPES = ["ratio::file", "ratio::directory", "ratio::root", "ratio::tool", "ratio::tool_io"]

    for file_type in all_file_types:
        if file_type.type_name in SKIP_FILE_TYPES:
            print(f"Skipping file type deletion: {file_type.type_name}")

            continue

        file_types_client.delete(file_type)

    # Delete all entities
    print("Clearing entities table...")

    entities_client = EntitiesTableClient()

    all_entities = entities_client._all_objects()

    for entity in all_entities:
        entities_client.delete(entity)

    # Delete all groups
    print("Clearing groups table...")

    groups_client = GroupsTableClient()

    all_groups = groups_client._all_objects()

    for group in all_groups:
        groups_client.delete(group)

    # Clear all event bus responses
    print("Clearing event bus responses table...")

    event_bus_responses_client = EventBusResponses()

    all_event_bus_responses = event_bus_responses_client._all_objects()

    for event_bus_response in all_event_bus_responses:
        event_bus_responses_client.delete(event_bus_response)

    print("All event bus responses cleared.")

    # Clear all processes
    print("Clearing processes table...")

    processes_client = ProcessTableClient()
    all_processes = processes_client._all_objects()
    for process in all_processes:
        processes_client.delete(process)
    print("All processes cleared.")