import os
import hashlib
import logging

from datetime import datetime, UTC as utc_tz
from typing import Dict, List, Optional, Tuple, Union

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)

_PERMISSION_ENTITIES = ("owner", "group", "everyone")

_PERMISSION_MASK = ("read", "write", "execute")


class PermissionMaskHandler:
    """
    A class for handling permission calculations using binary bit values.
    
    This class provides utilities for working with permission masks where:
    - READ = 1 (binary 001)
    - WRITE = 2 (binary 010)
    - EXECUTE = 4 (binary 100)
    
    These permissions can be combined to create composite permissions:
    - READ + WRITE = 3 (binary 011)
    - READ + EXECUTE = 5 (binary 101)
    - WRITE + EXECUTE = 6 (binary 110)
    - READ + WRITE + EXECUTE = 7 (binary 111)
    """
    
    # Define permission constants
    READ = 1      # binary 001
    WRITE = 2     # binary 010
    EXECUTE = 4   # binary 100
    
    # Map permission names to values
    PERMISSION_MAP = {
        "read": READ,
        "write": WRITE,
        "execute": EXECUTE
    }

    @staticmethod
    def octal_digits_to_binary(number_str: str) -> str:
        result = ""

        for digit in number_str:
            # Convert each digit to int, then to octal binary pattern (3 bits)
            binary = format(int(digit), '03b')

            result += binary

        return result

    @classmethod
    def calculate_permissions_breakdown(cls, permission_mask: Union[int, str], entities=_PERMISSION_ENTITIES, permissions=_PERMISSION_MASK):
        """
        Get a breakdown of permissions for each entity based on a permission mask.

        Keyword arguments:
        permission_mask -- The permission mask to break down (e.g., 0644)
        entities -- List of entity names in the order they appear in the mask
        """
        octal_str = permission_mask

        if isinstance(permission_mask, int):
            perm_mask = str(permission_mask)

        else:
            perm_mask = permission_mask

        # Convert octal string
        octal_str = cls.octal_digits_to_binary(number_str=perm_mask)

        result = {entity: [] for entity in entities}

        for i, entity in enumerate(entities):
        # Each entity gets 3 bits
            start_bit = i * 3

            end_bit = start_bit + 3
            
            # Extract the 3 bits for this entity
            entity_bits = octal_str[start_bit:end_bit]

            # Map bits to permissions
            for j, permission in enumerate(permissions):
                # Check if the bit is set for this permission
                if j < len(entity_bits) and entity_bits[j] == '1':

                    result[entity].append(permission)

        return result

    @classmethod
    def calculate_entity_permission_values(cls, permission_mask: Union[int, str], entities: List[str]) -> Dict:
        """
        Break down a permission mask into individual permission values for each entity.
        
        Keyword arguments:
        permission_mask -- The complete permission mask (e.g., 0644)
        entities -- List of entity names in the order they appear in the mask
        
        Example:
            If permission_mask is in octal format like 0644, where:
            - The first digit (6) = owner permissions (4+2 = READ+WRITE)  
            - The second digit (4) = group permissions (4 = READ)
            - The third digit (4) = everyone permissions (4 = READ)
        """
        result = {}

        breakdown = cls.calculate_permissions_breakdown(permission_mask=permission_mask, entities=entities)

        for entity in breakdown:
            # Convert permission list to a single integer value
            perm_value = 0

            for permission in breakdown[entity]:

                perm_value += cls.PERMISSION_MAP.get(permission.lower(), 0)
                
            result[entity] = perm_value

        return result

    @classmethod
    def get_matching_permission_masks(cls, required_permissions: List[str]) -> List[int]:
        """
        Compute all possible permission mask values that satisfy the required permissions.
        
        Keyword arguments:
        required_permissions -- List of required permission names (e.g., ["read", "write"])
        
        Example:
            If required_permissions=["read"], the method will return [1, 3, 5, 7],
            representing all combinations where the "read" bit is set.
        """
        # Calculate the combined permission value
        combined_permission = 0

        for permission in required_permissions:
            perm_value = cls.PERMISSION_MAP.get(permission.lower(), 0)
            combined_permission |= perm_value
            
        # Find all possible permission combinations that satisfy the requirements
        result = []

        for i in range(1, 8):  # Check all possible permission values (1-7)
            # Check if all required permission bits are set in this value
            if (i & combined_permission) == combined_permission:
                result.append(i)
                
        return result

    @classmethod
    def explain_permission(cls, permission_value: int) -> str:
        """
        Explain what a specific permission value means in terms of read, write, execute access.
        
        Keyword arguments:
        permission_value -- The permission value to explain (1-7)
        """
        permissions = []
        
        if permission_value & cls.READ:
            permissions.append("READ")

        if permission_value & cls.WRITE:
            permissions.append("WRITE")

        if permission_value & cls.EXECUTE:
            permissions.append("EXECUTE")
            
        if not permissions:
            return "No permissions"
        
        return " + ".join(permissions)


