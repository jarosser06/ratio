"""
Internal JWT Manager used by Ratio components to verify internally signed JWTs provided by the task manager.
"""
import json
import base64

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC as utc_tz
from typing import Dict, List, Optional, Tuple

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
    """Custom exception for JWT Manager errors."""
    def __init__(self, message: str):
        super().__init__(f"JWT Verification Failed: {message}")


class InternalJWTManager:
    signing_algorithm = 'RSASSA_PKCS1_V1_5_SHA_256'

    def __init__(self, kms_key_id: str, issuer: str = "ratio", expiry_minutes: int = 30):
        """
        Initialize the JWT Manager with KMS key information

        Keyword arguments:
        kms_key_id -- The KMS key ID used for signing JWTs
        issuer -- The issuer of the JWT (default: "Ratio")
        expiry_minutes -- The expiration time for the JWT in minutes (default: 30)
        """
        self.kms_key_id = kms_key_id

        self.issuer = issuer

        self.expiry_minutes = expiry_minutes

        self.kms_client = boto3.client('kms')
    
    def _create_header(self) -> Dict:
        """
        Create the JWT header with KMS information
        """
        return {
            "alg": "KMS-RSA-SHA256",
            "typ": "JWT",
            "kid": self.kms_key_id
        }

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

    def create_token(self, authorized_groups: List[str], entity: str, primary_group: str, custom_claims: Optional[Dict] = None,
                     home: Optional[str] = None, is_admin: bool = False) -> Tuple[str, datetime]:
        """
        Create a JWT with the given claims

        Keyword arguments:
        authorized_groups -- List of authorized groups for the entity
        entity -- The entity for which the JWT is created
        home -- The home directory for the entity (optional)
        primary_group -- The primary group for the entity
        custom_claims -- Any additional claims to include in the JWT (optional)
        
        Returns:
            Signed JWT string
        """
        # Create payload with standard claims
        now = datetime.now(tz=utc_tz)

        expires_at = now + timedelta(minutes=self.expiry_minutes)

        payload = JWTClaims(
            authorized_groups=authorized_groups,
            custom_claims=custom_claims,
            subject=entity,
            expiration=int(expires_at.timestamp()),
            home=home,
            is_admin=is_admin,
            issuer=self.issuer,
            issued_at=int(now.timestamp()),
            primary_group=primary_group,
        ).to_dict()

        # Create JWT segments
        header = self._create_header()

        header_encoded = self.encode_segment(header)

        payload_encoded = self.encode_segment(payload)

        unsigned_token = f"{header_encoded}.{payload_encoded}"

        # Sign with KMS
        signature = self.sign_with_kms(unsigned_token)

        # Return the complete JWT
        return f"{unsigned_token}.{signature}", expires_at

    def sign_with_kms(self, data: str) -> str:
        """
        Sign data using AWS KMS
        
        Keyword arguments:
        data -- The data to sign (header + payload)
        """
        response = self.kms_client.sign(
            KeyId=self.kms_key_id,
            Message=data.encode('utf-8'),
            MessageType='RAW',
            SigningAlgorithm=self.signing_algorithm
        )
        
        # Extract and encode the signature
        signature = response['Signature']

        return self.encode_bytes(signature)

    def verify_with_kms(self, data: str, signature: str) -> bool:
        """
        Verify the signature of the data using AWS KMS
        
        Keyword arguments:
        data -- The data to verify
        signature -- The signature to verify against
        """
        # Decode the signature from base64
        decoded_signature = self.decode_signature(signature)
        
        # Verify with KMS
        try:
            response = self.kms_client.verify(
                KeyId=self.kms_key_id,
                Message=data.encode('utf-8'),
                MessageType='RAW',
                Signature=decoded_signature,
                SigningAlgorithm=self.signing_algorithm,
            )

            return response.get('SignatureValid', False)

        except Exception as e:
            raise JWTVerificationException(f"KMS verification error: {str(e)}")

    def _verify_token(self, token: str) -> JWTClaims:
        """
        Verify a JWT token and return its claims if valid

        Keyword arguments:
        token -- The JWT token to verify
            
        Returns:
            The decoded payload if verification succeeds
            
        Raises:
            Exception if verification fails
        """
        # Split the token
        try:
            header_b64, payload_b64, signature = token.split('.')

        except ValueError:
            raise JWTVerificationException("invalid JWT format")

        unsigned_token = f"{header_b64}.{payload_b64}"
            
        # Verify the signature
        if not self.verify_with_kms(data=unsigned_token, signature=signature):
            raise JWTVerificationException("invalid signature")

        # Decode the payload
        payload = self.decode_segment(payload_b64)

        # Check for expiration
        now = datetime.now(tz=utc_tz).timestamp()

        # Check if the token has expired
        payload_expiration = payload.get('exp', 0)

        # If the token has expired, raise an exception
        if now >= payload_expiration:  # Fixed comparison - now should be compared with expiration
            raise JWTVerificationException("token has expired")

        return JWTClaims.from_claims(claims=payload)

    @classmethod
    def verify_token(cls, token: str) -> JWTClaims:
        """
        Verify a JWT token without needing to instantiate the class
        
        Keyword arguments:
        token -- The JWT token to verify
            
        Returns:
            The decoded payload if verification succeeds
            
        Raises:
            JWTVerificationException if verification fails
        """
        # Split the token
        try:
            header_b64, _, _ = token.split('.')

        except ValueError:
            raise JWTVerificationException("invalid JWT format")
        
        # Decode the header to get the key ID
        header = cls.decode_segment(header_b64)

        kms_key_id = header.get('kid')
        
        if not kms_key_id:
            raise JWTVerificationException("missing key ID in JWT header")
        
        # Create a temporary instance with the key ID from the header
        temp_verifier = cls(kms_key_id=kms_key_id)
        
        # Use the instance to verify the token
        return temp_verifier._verify_token(token)

    @classmethod
    def verify_with_public_key(cls, data: str, signature: str, public_key: str) -> bool:
        """
        Verify a signature using an RSA public key
        
        Keyword arguments:
        data -- The data to verify
        signature -- The signature to verify against (base64 encoded)
        public_key -- The RSA public key in PEM format
        """
        try:
            # Decode the signature from base64
            decoded_signature = cls.decode_signature(signature)
            
            # Load the public key
            key = load_pem_public_key(public_key.encode('utf-8'))
            
            # Verify the signature
            try:
                key.verify(
                    decoded_signature,
                    data.encode('utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return True

            except InvalidSignature:
                return False
        
        except Exception as e:
            raise JWTVerificationException(f"public key verification error: {str(e)}")