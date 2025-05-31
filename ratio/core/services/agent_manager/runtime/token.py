"""
Simple execution token management utility.
Creates execution tokens and refreshes when needed.
"""
import logging

from datetime import datetime, UTC as utc_tz

from da_vinci.core.global_settings import setting_value

from ratio.core.core_lib.jwt import InternalJWTManager, JWTClaims, JWTVerificationException


def create_execution_token(original_token: str) -> str:
    """
    Create a new 15-minute execution token from an original token.

    Keyword arguments:
    original_token -- JWT token string to base the execution token on.

    Returns:
        New execution token with 15-minute expiry

    Raises:
        JWTVerificationException: If original token is invalid
    """
    # Validate original token and get claims
    claims = InternalJWTManager.verify_token(token=original_token)

    jwt_manager = InternalJWTManager(
        kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
        expiry_minutes=15,
    )

    # Create execution token with same claims plus execution marker
    execution_token, _ = jwt_manager.create_token(
        authorized_groups=claims.authorized_groups,
        entity=claims.entity,
        primary_group=claims.primary_group,
        custom_claims={
            **claims.custom_claims,
            "token_type": "execution",
            "created_from": "original_token",
            "execution_created_at": datetime.now(tz=utc_tz).isoformat(),
        },
        home=claims.home,
        is_admin=claims.is_admin,
    )

    logging.debug(f"Created execution token for {claims.entity}")

    return execution_token


def token_check_and_refresh(token: str) -> str:
    """
    Take a token, check if it needs refresh, refresh if needed, return valid token.

    Keyword arguments:
    token -- JWT token string to validate and potentially refresh.

    Returns:
        Valid JWT token (either original or refreshed)

    Raises:
        JWTVerificationException: If token is invalid and can't be refreshed
    """
    try:
        # Check if current token is valid
        claims = InternalJWTManager.verify_token(token=token)

        # Check if token expires soon (within 5 minutes)
        now = datetime.now(tz=utc_tz).timestamp()

        time_until_expiry = claims.expiration - now

        if time_until_expiry > 300:  # 5 minutes buffer
            # Token is fine, return as-is
            return token

        # Token needs refresh
        logging.debug(f"Refreshing token, {time_until_expiry/60:.1f} minutes remaining")

        return _refresh_token(claims)

    except JWTVerificationException:
        # Token expired, try to refresh if we can decode it
        try:
            _, payload_b64, _ = token.split('.')
            payload = InternalJWTManager.decode_segment(payload_b64)

            expired_claims = JWTClaims.from_claims(claims=payload)

            # Only refresh if expired recently (within 1 hour)
            now = datetime.now(tz=utc_tz).timestamp()

            if now - expired_claims.expiration > 3600:
                raise JWTVerificationException("Token expired too long ago")

            logging.debug("Refreshing recently expired token")

            return _refresh_token(expired_claims)

        except Exception as e:
            raise JWTVerificationException(f"Cannot refresh invalid token: {e}")


def _refresh_token(claims: JWTClaims) -> str:
    """
    Create new token with same claims but fresh expiration

    Keyword arguments:
    claims -- JWTClaims object containing the claims to refresh
    """
    jwt_manager = InternalJWTManager(
        kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
        expiry_minutes=15,
    )

    # Keep execution marker if it exists, otherwise add it
    custom_claims = claims.custom_claims.copy()

    if custom_claims.get("token_type") != "execution":
        custom_claims.update({
            "token_type": "execution",
            "created_from": "refresh",
        })

    custom_claims["refreshed_at"] = datetime.now(tz=utc_tz).isoformat()

    new_token, _ = jwt_manager.create_token(
        authorized_groups=claims.authorized_groups,
        entity=claims.entity,
        primary_group=claims.primary_group,
        custom_claims=custom_claims,
        home=claims.home,
        is_admin=claims.is_admin,
    )

    return new_token