class File(TableObject):
    table_name = "file"

    description = "The global file table stores information about the file available in the system."

    partition_key_attribute = TableObjectAttribute(
        name="path_hash",
        attribute_type=TableObjectAttributeType.STRING,
        description="The hash of the file path. This is sha256 hash of the FS path of the file.",
    )

    sort_key_attribute = TableObjectAttribute(
        name="name_hash",
        attribute_type=TableObjectAttributeType.STRING,
        description="The hash of the file name. This is sha256 hash of the file name.",
    )

    attributes = [
        TableObjectAttribute(
            name="added_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the data was added to the system.",
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="description",
            attribute_type=TableObjectAttributeType.STRING,
            description="The description of the file.",
            optional=True,
        ),

        TableObjectAttribute(
            name="file_name",
            attribute_type=TableObjectAttributeType.STRING,
            description="The name of the file, e.g. 'john_doe_resume'.",
        ),

        TableObjectAttribute(
            name="file_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The full path of the file in the system. This is not hashed.",
        ),

        TableObjectAttribute(
            name="file_type",
            attribute_type=TableObjectAttributeType.STRING,
            description="The type of the file. E.g. 'TEXT', 'IMAGE', etc.",
        ),

        TableObjectAttribute(
            name="last_accessed_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the file information was last accessed.",
            default=lambda: datetime.now(utc_tz),
            optional=True,
        ),

        TableObjectAttribute(
            name="last_read_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the file data was last read. Only applies when data is read from the file.",
            default=lambda: datetime.now(utc_tz),
            optional=True,
        ),

        TableObjectAttribute(
            name="last_updated_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the file was last updated.",
            default=lambda: datetime.now(utc_tz),
            optional=True,
        ),

        TableObjectAttribute(
            name="latest_version_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the latest version of the file.",
            optional=True,
        ),

        TableObjectAttribute(
            name="is_directory",
            attribute_type=TableObjectAttributeType.BOOLEAN,
            description="Whether the file is a directory or not.",
            optional=True,
            default=False,
        ),

        TableObjectAttribute(
            name="metadata",
            attribute_type=TableObjectAttributeType.JSON_STRING,
            description="The metadata associated with the file.",
            optional=True,
        ),

        TableObjectAttribute(
            name="owner",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the entity that owns the file.",
        ),

        TableObjectAttribute(
            name="group",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the group that owns the file.",
        ),

        TableObjectAttribute(
            name="permissions",
            attribute_type=TableObjectAttributeType.STRING,
            description="The permissions associated with the file. Represented as a bitmask. E.g. 0x1 for read, 0x2 for write, etc.",
            default="464",
            optional=True,
        ),

        TableObjectAttribute(
            name="permissions_mask_everyone",
            attribute_type=TableObjectAttributeType.NUMBER,
            description="The permissions mask for everyone. Represented as an integer.",
            default=0,
            optional=True,
        ),

        TableObjectAttribute(
            name="permissions_mask_owner",
            attribute_type=TableObjectAttributeType.NUMBER,
            description="The permissions mask for the owner. Represented as an integer.",
            default=0,
            optional=True,
        ),

        TableObjectAttribute(
            name="permissions_mask_group",
            attribute_type=TableObjectAttributeType.NUMBER,
            description="The permissions mask for the group. Represented as an integer.",
            default=0,
            optional=True,
        ),
    ]

    @property
    def full_path(self) -> str:
        """
        Get the full path of the file.

        Keyword arguments:
        file_name -- The name of the file to generate the hash for.
        """
        return os.path.join(self.file_path, self.file_name)

    @property
    def full_path_hash(self) -> str:
        """
        Get the full path hash of the file.

        Keyword arguments:
        file_name -- The name of the file to generate the hash for.
        """
        return self.generate_full_path_hash(
            name_hash=self.name_hash,
            path_hash=self.path_hash,
        )

    @staticmethod
    def generate_full_path_hash(name_hash: str, path_hash: str):
        """
        Generate full path hash helper method
        """
        joined_keys = "-".join([path_hash, name_hash])

        return hashlib.sha256(joined_keys.encode()).hexdigest()

    @staticmethod
    def generate_hash(name: str) -> str:
        """
        Generate the hash of a str.

        Keyword arguments:
        file_name -- The name of the file to generate the hash for.
        """

        return hashlib.sha256(name.encode()).hexdigest()

    def execute_on_update(self):
        """
        Executes the update on the file object.
        """
        entities = list(_PERMISSION_ENTITIES)

        calculated_permissions = PermissionMaskHandler.calculate_entity_permission_values(
            permission_mask=self.permissions,
            entities=entities,
        )

        for entity in entities:
            permissions_mask = calculated_permissions[entity]

            logging.debug(f"Setting permissions mask for {entity}: {permissions_mask}")

            setattr(self, f"permissions_mask_{entity}", permissions_mask)


class FilesTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        super().__init__(
            app_name=app_name,
            deployment_id=deployment_id,
            default_object_class=File,
        )

    def check_if_type_in_use(self, file_type: str = None) -> bool:
        """
        Check if a file type is in use.

        Keyword arguments:
        file_type -- The type of the file to check.
        """
        scan_definition = TableScanDefinition(table_object_class=self.default_object_class)

        scan_definition.add(
            attribute_name="file_type",
            comparison="equal",
            value=file_type,
        )

        results = self.full_scan(scan_definition=scan_definition)

        if results:
            return True

        return False

    def delete(self, file: File) -> None:
        """
        Delete a file object from the system.
        """
        return self.delete_object(file)

    def get(self, name_hash: str, path_hash: str, consistent_read: bool = False) -> Union[File, None]:
        """
        Get a file object from the system.

        Keyword arguments:
        name_hash -- The hash of the file name.
        path_hash -- The hash of the file path.
        consistent_read -- Whether to use a consistent read.
        """
        return self.get_object(partition_key_value=path_hash, sort_key_value=name_hash, consistent_read=consistent_read)

    def get_sub_directories(self, path_hash: str) -> Union[List[File], None]:
        """
        Get all subdirectories of a directory.

        Keyword arguments:
        path_hash -- The hash of the file path.
        """
        scan_definition = TableScanDefinition(table_object_class=self.default_object_class)

        scan_definition.add(
            attribute_name="path_hash",
            comparison="equal",
            value=path_hash,
        )

        scan_definition.add(
            attribute_name="is_directory",
            comparison="equal",
            value=True,
        )

        results = self.full_scan(scan_definition=scan_definition)

        if results:
            return results

        return None

    def list(self, path_hash: str, last_evaluated_key: Optional[Dict] = None) -> Tuple[List[File], Optional[str]]:
        """
        List all file objects in the system.

        Keyword arguments:
        path_hash -- The hash of the file path.
        requesting_entity_id -- The id of the entity requesting the list.
        requesting_group_id -- The id of the group requesting the list.
        requestor_is_admin -- Whether the requestor is an admin.
        last_evaluated_key -- The last evaluated key for pagination.
        required_permissions -- The permissions required to access the file.
        """
        logging.debug(f"Listing files with path hash: {path_hash}")

        parameters = {
            "FilterExpression": "PathHash = :path_hash",
            "ExpressionAttributeValues": {
                ":path_hash": {"S": path_hash},
            }
        }

        results = []

        final_last_evaluated_key = None

        for page in self.paginated(call='scan', last_evaluated_key=last_evaluated_key, parameters=parameters):
            results.extend(page.items)

            final_last_evaluated_key = page.last_evaluated_key

        return results, final_last_evaluated_key

    def put(self, file: File) -> None:
        """
        Put a file object into the system.

        Keyword arguments:
        file -- The file object to put into the system.
        """
        return self.put_object(file)

    def set_last_accessed(self, name_hash: str, path_hash: str, last_accessed_on: datetime,
                          last_read_on: Optional[datetime] = None, last_updated_on: Optional[datetime] = None) -> None:
        """
        Set the last accessed and last read date and time for the file.

        Keyword arguments:
        name_hash -- The hash of the file name.
        path_hash -- The hash of the file path.
        last_accessed_on -- The date and time the file was last accessed.
        last_read_on -- The date and time the file was last read.
        last_updated_on -- The date and time the file was last updated.
        """
        updates = {"last_accessed_on": last_accessed_on}

        if last_read_on:
            updates["last_read_on"] = last_read_on

        if last_updated_on:
            updates["last_updated_on"] = last_updated_on

        self.update_object(partition_key_value=path_hash, sort_key_value=name_hash, updates=updates)