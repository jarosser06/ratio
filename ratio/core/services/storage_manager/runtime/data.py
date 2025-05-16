"""
S3 Data management helpers for the storage manager.
"""
from typing import Union

import boto3


FILE_EXTENSION = ".data"


def stored_name(file_name: str, file_extension: str = FILE_EXTENSION) -> str:
    """
    Create a stored name for the file.

    Keyword arguments:
    file_name -- The name of the file.
    file_extension -- The extension of the file.
    """
    return f"{file_name}{file_extension}"


def copy_version(bucket_name: str, dest_file: str, source_file: str, version_id: str) -> str:
    """
    Copy a specific version of an S3 object to another location within the same bucket.
    
    Keyword arguments:
    bucket_name -- The name of the S3 bucket.
    dest_file -- The name of the destination file in S3.
    source_file -- The name of the source file in S3.
    version_id -- The specific version ID to copy.
    """
    s3 = boto3.client("s3")
    
    # Copy the specific version to the destination within the same bucket
    response = s3.copy_object(
        Bucket=bucket_name,
        CopySource={
            'Bucket': bucket_name,
            'Key': stored_name(source_file),
            'VersionId': version_id
        },
        Key=stored_name(dest_file),
    )
    
    version_id = response.get('VersionId')

    if not version_id:
        raise ValueError("Version ID not returned from S3. Check if versioning is enabled on the bucket.")
    
    return version_id


def delete_version(bucket_name: str, file_name: str, version_id: str) -> None:
    """
    Delete data from the system.
    
    Keyword arguments:
    bucket_name -- The name of the S3 bucket.
    stored_name -- The name of the file in S3.
    """
    # Delete the data from S3
    s3 = boto3.client("s3")

    s3.delete_object(
        Bucket=bucket_name,
        Key=stored_name(file_name),
        VersionId=version_id,
    )


def delete_object_completely(bucket_name: str, file_name: str):
    """
    Delete an object and all its versions from an S3 bucket.

    Keyword arguments:
    bucket_name -- The name of the S3 bucket.
    file_name -- The name of the file in S3.
    """

    key = stored_name(file_name)

    s3_client = boto3.client('s3')

    object_response_paginator = s3_client.get_paginator('list_object_versions')

    delete_marker_list = []

    version_list = []

    # Use pagination to handle potentially large numbers of versions
    for object_response_itr in object_response_paginator.paginate(Bucket=bucket_name, Prefix=key):
        if 'DeleteMarkers' in object_response_itr:

            for delete_marker in object_response_itr['DeleteMarkers']:

                if delete_marker['Key'] == key:  # Only include exact key matches
                    delete_marker_list.append({
                        'Key': delete_marker['Key'], 
                        'VersionId': delete_marker['VersionId']
                    })

        if 'Versions' in object_response_itr:
            for version in object_response_itr['Versions']:
                if version['Key'] == key:  # Only include exact key matches
                    version_list.append({
                        'Key': version['Key'], 
                        'VersionId': version['VersionId']
                    })

    # Delete in batches of 1000 (S3 API limit)
    for i in range(0, len(delete_marker_list), 1000):
        s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={
                'Objects': delete_marker_list[i:i+1000],
                'Quiet': True
            }
        )

    for i in range(0, len(version_list), 1000):
        s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={
                'Objects': version_list[i:i+1000],
                'Quiet': True
            }
        )


def get_version(bucket_name: str, file_name: str, version_id: str) -> bytes:
    """
    Get data from the system.
    
    Keyword arguments:
    bucket_name -- The name of the S3 bucket.
    stored_name -- The name of the file in S3.
    """
    # Get the data from S3
    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=bucket_name,
        Key=stored_name(file_name),
        VersionId=version_id,
    )

    return response["Body"].read()


def put_version(data: Union[str, bytes], bucket_name: str, file_name: str) -> str:
    """
    Put data in the system and return the version ID.
    
    Parameters:
    data (Union[str, bytes]): The data to put
    bucket_name (str): The name of the S3 bucket
    stored_name (str): The key name to use in S3
    
    Returns:
    str: The version ID assigned by S3
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    
    # Store the data in S3
    s3 = boto3.client("s3")
    response = s3.put_object(
        Bucket=bucket_name,
        Key=stored_name(file_name=file_name),
        Body=data,
    )
    
    # Extract and return the version ID
    version_id = response.get('VersionId')

    if not version_id:
        raise ValueError("Version ID not returned from S3. Check if versioning is enabled on the bucket.")

    return version_id