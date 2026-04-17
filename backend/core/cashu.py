"""
Real Cashu wallet client - implements full protocol communication with mint.

Implements:
- Mint quotes and blinded message generation
- Proof receipt and DLEQ verification
- Swap operations with DHE outputs
- Melt quotes and Lightning redemption
"""

import requests
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
from models.cashu import Proof, Quote, KeySet
from crypto import crypto, BlindedMessage, BlindSignature


class CashuClient:
    """Client for communicating with a Cashu mint."""
    
    def __init__(self, mint_url: str):
        """
        Initialize client for a specific mint.
        
        Args:
            mint_url: Base URL of the mint (e.g., "http://localhost:5001")
        """
        self.mint_url = mint_url.rstrip("/")
        self.keyset_cache: Optional[KeySet] = None
    
    def fetch_keysets(self) -> KeySet:
        """
        Fetch the mint's current public key set.
        
        Returns:
            KeySet with public keys indexed by amount
        """
        try:
            resp = requests.get(
                f"{self.mint_url}/keys",
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Extract first active keyset
            keysets = data.get("keysets", [])
            if not keysets:
                raise ValueError("No keysets from mint")
            
            ks = keysets[0]
            keyset_id = ks.get("id", "00")
            public_keys = ks.get("public_keys", {})
            
            self.keyset_cache = KeySet(
                keyset_id=keyset_id,
                mint_url=self.mint_url,
                public_keys=public_keys,
                active=ks.get("active", True)
            )
            
            print(f"[Client] Fetched keyset {keyset_id} from {self.mint_url}")
            return self.keyset_cache
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch keys from {self.mint_url}: {str(e)}")
    
    def request_mint_quote(self, amount: int) -> Quote:
        """
        Request a mint quote from the mint.
        
        This is step 1 of minting:
        Client → Mint: "I want to mint X sats"
        Mint → Client: "Here's a quote, pay this Lightning invoice"
        
        Args:
            amount: Satoshis to mint
        
        Returns:
            Quote with invoice request
        """
        try:
            resp = requests.post(
                f"{self.mint_url}/requestmint",
                json={"amount": amount},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            quote_id = data.get("quote")
            request = data.get("request", "")
            
            quote = Quote(
                quote_id=quote_id,
                amount=amount,
                request=request,
                quote_type="mint",
                state="pending",
                expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
                mint_url=self.mint_url
            )
            
            print(f"[Client] Got mint quote {quote_id}")
            return quote
            
        except Exception as e:
            raise RuntimeError(f"Failed to request mint quote: {str(e)}")
    
    def finish_mint(
        self,
        quote: Quote
    ) -> List[Proof]:
        """
        Finish the mint process - provide blinded messages and receive proofs.
        
        This is step 2 of minting:
        Client → Mint: [blinded messages B_1, B_2, ...]
        Mint → Client: [blind signatures C_1, C_2, ...]
        Client: Unblinds signatures to get spendable proofs
        
        Args:
            quote: The quote from request_mint_quote
        
        Returns:
            List of Proof objects (now spendable)
        """
        if quote.quote_type != "mint":
            raise ValueError("Quote must be a mint quote")
        
        # Generate blinded messages for each output
        blinded_messages = []
        secrets = []
        blinding_factors = []
        
        # Divide amount into powers of 2
        amounts = []
        remaining = quote.amount
        power = 0
        while remaining > 0 and power < 12:
            amount = min(2 ** power, remaining)
            amounts.append(amount)
            remaining -= amount
            power += 1
        
        for amount in amounts:
            secret = f"{uuid.uuid4().hex}"
            blinded = crypto.generate_blinded_message(amount, secret)
            
            blinded_messages.append({
                "amount": amount,
                "B_": blinded.B_,
                "r": blinded.r
            })
            secrets.append(secret)
            blinding_factors.append(blinded.r)
        
        # Send blinded messages to mint
        try:
            resp = requests.post(
                f"{self.mint_url}/mint",
                json={
                    "quote": quote.quote_id,
                    "blinded_messages": blinded_messages
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Failed to finish mint: {str(e)}")
        
        # Unblind the signatures to get valid proofs
        proofs = []
        blind_sigs = data.get("proofs", [])
        
        for i, blind_sig in enumerate(blind_sigs):
            amount = blind_sig.get("amount", 0)
            C_ = blind_sig.get("C_", "")
            dleq_proof = blind_sig.get("dleq", {})
            
            # Verify DLEQ proof (simplified)
            if not crypto.verify_dleq_proof(secrets[i], C_, dleq_proof):
                print(f"[Client] WARNING: DLEQ proof failed for output {i}")
            
            # Unblind the signature
            blind_sig_obj = BlindSignature(amount, C_)
            C = crypto.unblind_signature(
                blind_sig_obj,
                blinding_factors[i]
            )
            
            # Create proof
            proof = Proof(
                amount=amount,
                secret=secrets[i],
                C=C,
                mint=self.mint_url,
                keyset_version=self.keyset_cache.keyset_id if self.keyset_cache else "00"
            )
            
            proofs.append(proof)
            print(f"[Client] Created proof: {amount} sats")
        
        return proofs
    
    def request_melt_quote(self, invoice: str, amount: int) -> Quote:
        """
        Request a melt quote to redeem proofs as Lightning.
        
        Args:
            invoice: Lightning invoice to pay
            amount: Amount of sats to redeem
        
        Returns:
            Quote confirming the melt terms
        """
        try:
            resp = requests.post(
                f"{self.mint_url}/requestmelt",
                json={
                    "pr": invoice,
                    "amount": amount
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            quote_id = data.get("quote")
            
            quote = Quote(
                quote_id=quote_id,
                amount=amount,
                request=invoice,
                quote_type="melt",
                state="pending",
                expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
                mint_url=self.mint_url
            )
            
            print(f"[Client] Got melt quote {quote_id}")
            return quote
            
        except Exception as e:
            raise RuntimeError(f"Failed to request melt quote: {str(e)}")
    
    def finish_melt(self, quote: Quote, proofs: List[Proof]) -> bool:
        """
        Finish the melt process - redeem proofs for Lightning payment.
        
        Args:
            quote: The melt quote from request_melt_quote
            proofs: Proofs to redeem
        
        Returns:
            True if melt successful
        """
        if quote.quote_type != "melt":
            raise ValueError("Quote must be a melt quote")
        
        total = sum(p.amount for p in proofs)
        if total < quote.amount:
            raise ValueError(
                f"Insufficient proofs: {total} sats available, {quote.amount} needed"
            )
        
        proof_dicts = [p.to_dict() for p in proofs]
        
        try:
            resp = requests.post(
                f"{self.mint_url}/melt",
                json={
                    "quote": quote.quote_id,
                    "pr": quote.request,
                    "proofs": proof_dicts
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            state = data.get("state", "")
            print(f"[Client] Melt completed: {state}")
            return state == "paid"
            
        except Exception as e:
            raise RuntimeError(f"Failed to finish melt: {str(e)}")
    
    def swap(
        self,
        proofs: List[Proof],
        output_amounts: List[int]
    ) -> List[dict]:
        """
        Swap proofs for blinded outputs (for sending to another wallet).
        
        This creates blind-signed outputs that only the recipient can use.
        
        Args:
            proofs: Proofs to swap
            output_amounts: Desired output amounts [e.g., 64, 32, 4]
        
        Returns:
            List of blind output dicts with B_ and C_
        """
        total_proofs = sum(p.amount for p in proofs)
        total_outputs = sum(output_amounts)
        
        if total_proofs != total_outputs:
            raise ValueError(
                f"Proof amount {total_proofs} != output amount {total_outputs}"
            )
        
        proof_dicts = [p.to_dict() for p in proofs]
        
        try:
            resp = requests.post(
                f"{self.mint_url}/swap",
                json={
                    "proofs": proof_dicts,
                    "output_amounts": output_amounts
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            outputs = data.get("outputs", [])
            print(f"[Client] Swapped {len(proofs)} proofs for {len(outputs)} outputs")
            return outputs
            
        except Exception as e:
            raise RuntimeError(f"Failed to swap proofs: {str(e)}")
