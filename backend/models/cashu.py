"""
Enhanced Cashu models for production protocol support.
"""

from datetime import datetime
from typing import Optional, Dict, List


class Proof:
    """Ecash proof - represents ownership of satoshis."""
    
    def __init__(
        self,
        amount: int,
        secret: str,
        C: str,
        mint: str,
        keyset_version: str = "00"
    ):
        self.amount = amount
        self.secret = secret  # The blinding secret (kept private)
        self.C = C            # The commitment (unblinded signature)
        self.mint = mint
        self.keyset_version = keyset_version
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "secret": self.secret,
            "C": self.C,
            "mint": self.mint,
            "keyset_version": self.keyset_version,
            "created_at": self.created_at
        }
    
    @staticmethod
    def from_dict(data: dict):
        return Proof(
            amount=data["amount"],
            secret=data["secret"],
            C=data["C"],
            mint=data.get("mint", ""),
            keyset_version=data.get("keyset_version", "00")
        )
    
    def __repr__(self):
        return f"<Proof {self.amount} sats @ {self.mint}>"
    
    def __eq__(self, other):
        return (
            isinstance(other, Proof) and
            self.secret == other.secret and
            self.C == other.C
        )


class Quote:
    """Mint or Melt quote - represents a time-bound transaction request."""
    
    def __init__(
        self,
        quote_id: str,
        amount: int,
        request: str,  # Lightning invoice (for melt) or cashu request (for mint)
        quote_type: str,  # "mint" or "melt"
        state: str = "pending",  # pending, confirmed, expired
        expires_at: Optional[str] = None,
        mint_url: str = "http://localhost:5001"  # Mint URL for this quote
    ):
        self.quote_id = quote_id
        self.amount = amount
        self.request = request
        self.quote_type = quote_type  # mint or melt
        self.state = state
        self.expires_at = expires_at
        self.created_at = datetime.now().isoformat()
        self.mint_url = mint_url
    
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires
    
    def to_dict(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "amount": self.amount,
            "request": self.request,
            "quote_type": self.quote_type,
            "state": self.state,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "mint_url": self.mint_url
        }
    
    @staticmethod
    def from_dict(data: dict):
        return Quote(
            quote_id=data["quote_id"],
            amount=data["amount"],
            request=data["request"],
            quote_type=data["quote_type"],
            state=data.get("state", "pending"),
            expires_at=data.get("expires_at")
        )


class KeySet:
    """Mint's signing keyset - tracks public keys for proof verification."""
    
    def __init__(
        self,
        keyset_id: str,
        mint_url: str,
        public_keys: Dict[int, str],
        active: bool = True,
        imported_at: Optional[str] = None
    ):
        self.keyset_id = keyset_id
        self.mint_url = mint_url
        self.public_keys = public_keys  # {amount: public_key_pem}
        self.active = active
        self.imported_at = imported_at or datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "keyset_id": self.keyset_id,
            "mint_url": self.mint_url,
            "public_keys": self.public_keys,
            "active": self.active,
            "imported_at": self.imported_at
        }
    
    @staticmethod
    def from_dict(data: dict):
        return KeySet(
            keyset_id=data["keyset_id"],
            mint_url=data["mint_url"],
            public_keys=data.get("public_keys", {}),
            active=data.get("active", True),
            imported_at=data.get("imported_at")
        )


class Token:
    """Cashu token - a portable unit of value."""
    
    def __init__(self, mint: str, proofs: List[Proof]):
        self.mint = mint
        self.proofs = proofs
        self.created_at = datetime.now().isoformat()
    
    @property
    def total_amount(self) -> int:
        return sum(p.amount for p in self.proofs)
    
    def to_dict(self) -> dict:
        return {
            "mint": self.mint,
            "proofs": [p.to_dict() for p in self.proofs],
            "created_at": self.created_at
        }
