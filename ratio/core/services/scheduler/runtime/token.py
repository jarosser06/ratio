import logging

from da_vinci.core.global_settings import setting_value

from ratio.core.core_lib.jwt import InternalJWTManager

from ratio.core.tables.entities.client import (
    EntitiesTableClient,
)


def generate_token(entity_id: str):
    """
    Create a token for the entity.

    Keyword Arguments:
    entity_id -- The ID of the entity for which the token is being created.
    """
    entity_client = EntitiesTableClient()

    # Get the entity
    entity = entity_client.get(entity_id=entity_id)

    if not entity:
        raise Exception(f"Entity with ID {entity_id} not found")

    jwt_manager = InternalJWTManager(
        # Don't need a very long expiry for scheduler tokens, execution will create its own tokens
        expiry_minutes=5,
        kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
    )

    admin_entity_id = setting_value(namespace="ratio::core", setting_key="admin_entity_id")

    admin_group_id = setting_value(namespace="ratio::core", setting_key="admin_group_id")

    if entity_id == admin_entity_id or admin_group_id in entity.groups:
        logging.debug(f"Entity is admin or part of the admin group: {entity_id}")

        is_admin = True

    else:
        logging.debug(f"Entity is not admin or part of the admin group: {entity_id}")

        is_admin = False

    token, _ = jwt_manager.create_token(
        authorized_groups=entity.groups,
        entity=entity.entity_id,
        custom_claims={
            "auth_method": "scheduler",
        },
        home=entity.home_directory,
        primary_group=entity.primary_group_id,
        is_admin=is_admin,
    )

    return token