"""
Helper functions for Ratio testing
"""
import json

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


ENTITY_CREDENTIALS_DIR = "test_entities"


@dataclass
class EntityCredentials:
    """Entity credentials and metadata"""
    entity_id: str
    private_key: bytes
    public_key: bytes
    metadata: Dict[str, Any] = None

    @property
    def private_key_pem(self) -> str:
        """Get private key as PEM string"""
        return self.private_key.decode()

    @property
    def public_key_pem(self) -> str:
        """Get public key as PEM string"""
        return self.public_key.decode()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding binary data"""
        return {
            "entity_id": self.entity_id,
            "metadata": self.metadata
        }


class EntityManager:
    """Manages entity credentials for testing"""

    def __init__(self, base_dir: str = ENTITY_CREDENTIALS_DIR):
        """
        Initialize the EntityManager with a base directory for storing entity credentials.

        Keyword arguments:
        base_dir -- the base directory where entity credentials will be stored (default: "test_entities")
        """
        # Use relative path for test entities
        # to avoid issues with absolute paths in different environments

        self.base_dir = Path(base_dir).resolve()

        self.base_dir.mkdir(exist_ok=True)

    def generate_rsa_key_pair(self) -> Tuple[bytes, bytes]:
        """Generate an RSA key pair for digital signatures"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    def create_entity(self, entity_id: str, metadata: Dict[str, Any] = None) -> EntityCredentials:
        """Create a new entity with generated keys"""
        private_key, public_key = self.generate_rsa_key_pair()

        entity = EntityCredentials(
            entity_id=entity_id,
            private_key=private_key,
            public_key=public_key,
            metadata=metadata or {}
        )

        self.save_entity(entity)

        return entity

    def save_entity(self, entity: EntityCredentials):
        """Save entity credentials to disk"""
        entity_dir = self.base_dir / entity.entity_id

        entity_dir.mkdir(exist_ok=True)
        
        # Save private key
        with open(entity_dir / "private.pem", "wb") as f:
            f.write(entity.private_key)

        # Save public key
        with open(entity_dir / "public.pem", "wb") as f:
            f.write(entity.public_key)

        # Save metadata
        if entity.metadata:
            with open(entity_dir / "metadata.json", "w") as f:
                json.dump(entity.metadata, f, indent=2)

    def load_entity(self, entity_id: str) -> Optional[EntityCredentials]:
        """Load entity credentials from disk"""
        entity_dir = self.base_dir / entity_id

        if not entity_dir.exists():
            return None

        # Load private key
        with open(entity_dir / "private.pem", "rb") as f:
            private_key = f.read()

        # Load public key
        with open(entity_dir / "public.pem", "rb") as f:
            public_key = f.read()

        # Load metadata
        metadata = {}

        metadata_file = entity_dir / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)

        return EntityCredentials(
            entity_id=entity_id,
            private_key=private_key,
            public_key=public_key,
            metadata=metadata
        )

    def update_entity(self, entity: EntityCredentials):
        """Update an existing entity's credentials"""
        self.save_entity(entity)

    def delete_entity(self, entity_id: str):
        """Delete entity credentials from disk"""
        entity_dir = self.base_dir / entity_id

        if entity_dir.exists():

            for file in entity_dir.iterdir():
                file.unlink()

            entity_dir.rmdir()

    def entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        return (self.base_dir / entity_id).exists()