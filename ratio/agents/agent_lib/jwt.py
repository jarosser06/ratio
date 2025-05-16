"""
JWT Client Library for verifying tokens and accessing claims.

This is a streamlined version that handles token verification and claims extraction.
"""
import json
import base64

from dataclasses import dataclass
from datetime import datetime, UTC as utc_tz
from typing import Dict, List, Optional

import boto3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key


@dataclass
class JWTClaims:
    """
    Data class to hold JWT claims
    """
    authorized_groups: List[str]
    expiration: int
    is_admin: bool
    issuer: str
    issued_at: int
    primary_group: str
    subject: str
    custom_claims: Optional[Dict] = None
    home: Optional[str] = None

    @property
    def entity(self) -> str:
        """
        Get the entity from the claims
        """
        return self.subject

    @classmethod
    def from_claims(cls, claims: Dict) -> "JWTClaims":
        """
        Populate the claims from a dictionary

        Keyword arguments:
        claims -- The claims dictionary to populate from
        """
        return cls(
            authorized_groups=claims['auth_grps'],
            custom_claims=claims.get('cus', {}),
            subject=claims['sub'],
            expiration=claims['exp'],
            issuer=claims['iss'],
            issued_at=claims['iat'],
            is_admin=claims['admin'],
            home=claims.get('home', ''),
            primary_group=claims['p_grp'],
        )

    def to_dict(self) -> Dict:
        """
        Convert the claims to a dictionary
        """
        return {
            "admin": self.is_admin,
            "auth_grps": self.authorized_groups,
            "cus": self.custom_claims,
            "sub": self.subject,
            "exp": self.expiration,
            "iss": self.issuer,
            "iat": self.issued_at,
            "home": self.home,
            "p_grp": self.primary_group,
        }


class JWTVerificationException(Exception):
    """Custom exception for JWT verification errors."""
    def __init__(self, message: str):
        super().__init__(f"JWT Verification Failed: {message}")


class JWTClient:
    """
    Client library for verifying JWTs and accessing claims.
    """
    signing_algorithm = 'RSASSA_PKCS1_V1_5_SHA_256'

    @staticmethod
    def encode_segment(segment: Dict) -> str:
        """
        Base64 encode a JWT segment

        Keyword arguments:
        segment -- The segment to encode (header or payload)
        """
        json_segment = json.dumps(segment)
        encoded = base64.urlsafe_b64encode(json_segment.encode('utf-8'))
        return encoded.decode('utf-8').rstrip('=')

    @staticmethod
    def encode_bytes(data: bytes) -> str:
        """
        Base64 encode raw bytes (for signature)
        
        Keyword arguments:
        data -- The bytes to encode
        """
        encoded = base64.urlsafe_b64encode(data)
        return encoded.decode('utf-8').rstrip('=')

    @staticmethod
    def decode_segment(segment: str) -> Dict:
        """
        Base64 decode a JWT segment

        Keyword arguments:
        segment -- The segment to decode (header or payload)
        """
        # Add padding if needed
        padding = '=' * (4 - (len(segment) % 4)) if len(segment) % 4 else ''
        padded_segment = segment + padding
        json_segment = base64.urlsafe_b64decode(padded_segment).decode('utf-8')
        return json.loads(json_segment)

    @staticmethod
    def decode_signature(signature: str) -> bytes:
        """
        Base64 decode a signature segment to bytes
        
        Keyword arguments:
        signature -- The signature segment to decode
        """
        # Add padding if needed
        padding = '=' * (4 - (len(signature) % 4)) if len(signature) % 4 else ''
        padded_signature = signature + padding
        return base64.urlsafe_b64decode(padded_signature)

    @classmethod
    def extract_kms_id(cls, token: str) -> str:
        """
        Extract the KMS ID from a JWT token
        
        Keyword arguments:
        token -- The JWT token
        
        Returns:
            KMS ID from the token header
            
        Raises:
            JWTVerificationException if the token format is invalid or missing KMS ID
        """
        try:
            header_b64, _, _ = token.split('.')
        except ValueError:
            raise JWTVerificationException("invalid JWT format")
        
        # Decode the header to get the key ID
        header = cls.decode_segment(header_b64)
        kms_key_id = header.get('kid')
        
        if not kms_key_id:
            raise JWTVerificationException("missing key ID in JWT header")
            
        return kms_key_id

    @classmethod
    def verify_token(cls, token: str) -> JWTClaims:
        """
        Verify a JWT token and return its claims
        
        Keyword arguments:
        token -- The JWT token to verify
            
        Returns:
            JWTClaims object containing the payload claims
            
        Raises:
            JWTVerificationException if verification fails
        """
        # Get the KMS ID from the token
        kms_key_id = cls.extract_kms_id(token)
        
        # Create a KMS client
        kms_client = boto3.client('kms')
        
        # Split the token
        try:
            header_b64, payload_b64, signature = token.split('.')
        except ValueError:
            raise JWTVerificationException("invalid JWT format")

        unsigned_token = f"{header_b64}.{payload_b64}"
        
        # Verify the signature with KMS
        try:
            decoded_signature = cls.decode_signature(signature)
            
            response = kms_client.verify(
                KeyId=kms_key_id,
                Message=unsigned_token.encode('utf-8'),
                MessageType='RAW',
                Signature=decoded_signature,
                SigningAlgorithm=cls.signing_algorithm,
            )
            
            if not response.get('SignatureValid', False):
                raise JWTVerificationException("invalid signature")
        except Exception as e:
            raise JWTVerificationException(f"KMS verification error: {str(e)}")
        
        # Decode the payload
        payload = cls.decode_segment(payload_b64)
        
        # Check for expiration
        now = datetime.now(tz=utc_tz).timestamp()
        payload_expiration = payload.get('exp', 0)
        
        if now >= payload_expiration:
            raise JWTVerificationException("token has expired")
        
        # Return claims object
        return JWTClaims.from_claims(claims=payload)

    @classmethod
    def verify_with_public_key(cls, token: str, public_key: str) -> JWTClaims:
        """
        Verify a JWT token using an RSA public key
        
        Keyword arguments:
        token -- The JWT token to verify
        public_key -- The RSA public key in PEM format
            
        Returns:
            JWTClaims object containing the payload claims
            
        Raises:
            JWTVerificationException if verification fails
        """
        # Split the token
        try:
            header_b64, payload_b64, signature = token.split('.')
        except ValueError:
            raise JWTVerificationException("invalid JWT format")

        unsigned_token = f"{header_b64}.{payload_b64}"
        
        # Verify with public key
        try:
            # Decode the signature
            decoded_signature = cls.decode_signature(signature)
            
            # Load the public key
            key = load_pem_public_key(public_key.encode('utf-8'))
            
            # Verify the signature
            try:
                key.verify(
                    decoded_signature,
                    unsigned_token.encode('utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            except InvalidSignature:
                raise JWTVerificationException("invalid signature")
                
        except Exception as e:
            raise JWTVerificationException(f"public key verification error: {str(e)}")
        
        # Decode the payload
        payload = cls.decode_segment(payload_b64)
        
        # Check for expiration
        now = datetime.now(tz=utc_tz).timestamp()
        payload_expiration = payload.get('exp', 0)
        
        if now >= payload_expiration:
            raise JWTVerificationException("token has expired")
        
        # Return claims object
        return JWTClaims.from_claims(claims=payload)