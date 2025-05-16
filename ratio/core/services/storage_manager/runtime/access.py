"""
Access control for file operations in the storage manager.
"""

import logging

from enum import StrEnum
from typing import Dict, List

from ratio.core.core_lib.jwt import JWTClaims
from ratio.core.core_lib.shadow import as_permissions_model, Permissions

from ratio.core.services.storage_manager.tables.files.client import File


class FilePermission(StrEnum):
    """
    Enum for file permissions.
    """
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


def entity_has_access(file: File, request_context: Dict, requested_permission_names: List[str] = [FilePermission.READ],
                      requires_owner: bool = False) -> bool:
    """
    Validates if the entity has access to the object.

    Keyword arguments:
    file -- The file object to check access for.
    request_context -- The context of the request, including claims and other metadata.
    requested_permission_names -- The list of requested permission names.
    requires_owner -- If True, the requestor must be either admin or the owner of the file to access it. Permissions are not checked.
    """
    logging.debug(f"Validating access for file: {file.full_path} with request: {request_context}")

    if "request_claims" not in request_context:
        logging.error("Request context does not contain 'request_claims'. Access denied.")

        return False

    claims = JWTClaims.from_claims(claims=request_context["request_claims"])

    is_admin = claims.is_admin

    if is_admin:
        logging.debug(f"Requestor is admin, granting access to file: {file.full_path}")

        return True

    if requires_owner:
        logging.debug(f"Requires owner access, checking if requestor is owner of file: {file.full_path}")

        return claims.entity == file.owner

    logging.debug(f"Requestor is not admin, checking permissions for file: {file.full_path} with permissions: {file.permissions}")

    perm_mdl = as_permissions_model(
        owner=file.owner,
        group=file.group,
        permissions_mask=file.permissions
    )

    logging.debug(f"Translated file permissions model: {perm_mdl}")

    req_permissions = Permissions.from_names(requested_permission_names)

    logging.debug(f"Requested permissions: {req_permissions}")

    req_entity = claims.entity

    req_groups = claims.authorized_groups

    logging.debug(f"Requestor entity: {req_entity}, groups: {req_groups}")

    # Validate the requestor has access to the file
    return perm_mdl.has_access(requestor=req_entity, requestor_member_groups=req_groups, requested_permissions=req_permissions)