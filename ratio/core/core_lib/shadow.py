"""
Permissions model for managing access control in the system
"""
import logging

from dataclasses import dataclass, fields as dc_fields
from typing import Dict, List, Union


@dataclass
class Permissions:
    read: bool = False
    write: bool = False
    execute: bool = False

    def has_access(self, required_permissions: 'Permissions') -> bool:
        """
        Check if the current permissions allow the required permissions.

        Keyword arguments:
        required_permissions -- The permissions required to access the object.
        """
        # Need to validate it meets the minimum required permissions, not just exact match
        # only ensure the required permissions are met
        required_permission_names = [perm_name for perm_name, perm_value in required_permissions.__dict__.items() if perm_value]

        logging.debug(f"Required permissions: {required_permission_names}")

        supported_permission_names = [perm_name for perm_name, perm_value in self.__dict__.items() if perm_value]

        logging.debug(f"Supported permissions: {supported_permission_names}")

        # Use set intersection to check if all required permissions are met
        return set(required_permission_names).issubset(set(supported_permission_names))

    @classmethod
    def from_names(cls, permission_names: List[str]) -> 'Permissions':
        """
        Create a Permissions instance from a list of requested permission names.

        Keyword arguments:
        permission_names -- The list of permission names to create the Permissions instance from.
        """
        # Validate the input
        klass_field_names = [f.name for f in dc_fields(cls)]

        if not set(permission_names).issubset(set(klass_field_names)):
            raise ValueError(f"Invalid permission names: {permission_names}. Valid names are: {klass_field_names}")

        permissions_dict = {perm_name: True for perm_name in permission_names}

        return cls(**permissions_dict)


@dataclass
class PermissionsModel:
    everyone: Permissions
    owner: Permissions
    owner_name: str
    group: Permissions 
    group_name: str

    def has_access(self, requestor: str, requestor_member_groups: List[str], requested_permissions: Permissions) -> bool:
        """
        Check if the entity has access to the object represented by this model.

        Keyword arguments:
        requestor -- The entity requesting access.
        requestor_member_groups -- The groups the requestor is a member of.
        requested_permissions -- The permissions required to access the object.
        """
        # Validate based on permissions model first
        # Check if everyone has the required permissions
        if self.everyone.has_access(requested_permissions):
            return True

        # Check if in owning group
        if self.group_name in requestor_member_groups:
            # Check if owner has the required permissions
            if self.group.has_access(requested_permissions):
                return True

        # Check if owning entity
        if self.owner_name == requestor:
            # Check if owner entity has the required permissions
            if self.owner.has_access(requested_permissions):
                return True

        # If none of the above checks pass, access is denied
        return False

def as_permissions_model(owner: str, group: str, permissions_mask: int = 644) -> PermissionsModel:
    """
    Generate a permissions model based on the owner group name and permissions mask.
    
    Keyword arguments:
    owner -- The name of the owner entity.
    group -- The name of the owning group.
    permissions_mask -- The permissions mask (default 466).
                        Format:  owner(6) group(4) everyone(4)
    """
    # Parse the permissions mask into a structured format
    parsed_permissions = parse_permissions(permissions_mask)

    owner_permissions = Permissions(**parsed_permissions['owner'])

    group_permissions = Permissions(**parsed_permissions['group'])

    everyone_permissions = Permissions(**parsed_permissions['everyone'])

    # Create and return the PermissionsModel instance
    return PermissionsModel(
        everyone=everyone_permissions,
        owner=owner_permissions,
        group=group_permissions,
        group_name=group,
        owner_name=owner,
    )


def parse_permissions(permissions_mask: Union[int, str]) -> Dict[str, Dict[str, bool]]:
    """
    Parse Unix-style permission mask into a structured format.
    
    Args:
        permissions_mask (int): Unix-style permission mask (default 464)
                               Format: owner(4) group(6) everyone(4)
    
    Returns:
        dict: A dictionary with nested structure for easy permission checking
    """
    # Convert to octal string and ensure it's 3 digits
    if isinstance(permissions_mask, str):
        # Handle string input like '464'
        permissions_mask = int(permissions_mask, 8)

    # Create octal string and ensure it's 3 digits
    octal_str = oct(permissions_mask)[2:].zfill(3)

    # Parse each digit
    owner = int(octal_str[0])

    group = int(octal_str[1])

    everyone = int(octal_str[2])

    # Function to convert a single digit to permissions
    def digit_to_permissions(digit):
        return {
            "read": bool(digit & 4),
            "write": bool(digit & 2),
            "execute": bool(digit & 1)
        }

    # Create a structured permissions dictionary
    permissions = {
        "owner": digit_to_permissions(owner),
        "group": digit_to_permissions(group),
        "everyone": digit_to_permissions(everyone)
    }

    return permissions