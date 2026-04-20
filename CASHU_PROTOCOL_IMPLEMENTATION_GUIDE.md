# Cashu Protocol Implementation Guide - Educational Reference

This file contains Python code examples demonstrating blind signing, mint protocol, swap, melt, and quote management.

## Reference Code

```python


# ==============================================================================
# PART 1: BLIND SIGNING (RSA-PSS)
# ==============================================================================

class BlindSigningStep1:
    # User creates blinded message for privacy
    
    @staticmethod
    def generate_blinded_message(amount: int, secret: str) -> Dict:
        # Generate blinded message that hides secret from mint
        secret_hash = hashlib.sha256(secret.encode()).digest()
        secret_int = int.from_bytes(secret_hash, 'big')
        
        # Generate random blinding factor (32 bytes)
        r_bytes = os.urandom(32)
        r_int = int.from_bytes(r_bytes, 'big')
        
        # Combine secret and blinding factor
        combined = hashlib.sha256(secret_hash + r_bytes).digest()
        
        # Convert to hex for transmission
        B_ = combined.hex()
        r = r_bytes.hex()
        
        return {
            "amount": amount,
            "B_": B_,      # Send to mint
            "r": r         # Keep secret
        }


class BlindSigningStep2:
    # Mint signs the blinded message without seeing the secret
    
    @staticmethod
    def blind_sign(blinded_message: Dict, private_key_pem: str) -> Dict:
        # Mint blindly signs the blinded message for privacy-preserving minting
        
        # Import here to avoid dependencies
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
        
        # Load private key from PEM
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Convert blinded message from hex to bytes
        B_bytes = bytes.fromhex(blinded_message["B_"])
        
        # Sign with RSA-PSS
        signature = private_key.sign(
            B_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Convert signature to hex
        C_ = signature.hex()
        
        return {
            "amount": blinded_message["amount"],
            "C_": C_  # Blind signature for user to unblind
        }


class BlindSigningStep3:
    # User unblinds the signature to create a spendable proof
    
    @staticmethod
    def unblind_signature(blind_sig: Dict, blinding_factor: str) -> str:
        # Unblind the mint's signature using the blinding factor
        
        # Convert blind signature and factor from hex to bytes
        C_bytes = bytes.fromhex(blind_sig["C_"])
        r_bytes = bytes.fromhex(blinding_factor)
        
        # Unblind by hashing signature and blinding factor
        C = hashlib.sha256(C_bytes + r_bytes).hexdigest()
        
        return C


class BlindSigningStep4:
    # Verify DLEQ proof (Discrete Log Equality)
    
    @staticmethod
    def verify_dleq_proof(proof_secret: str, commitment: str, dleq_proof: Dict) -> bool:
        # Verify DLEQ proof that commitment matches secret (simplified check)
        
        # Check required fields exist
        required_fields = ['z', 'r', 'e']
        if not all(field in dleq_proof for field in required_fields):
            return False
        
        # Validate hex format
        try:
            int(dleq_proof['z'], 16)
            int(dleq_proof['r'], 16)
            int(dleq_proof['e'], 16)
        except (ValueError, TypeError):
            return False
        
        return True


# ==============================================================================
# PART 2: MINT PROTOCOL (Request → Blind Sign → Unblind)
# ==============================================================================

class MintProtocolPhase1:
    # User requests a mint quote from the mint
    
    @staticmethod
    def request_mint_quote(mint_url: str, amount: int) -> Dict:
        # Request mint quote to initiate minting process
        
        import requests
        
        try:
            response = requests.post(
                f"{mint_url}/requestmint",
                json={"amount": amount},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "quote_id": data.get("quote"),
                "request": data.get("request", ""),
                "state": "pending",
                "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
        except Exception as e:
            raise RuntimeError(f"Failed to request mint quote: {str(e)}")


class MintProtocolPhase2:
    # User finishes minting by sending blinded messages and receiving proofs
    
    @staticmethod
    def finish_mint(mint_url: str, quote: Dict, blinded_messages: List[Dict]) -> List[Dict]:
        # Complete minting: send blinded messages, receive blind signatures, unblind
        
        import requests
        
        try:
            # Send blinded messages to mint
            response = requests.post(
                f"{mint_url}/mint",
                json={
                    "quote": quote["quote_id"],
                    "blinded_messages": blinded_messages
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            proofs = []
            for proof_data in data.get("proofs", []):
                proofs.append({
                    "amount": proof_data.get("amount"),
                    "C": proof_data.get("C_"),
                    "dleq": proof_data.get("dleq")
                })
            
            return proofs
        except Exception as e:
            raise RuntimeError(f"Failed to finish mint: {str(e)}")


# ==============================================================================
# PART 3: SWAP PROTOCOL (Send proofs to other wallet)
# ==============================================================================

class SwapProtocol:
    # Exchange proofs for blinded outputs to send to another wallet
    
    @staticmethod
    def client_swap(mint_url: str, proofs: List[Dict], output_amounts: List[int]) -> List[Dict]:
        # Swap proofs for blinded outputs to create sendable token
        
        import requests
        
        total_proof = sum(p.get("amount", 0) for p in proofs)
        total_output = sum(output_amounts)
        
        if total_proof != total_output:
            raise ValueError(f"Proof amount {total_proof} != output amount {total_output}")
        
        try:
            response = requests.post(
                f"{mint_url}/swap",
                json={
                    "proofs": proofs,
                    "output_amounts": output_amounts
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("outputs", [])
        except Exception as e:
            raise RuntimeError(f"Failed to swap proofs: {str(e)}")


# ==============================================================================
# PART 4: MELT PROTOCOL (Redeem proofs as Lightning)
# ==============================================================================

class MeltProtocolPhase1:
    # Request a melt quote to redeem proofs as Lightning payment
    
    @staticmethod
    def client_request_melt_quote(mint_url: str, invoice: str, amount: int) -> Dict:
        # Request melt quote to redeem proofs for Lightning
        
        import requests
        
        try:
            response = requests.post(
                f"{mint_url}/requestmelt",
                json={
                    "pr": invoice,
                    "amount": amount
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "quote_id": data.get("quote"),
                "amount": amount,
                "state": "pending",
                "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
        except Exception as e:
            raise RuntimeError(f"Failed to request melt quote: {str(e)}")


class MeltProtocolPhase2:
    # User finishes melting by sending proofs to redeem as Lightning
    
    @staticmethod
    def client_finish_melt(mint_url: str, quote: Dict, proofs: List[Dict]) -> bool:
        # Complete melt: send proofs to mint, receive Lightning payment confirmation
        
        import requests
        
        try:
            response = requests.post(
                f"{mint_url}/melt",
                json={
                    "quote": quote["quote_id"],
                    "proofs": proofs,
                    "pr": quote.get("invoice", "")
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("state") == "paid"
        except Exception as e:
            raise RuntimeError(f"Failed to finish melt: {str(e)}")


# ==============================================================================
# PART 5: QUOTE MANAGEMENT
# ==============================================================================

class QuoteManagement:
    # Manage mint and melt quotes with expiration tracking
    
    def __init__(self):
        # Initialize quote manager
        self.pending_quotes = {}
    
    def create_quote(self, quote_id: str, amount: int, quote_type: str) -> Dict:
        # Create and track a new quote
        quote = {
            "quote_id": quote_id,
            "amount": amount,
            "type": quote_type,
            "state": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
        }
        self.pending_quotes[quote_id] = quote
        return quote
    
    def is_expired(self, quote_id: str) -> bool:
        # Check if quote has expired
        if quote_id not in self.pending_quotes:
            return True
        
        quote = self.pending_quotes[quote_id]
        expires = datetime.fromisoformat(quote["expires_at"])
        return datetime.now() > expires
    
    def get_quote(self, quote_id: str) -> Optional[Dict]:
        # Retrieve quote by ID
        return self.pending_quotes.get(quote_id)
    
    def remove_quote(self, quote_id: str) -> None:
        # Remove quote after completion
        if quote_id in self.pending_quotes:
            del self.pending_quotes[quote_id]


# ==============================================================================
# EDUCATIONAL REFERENCE (COMMENTED)
# ==============================================================================

# CASHU PROTOCOL OVERVIEW:
#
# 1. BLIND SIGNING
#    - User hashes secret and blinds it with random factor r
#    - Sends blinded message B_ to mint (mint doesn't see secret)
#    - Mint signs: C_ = RSA_sign(B_)
#    - User unblinds: C = unblind(C_, r)
#    - Result: C is valid signature of secret
#
# 2. MINTING
#    - User requests quote with amount
#    - User pays Lightning invoice
#    - User sends blinded messages to mint
#    - Mint returns blind signatures
#    - User unblinds to create proofs
#    - Result: User has proofs worth amount
#
# 3. SWAPPING
#    - User sends proofs to mint with output amounts
#    - Mint blindly signs new commitments
#    - User receives blinded outputs
#    - User sends outputs to recipient
#    - Recipient unblinds to get new proofs
#    - Result: Recipient has proofs
#
# 4. MELTING
#    - User requests melt quote with Lightning invoice
#    - User sends proofs to mint
#    - Mint verifies proofs and pays invoice
#    - Proofs are marked as spent
#    - Result: Fiat/Lightning payment sent
#
# PRIVACY PROPERTIES:
# - Mint never learns user secrets
# - Mint cannot link proofs to users
# - Mint cannot track sender/receiver
# - Proofs are anonymous and untrackable
```
# Cashu Protocol Implementation Guide - Educational Reference
# Demonstrates blind signing, mint protocol, swap, melt, and quote management

