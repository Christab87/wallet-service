"""Mock Cashu mint service (legacy).

Note: This is superseded by the standalone mint_server.py.
Kept for reference but not actively used.
"""

import uuid
from typing import List


class MintService:
    """Legacy mock Cashu mint."""

    def __init__(self):
        # Initialize with default local mint server
        self.mints = [
            {
                "id": "localhost-5001",
                "name": "Local Mint",
                "url": "http://localhost:5001",
                "created_at": str(__import__("time").time()),
            }
        ]
        self.keys = {"cashu:localhost": {"amount": "1"}}

    def create_mint(
        self, amount: int, name: str
    ) -> str:
        mint_id = str(uuid.uuid4())
        self.mints.append(
            {
                "id": mint_id,
                "name": name,
                "amount": amount,
                "created_at": str(__import__("time").time()),
            }
        )
        return mint_id

    def add_mint_from_url(self, url: str, name: str = None) -> str:
        """Add a mint by URL."""
        mint_id = str(uuid.uuid4())
        if not name:
            name = url.split("/")[-1] if url != "http://localhost:5001" else "Local Mint"
        
        self.mints.append({
            "id": mint_id,
            "name": name,
            "url": url,
            "created_at": str(__import__("time").time()),
        })
        return mint_id

    def get_mints(self) -> List:
        return list(self.mints)
    
    def get_mint_by_url(self, url: str):
        """Get mint details by URL."""
        for mint in self.mints:
            if mint.get("url") == url:
                return mint
        return None