import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


# ==============================================================================
# PART 1: BLIND SIGNING (RSA-PSS)
# ==============================================================================

class BlindSigningStep1:
    # User creates blinded message
    
    @staticmethod
    def generate_blinded_message(amount: int, secret: str) -> Dict:
        # Generate blinded message for secret
        
        # Step 1: Hash the user's secret
        secret_hash = hashlib.sha256(secret.encode()).digest()
        
        # Convert to integer for mathematical operations
        secret_int = int.from_bytes(secret_hash, 'big')
        
        # Step 2: Generate random blinding factor (32 bytes = 256 bits)
        r_bytes = os.urandom(32)
        r_int = int.from_bytes(r_bytes, 'big')
        
        # Step 3: Blind the commitment with secret and random factor
        # Production Cashu: B_ = (secret_int * r_int) mod n
        # Here: B_ = SHA256(secret_hash + r_bytes)
        combined = hashlib.sha256(secret_hash + r_bytes).digest()
        
        # Convert to hex for transmission
        B_ = combined.hex()
        r = r_bytes.hex()
        
        # Step 4: Send blinded message (B_) to mint, keep r secret
        return BlindedMessage(
            amount=amount,
            B_=B_,        # Send to mint ✓
            r=r           # Keep secret ✓
        )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Blind Sign (Mint Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep2:
    # Mint signs blinded message
    
    @staticmethod
    def blind_sign(blinded_message: BlindedMessage, private_key_pem: str):
        # Mint signs blinded message
       """ 
        The key insight: The mint signs the blinded message B_,
        not the secret. Since it's blinded, the mint doesn't learn what
        the secret is.
        
        Process:
        1. Receive blinded message B_ from user
        2. Sign with RSA-PSS: C_ = RSA_sign(B_)
        3. Return blind signature C_ to user
        
        The mint doesn't know:
        - What the original secret is
        - What the unblinded signature will be
        - Which proofs came from which user
        
        Args:
            blinded_message: The BlindedMessage with B_ that we receive
            private_key_pem: Mint's private RSA key (PEM format)
        
        Returns:
            BlindSignature with C_ that the user can unblind
        """
        
        # Step 1: Load mint's private RSA key from PEM
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Step 2: Convert blinded message from hex string to bytes
        B_bytes = bytes.fromhex(blinded_message.B_)
        
        # Step 3: Sign with RSA-PSS and SHA256
        # RSA-PSS adds randomness, so identical inputs don't produce identical
        # outputs
        signature = private_key.sign(
            B_bytes,
            padding.PSS(
                # MGF1 is the mask generation function
                mgf=padding.MGF1(hashes.SHA256()),
                # PSS.DIGEST_LENGTH = salt length = hash output size
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Step 4: Convert signature to hex for transmission
        C_ = signature.hex()
        
        # Return blind signature
        return BlindSignature(
            amount=blinded_message.amount,
            C_=C_  # Blind signature - user will unblind this
        )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Signature Unblinding (User Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep3:
    # User unblinds signature to get spendable proof
    
    @staticmethod
    def unblind_signature(blind_signature: BlindSignature, blinding_factor: str):
        # Unblind signature to create spendable proof
       """ 
        Now the user takes the blind signature C_ and their secret blinding
        factor r and creates an unblinded signature C that can be spent.
        
        Process:
        1. Receive blind signature C_ from mint
        2. Unblind: C = sha256(C_ + r)
        3. Create proof (secret, C, amount) that can be spent
        
        Magic property: 
        - The mint signed B_ (which is sha256(secret + r))
        - User unblinds: C = sha256(C_ + r)
        - Result: C is a valid signature of the secret!
        
        Args:
            blind_signature: The C_ that is received from mint
            blinding_factor: The r factor from generate_blinded_message()
        
        Returns:
            Unblinded signature C (hex string) that can be spent
        """
        
        # Step 1: Convert blind signature and blinding factor from hex to bytes
        C_bytes = bytes.fromhex(blind_signature.C_)
        r_bytes = bytes.fromhex(blinding_factor)
        
        # Step 2: Unblind by hashing signature and factor together
        # Production Cashu: C = (C_ / r) mod n (modular arithmetic)
        # Here: C = SHA256(C_ + r)
        C = hashlib.sha256(C_bytes + r_bytes).hexdigest()
        
        # Step 3: Return unblinded signature (now spendable)
        return C


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: DLEQ Proof Verification
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep4:
    # Verify DLEQ proof
    
    @staticmethod
    def verify_dleq_proof(proof_secret: str, commitment: str, dleq_proof: dict):
        # Verify DLEQ proof (simplified check)
       """ 
        DLEQ proof verifies: "The commitment C corresponds to the secret in the
        same way that C_ corresponds to B_" without revealing the secret.
        
        Current implementation: SIMPLIFIED (not cryptographically verified)
        - Only checks that required fields are present
        - Validates that they are valid hex strings
        
        Production implementation would:
        - Use elliptic curve cryptography
        - Verify zero-knowledge proof equations
        
        Args:
            proof_secret: The user's original secret
            commitment: The unblinded commitment C
            dleq_proof: Proof data from mint with fields z, r, e
        
        Returns:
            True if fields are present and valid, False otherwise
        """
        
        # Step 1: Check that required fields are present
        required_fields = ['z', 'r', 'e']
        if not all(field in dleq_proof for field in required_fields):
            return False
        
        # Step 2: Validate that each field is valid hex
        try:
            int(dleq_proof['z'], 16)  # Parse as hex
            int(dleq_proof['r'], 16)
            int(dleq_proof['e'], 16)
        except (ValueError, TypeError):
            return False
        
        # In production: Perform actual elliptic curve verification
        # This would include complex math for zero-knowledge proof verification
        
        return True


# ==============================================================================
# PART 2: MINT PROTOCOL (Generate → Sign → Unblind)
# ==============================================================================
"""
The mint protocol is a 2-phase process:

PHASE 1: REQUEST MINT QUOTE
  Client: "I want to mint 100 Sats"
  Mint: "Pay this Lightning invoice, get Quote_ID"

PHASE 2: FINISH MINTING
  Client: "Here's my Quote_ID and blinded messages"
  Mint: "Here are blind signatures"
  Client: "I'll unblind these to get proofs"

Result: Client has 100 Sats in proofs (ecash tokens)
"""

# ─────────────────────────────────────────────────────────────────────────────
# MINT PHASE 1: Request mint quote
# ─────────────────────────────────────────────────────────────────────────────

class MintProtocolPhase1:
    # Request mint quote
    
    @staticmethod
    def request_mint_quote(mint_url: str, amount: int):
        # Request mint quote from mint
       """ 
        Step 1 of minting: Client requests mint quote.
        Mint returns a Lightning invoice to pay.
        
        Process:
        1. Client sends: POST /requestmint with amount=100
        2. Mint creates Quote_ID (tracked in MINT_QUOTES)
        3. Mint generates Lightning invoice
        4. Mint returns: Quote_ID, invoice, expiration (5 minutes)
        
        Args:
            mint_url: Mint's base URL (e.g., "http://localhost:5001")
            amount: Sats to mint
        
        Returns:
            Quote object with:
            - quote_id: Unique quote identifier
            - request: Lightning invoice to pay
            - state: "pending"
            - expires_at: ISO timestamp (now + 5 minutes)
        """
        
        # Step 1: Send request to mint server
        response = requests.post(
            f"{mint_url}/requestmint",
            json={"amount": amount},
            timeout=10
        )
        data = response.json()
        
        # Step 2: Extract response data
        quote_id = data.get("quote")          # e.g., "d6702017-7321-4fc6-..."
        invoice = data.get("request", "")     # e.g., "lnbc100u1p0mockivv"
        
        # Step 3: Create quote object with 5-minute expiration
        quote = Quote(
            quote_id=quote_id,
            amount=amount,
            request=invoice,
            quote_type="mint",
            state="pending",
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            mint_url=mint_url
        )
        
        # Step 4: Return quote for next phase
        return quote


# ─────────────────────────────────────────────────────────────────────────────
# MINT PHASE 2: Finish minting
# ─────────────────────────────────────────────────────────────────────────────

class MintProtocolPhase2:
    # Mint protocol: finish minting process
    
    @staticmethod
    def finish_mint(mint_url: str, quote: Quote):
        # Finish minting: create blinded messages and receive signatures
       """ 
        Step 2 of minting: 
        1. Generate blinded messages for each denomination
        2. Send to mint
        3. Receive blind signatures
        4. Unblind signatures to get spendable proofs
        
        Process:
        1. Split amount into powers of two: [64, 32, 4]
        2. For each amount: generate_blinded_message()
        3. Send all blinded messages to mint
        4. Mint returns blind signatures
        5. For each signature: unblind_signature()
        6. Create proof objects (secret, C, amount)
        7. Return proofs to wallet
        
        Args:
            mint_url: Mint server URL
            quote: Quote from request_mint_quote()
        
        Returns:
            List of proof objects (now spendable)
        """
        
        # Step 1: Split amount into denominations (powers of two)
        # Example: 100 Sats → [64, 32, 4]
        amounts = []
        remaining = quote.amount
        power = 0
        while remaining > 0 and power < 12:
            amount = min(2 ** power, remaining)  # Use min, don't go too far
            amounts.append(amount)
            remaining -= amount
            power += 1
        
        # Step 2: Generate blinded messages for each amount
        blinded_messages = []
        secrets = []
        blinding_factors = []
        
        for amount in amounts:
            # Create random secret for this proof
            secret = f"{uuid.uuid4().hex}"
            
            # Generate blinded message
            blinded = crypto.generate_blinded_message(amount, secret)
            
            # Track for later unblinding
            blinded_messages.append({
                "amount": amount,
                "B_": blinded.B_,    # Send this
                "r": blinded.r       # Keep secret
            })
            secrets.append(secret)
            blinding_factors.append(blinded.r)
        
        # Step 3: Send blinded messages to mint
        response = requests.post(
            f"{mint_url}/mint",
            json={
                "quote": quote.quote_id,
                "blinded_messages": blinded_messages
            },
            timeout=10
        )
        data = response.json()
        
        # Step 4: Receive blind signatures from mint
        blind_sigs = data.get("proofs", [])
        
        # Step 5: Unblind signatures and create proofs
        proofs = []
        
        for i, blind_sig in enumerate(blind_sigs):
            amount = blind_sig.get("amount", 0)
            C_ = blind_sig.get("C_", "")
            dleq_proof = blind_sig.get("dleq", {})
            
            # Verify DLEQ proof (simplified)
            if not crypto.verify_dleq_proof(secrets[i], C_, dleq_proof):
                print(f"[Client] WARNING: DLEQ proof failed for output {i}")
            
            # Unblind signature
            blind_sig_obj = BlindSignature(amount, C_)
            C = crypto.unblind_signature(
                blind_sig_obj,
                blinding_factors[i]  # Use the r factor
            )
            
            # Step 6: Create proof object (now spendable)
            proof = Proof(
                amount=amount,
                secret=secrets[i],           # The original secret
                C=C,                         # The unblinded signature
                mint=mint_url,               # Which mint issued this
                keyset_version="00"          # Keyset version
            )
            
            proofs.append(proof)
        
        # Step 7: Return proofs to wallet
        return proofs


# ==============================================================================
# PART 3: SWAP PROTOCOL (Proof Exchange)
# ==============================================================================
"""
The swap protocol allows a user to exchange their proofs for blind outputs
that they can send to another user.

Process:
1. Sender: "I want to send 100 Sats. Here are my proofs."
2. Mint: "I'll create blind outputs for you."
3. Sender: "I'm sending these blind outputs to the recipient."
4. Recipient: "I received these blind outputs and unblinded them!"

Key insight: The blind outputs are created with the RECIPIENT'S blinding
factor, so only the recipient can unblind them. The sender cannot spend
them after creation.
"""

class SwapProtocol:
    # Swap proofs for blinded outputs
    
    @staticmethod
    def client_swap(mint_url: str, proofs_to_send: List[Proof], 
                    output_amounts: List[int]):
        """
        CLIENT OPERATION: Exchange proofs for blind outputs to send.
        
        Used when the user wants to send money via token to another wallet.
        
        Process:
        1. Select proofs from wallet that cover the amount
        2. Call swap()
        3. Mint returns blind outputs
        4. Encode outputs as token
        5. Remove proofs from wallet (now spent)
        6. Send token to recipient
        
        Args:
            mint_url: Mint URL
            proofs_to_send: List of proofs to exchange
            output_amounts: Desired output denominations [64, 32, 4]
        
        Returns:
            List of blind outputs to encode as token
        """
        
        # Step 1: Check amounts match
        total_proofs = sum(p.amount for p in proofs_to_send)
        total_outputs = sum(output_amounts)
        
        if total_proofs != total_outputs:
            raise ValueError(f"Proof amount {total_proofs} != output {total_outputs}")
        
        # Step 2: Serialize proofs for transmission
        proof_dicts = [p.to_dict() for p in proofs_to_send]
        
        # Step 3: Call mint swap endpoint
        response = requests.post(
            f"{mint_url}/swap",
            json={
                "proofs": proof_dicts,
                "output_amounts": output_amounts
            },
            timeout=10
        )
        data = response.json()
        
        # Step 4: Receive blind outputs
        outputs = data.get("outputs", [])
        
        # Step 5: Outputs now ready to encode as token
        return outputs


# ==============================================================================
# PART 4: MELT PROTOCOL (Quote + Redemption)
# ==============================================================================
"""
The melt protocol allows users to redeem ecash proofs back to fiat/Lightning.

PHASE 1: REQUEST MELT QUOTE
  Client: "I want to redeem 100 Sats via this Lightning invoice"
  Mint: "OK, here's a melt quote with 5-minute expiration"

PHASE 2: FINISH MELTING
  Client: "Here are my proofs and quote_id"
  Mint: "I'll validate and pay the Lightning invoice"
  Client: "Confirmed! Proofs are now spent."

Result: Client received real Lightning Sats (or fiat equivalent)
"""

class MeltProtocolPhase1:
    # Request melt quote
    
    @staticmethod
    def client_request_melt_quote(mint_url: str, invoice: str, amount: int):
        # Request melt quote
        
        # Step 1: Send request to mint
        response = requests.post(
            f"{mint_url}/requestmelt",
            json={
                "pr": invoice,      # pr = payment request
                "amount": amount
            },
            timeout=10
        )
        data = response.json()
        
        # Step 2: Create quote object
        quote_id = data.get("quote")
        quote = Quote(
            quote_id=quote_id,
            amount=amount,
            request=invoice,
            quote_type="melt",
            state="pending",
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            mint_url=mint_url
        )
        
        return quote


class MeltProtocolPhase2:
    # Finish melt process
    
    @staticmethod
    def client_finish_melt(mint_url: str, quote: Quote, 
                          proofs: List[Proof]) -> bool:
        # Finish melting: redeem proofs
        """
        Step 2 of melting: Send proofs to mint for redemption.
        
        Args:
            mint_url: Mint server URL
            quote: Melt quote from request_melt_quote()
            proofs: Proofs to redeem
        
        Returns:
            True if melt is successful, False otherwise
        """
        
        # Step 1: Check amount
        total = sum(p.amount for p in proofs)
        if total < quote.amount:
            raise ValueError(f"Insufficient proofs: {total} < {quote.amount}")
        
        # Step 2: Serialize proofs
        proof_dicts = [p.to_dict() for p in proofs]
        
        # Step 3: Send to mint
        response = requests.post(
            f"{mint_url}/melt",
            json={
                "quote": quote.quote_id,
                "pr": quote.request,    # Invoice to pay
                "proofs": proof_dicts
            },
            timeout=10
        )
        data = response.json()
        
        # Step 4: Check if mint confirmed
        state = data.get("state", "")
        return state == "paid"


# ==============================================================================
# PART 5: QUOTE MANAGEMENT (Expiration, State Tracking)
# ==============================================================================
"""

Quotes manage time-bound transactions. They prevent:
- Users from minting without payment
- Indefinite hangs if something breaks
- Double-spending the same quote twice

State path: pending → confirmed → expired
Expiration: 5 minutes from creation
"""

class QuoteManagement:
    # Quote lifecycle management
    
    # Quote model
    class Quote:
        # Mint or melt quote representation
        
        def __init__(
            self,
            quote_id: str,
            amount: int,
            request: str,              # Invoice or Cashu request
            quote_type: str,           # "mint" or "melt"
            state: str = "pending",    # pending, confirmed, expired
            expires_at: Optional[str] = None,
            mint_url: str = "http://localhost:5001"
        ):
            """
            Initialize a quote.
            
            Args:
                quote_id: Unique identifier (UUID)
                amount: Sats involved
                request: Lightning invoice or Cashu request
                quote_type: "mint" creates proofs, "melt" redeems them
                state: Current status (pending/confirmed/expired)
                expires_at: ISO timestamp when quote expires
                mint_url: Which mint issued this quote

            """
            self.quote_id = quote_id
            self.amount = amount
            self.request = request
            self.quote_type = quote_type
            self.state = state
            self.expires_at = expires_at
            self.created_at = datetime.now().isoformat()
            self.mint_url = mint_url
        
        def is_expired(self) -> bool:
            # Check if quote has expired
            if not self.expires_at:
                return False
            
            # Parse ISO timestamp
            expires = datetime.fromisoformat(self.expires_at)
            
            # Compare with current time
            return datetime.now() > expires
        
        
        def to_dict(self) -> dict:
            # Serialize quote for storage
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
    
    
    # Wallet quote tracking
    class WalletQuoteTracking:
        # Track pending quotes in wallet
        
        def __init__(self):
            # Initialize quote tracking
            self.pending_quotes = {}  # {quote_id: quote_data}
        
        
        def add_quote(self, quote: Quote):
            # Add quote to pending list
            """
            Called when:
            - User requests mint quote
            - User requests melt quote
            
            Storage:
            - In memory during session
            - Lost on server restart (design limitation)
            
            Args:
                quote: Quote object
            """
            self.pending_quotes[quote.quote_id] = quote
            print(f"[Wallet] Tracking quote {quote.quote_id}")
        
        
        def get_quote(self, quote_id: str) -> Optional[Quote]:
            # Get quote by ID
            """
            Before using, check:
            - Quote exists
            - Quote is not expired
            - Quote is correct type (mint vs melt)
            
            Args:
                quote_id: UUID of quote
            
            Returns:
                Quote object or None if not found
            """
            return self.pending_quotes.get(quote_id)
        
        
        def remove_quote(self, quote_id: str):
            # Remove quote after completion
            """
            Called when:
            - finish_mint() succeeds
            - finish_melt() succeeds
            - Quote expires (cleanup)
            
            Args:
                quote_id: UUID of quote to remove
            """
            if quote_id in self.pending_quotes:
                del self.pending_quotes[quote_id]
                print(f"[Wallet] Quote removed {quote_id}")


# ==============================================================================
# SUMMARY: Complete Protocol Flow
# ==============================================================================

"""
COMPLETE TRANSACTION FLOW:

1. MINTING (creating 100 Sats ecash)
2. SWAPPING (sending 50 Sats to another wallet)
3. MELTING (redeeming 25 Sats to Lightning/Fiat)

Each step uses Chaum's blind signing protocol for complete
cryptographic anonymity and security.
"""
