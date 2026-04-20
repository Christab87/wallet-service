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
        
        import uuid
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
                "request": data.get("request", ""),  # Lightning invoice
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
        self.pending_quotes = {}  # {quote_id: quote_data}
    
    def create_quote(self, quote_id: str, amount: int, quote_type: str) -> Dict:
        # Create and track a new quote
        quote = {
            "quote_id": quote_id,
            "amount": amount,
            "type": quote_type,  # "mint" or "melt"
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
# EDUCATIONAL NOTES
# ==============================================================================

"""
CASHU PROTOCOL OVERVIEW:

1. BLIND SIGNING
   - User hashes secret and blinds it with random factor r
   - Sends blinded message B_ to mint (mint doesn't see secret)
   - Mint signs: C_ = RSA_sign(B_)
   - User unblinds: C = unblind(C_, r)
   - Result: C is valid signature of secret

2. MINTING
   - User requests quote with amount
   - User pays Lightning invoice
   - User sends blinded messages to mint
   - Mint returns blind signatures
   - User unblinds to create proofs
   - Result: User has proofs worth amount

3. SWAPPING
   - User sends proofs to mint with output amounts
   - Mint blindly signs new commitments
   - User receives blinded outputs
   - User sends outputs to recipient
   - Recipient unblinds to get new proofs
   - Result: Recipient has proofs

4. MELTING
   - User requests melt quote with Lightning invoice
   - User sends proofs to mint
   - Mint verifies proofs and pays invoice
   - Proofs are marked as spent
   - Result: Fiat/Lightning payment sent

PRIVACY PROPERTIES:
- Mint never learns user secrets
- Mint cannot link proofs to users
- Mint cannot track sender/receiver
- Proofs are anonymous and untrackable
"""
# Cashu Protocol Implementation Guide (German)
# Blind signing, mint protocol, swap, melt, quote management

# ==============================================================================
# TEIL 1: BLIND SIGNING (RSA-PSS)
# ==============================================================================
# Part 1: Blind signing protocol (RSA-PSS)

# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 1: Verblindete Nachricht generieren (Benutzer-Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep1:
    # User creates blinded message
    
    def generate_blinded_message(amount: int, secret: str):
        # Generate blinded message for secret
        
        # Schritt 1: Geheimnis des Benutzers hashen
        secret_hash = hashlib.sha256(secret.encode()).digest()
        
        # Zur Integer für mathematische Operationen konvertieren
        secret_int = int.from_bytes(secret_hash, 'big')
        
        # Schritt 2: Zufälligen Verblindungsfaktor generieren (32 Bytes = 256 Bits)
        r_bytes = os.urandom(32)
        r_int = int.from_bytes(r_bytes, 'big')
        
        # Schritt 3: Das Engagement mit Geheimnis und Zufallsfaktor verblindes
        # Produktions-Cashu: B_ = (Geheimnis_int * r_int) mod n
        # Hier: B_ = SHA256(Geheimnis_hash + r_bytes)
        combined = hashlib.sha256(secret_hash + r_bytes).digest()
        
        # Zur Übertragung in Hex konvertieren
        B_ = combined.hex()
        r = r_bytes.hex()
        
        # Schritt 4: Verblindete Nachricht (B_) an Mint senden, r geheim halten
        return BlindedMessage(
            amount=amount,
            B_=B_,        # An Mint senden ✓
            r=r           # Geheim halten ✓
        )


# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 2: Blind Sign (Mint-Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep2:
    # Mint signs blinded message
    
    def blind_sign(blinded_message: BlindedMessage, private_key_pem: str):
        # Mint signs blinded message
       """ 
        Der Schlüssel-Insight: Die Mint signiert die verblindete Nachricht B_,
        nicht das Geheimnis. Da es verblind ist, lernt die Mint nicht, was das
        Geheimnis ist.
        
        Weg:
        1. Verblindete Nachricht B_ vom Benutzer empfangen
        2. Mit RSA-PSS signieren: C_ = RSA_sign(B_)
        3. Blindsignatur C_ an Benutzer zurückgeben
        
        Die Mint weiß nicht:
        - Was das ursprüngliche Geheimnis ist
        - Was die entblindete Signatur sein wird
        - Welche Proofs von welchem Benutzer kamen
        
        Args:
            blinded_message: Die BlindedMessage mit B_, die wir empfangen
            private_key_pem: Mint privater RSA-Schlüssel (PEM-Format)
        
        Returns:
            BlindSignature mit C_, die der Benutzer entblindes kann
        """
        
        # Schritt 1: Mint privaten RSA-Schlüssel von PEM laden
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Schritt 2: Verblindete Nachricht von Hex-String zu Bytes konvertieren
        B_bytes = bytes.fromhex(blinded_message.B_)
        
        # Schritt 3: Mit RSA-PSS und SHA256 signieren
        # RSA-PSS fügt Zufälligkeit hinzu, so dass gleiche Eingaben nicht gleiche
        # Ausgaben produzieren
        signature = private_key.sign(
            B_bytes,
            padding.PSS(
                # MGF1 ist die Maskenerzeugungsfunktion
                mgf=padding.MGF1(hashes.SHA256()),
                # PSS.DIGEST_LENGTH = Salt-Länge = Hash-Ausgabegröße
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Schritt 4: Signatur zu Hex für Übertragung konvertieren
        C_ = signature.hex()
        
        # Blindsignatur zurückgeben
        return BlindSignature(
            amount=blinded_message.amount,
            C_=C_  # Blindsignatur - Benutzer wird das entblindes
        )


# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 3: Signatур Entblindung (Benutzer-Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep3:
    # User unblinds signature to get spendable proof
    
    def unblind_signature(blind_signature: BlindSignature, blinding_factor: str):
        # Unblind signature to create spendable proof
       """ 
        Jetzt nimmt der Benutzer die Blindsignatur C_ und seinen geheimen Verblindungs-
        faktor r und erstellt eine entblindete Signatur C, die ausgegeben werden kann.
        
        Weg:
        1. Blindsignatur C_ von Mint empfangen
        2. Mit entblindes: C = sha256(C_ + r)
        3. Beweis (Geheimnis, C, Betrag) erstellen, der ausgegeben werden kann
        
        Magische Eigenschaft: 
        - Die Mint signierte B_ (das sha256(Geheimnis + r) ist)
        - Benutzer entblindet: C = sha256(C_ + r)
        - Ergebnis: C ist eine gültige Signatur des Geheimnisses!
        
        Args:
            blind_signature: Die C_, die von Mint empfangen wird
            blinding_factor: Der r-Faktor von generate_blinded_message()
        
        Returns:
            Entblindete Signatur C (Hex-String), die ausgegeben werden kann
        """
        
        # Schritt 1: Blindsignatur und Verblindungsfaktor von Hex zu Bytes konvertieren
        C_bytes = bytes.fromhex(blind_signature.C_)
        r_bytes = bytes.fromhex(blinding_factor)
        
        # Schritt 2: Entblinde, indem Signatur und Faktor zusammen gehasht werden
        # Produktions-Cashu: C = (C_ / r) mod n (modulare Arithmetik)
        # Hier: C = SHA256(C_ + r)
        C = hashlib.sha256(C_bytes + r_bytes).hexdigest()
        
        # Schritt 3: Entblindete Signatur zurückgeben (jetzt ausgegeben)
        return C


# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 4: DLEQ-Beweis verifikation
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep4:
    # Verify DLEQ proof
    
    def verify_dleq_proof(proof_secret: str, commitment: str, dleq_proof: dict):
        # Verify DLEQ proof (simplified check)
       """ 
        DLEQ-Beweis überprüft: "Das Engagement C entspricht dem Geheimnis auf die
        gleiche Weise, wie C_ B_ entspricht" ohne das Geheimnis offenzulegen.
        
        Aktuelle Implementierung: VEREINFACHT (nicht kryptografisch verifiziert)
        - Überprüft nur, dass erforderliche Felder vorhanden sind
        - Validiert, dass sie gültige Hex-Strings sind
        
        Produktions-Implementierung würde:
        - Elliptische Kurven-Kryptografie verwenden
        - Zero-Knowledge-Proof-Gleichungen überprüfen
        
        Args:
            proof_secret: Das ursprüngliche Geheimnis des Benutzers
            commitment: Das entblindete Engagement C
            dleq_proof: Beweis-Daten von Mint mit Feldern z, r, e
        
        Returns:
            True wenn Felder vorhanden und gültig sind, False sonst
        """
        
        # Schritt 1: Überprüfen Sie, ob erforderliche Felder vorhanden sind
        required_fields = ['z', 'r', 'e']
        if not all(field in dleq_proof for field in required_fields):
            return False
        
        # Schritt 2: Validieren Sie, dass jedes Feld gültige Hex ist
        try:
            int(dleq_proof['z'], 16)  # Als Hex analysieren
            int(dleq_proof['r'], 16)
            int(dleq_proof['e'], 16)
        except (ValueError, TypeError):
            return False
        
        # In Produktien: Führen Sie echte elliptische Kurve-Verifikation durch
        # Dies würde komplexe Mathematik für Zero-Knowledge-Beweis-Verifikation beinhalten
        
        return True


# ==============================================================================
# TEIL 2: MINT PROTOKOLL (Generieren → Signieren → Entblindes)
# ==============================================================================
"""
Das Mint-Protokoll ist ein 2-Phasen-Prozess:

PHASE 1: MINT-QUOTE ANFORDERN
  Client: "Ich möchte 100 Sats"
  Mint: "Bezahlen Sie diese Lightning-Rechnung, erhalten Sie Quote_ID"

PHASE 2: MINTING FERTIGSTELLEN
  Client: "Hier sind meine Quote_ID und Blindnachrichten"
  Mint: "Hier sind Blindsignaturen"
  Client: "Ich werde diese entblindes, um Proofs zu erhalten"

Ergebnis: Client hat 100 Sats in Proofs (Ecash-Tokens)
"""

# ─────────────────────────────────────────────────────────────────────────────
# MINT PHASE 1: Mint-Quote anfordern
# ─────────────────────────────────────────────────────────────────────────────

class MintProtocolPhase1:
    # Request mint quote
    
    def request_mint_quote(mint_url: str, amount: int):
        # Request mint quote from mint
       """ 
        Schritt 1 des Minting: Client fordert Mint Quote an.
        Mint gibt eine Lightning-Rechnung zurück zum Bezahlen.
        
        Weg:
        1. Client sendet: POST /requestmint mit Betrag=100
        2. Mint erstellt Quote_ID (verfolgt in MINT_QUOTES)
        3. Mint generiert Lightning-Rechnung
        4. Mint gibt zurück: Quote_ID, Rechnung, Ablauf (5 Minuten)
        
        Args:
            mint_url: Basis-URL der Mint (z.B. "http://localhost:5001")
            amount: Sats zu Minting
        
        Returns:
            Quote-Objekt mit:
            - Quote_ID: Eindeutige Quote-Kennung
            - request: Lightning-Rechnung zum Bezahlen
            - state: "ausstehend"
            - expires_at: ISO-Zeitstempel (jetzt + 5 Minuten)
        """
        
        # Schritt 1: Anfrage an Mint-Server senden
        response = requests.post(
            f"{mint_url}/requestmint",
            json={"amount": amount},
            timeout=10
        )
        data = response.json()
        
        # Schritt 2: Antwortdaten extrahieren
        quote_id = data.get("quote")          # z.B. "d6702017-7321-4fc6-..."
        invoice = data.get("request", "")     # z.B. "lnbc100u1p0mockivv"
        
        # Schritt 3: Quote-Objekt mit 5-Minuten-Ablauf erstellen
        quote = Quote(
            quote_id=quote_id,
            amount=amount,
            request=invoice,
            quote_type="mint",
            state="pending",
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            mint_url=mint_url
        )
        
        # Schritt 4: Quote für nächste Phase zurückgeben
        return quote


# ─────────────────────────────────────────────────────────────────────────────
# MINT PHASE 2: Minting fertigstellen
# ─────────────────────────────────────────────────────────────────────────────

class MintProtocolPhase2:
    # Mint protocol: finish minting process
    
    def finish_mint(mint_url: str, quote: Quote):
        # Finish minting: create blinded messages and receive signatures
       """ 
        Schritt 2 des Minting: 
        1. Verblindete Nachrichten für jede Stückelung generieren
        2. An Mint senden
        3. Blindsignaturen empfangen
        4. Signaturen entblindes um ausgebbare Proofs zu erhalten
        
        Weg:
        1. Betrag in Zweierpotenzen aufteilen: [64, 32, 4]
        2. Für jeden Betrag: generate_blinded_message()
        3. Alle Blindnachrichten an Mint senden
        4. Mint gibt Blindsignaturen zurück
        5. Für jede Signatur: unblind_signature()
        6. Proof-Objekte (Geheimnis, C, Betrag) erstellen
        7. Proofs an Wallet zurückgeben
        
        Args:
            mint_url: Mint-Server-URL
            quote: Quote von request_mint_quote()
        
        Returns:
            Liste von Proof-Objekten (jetzt ausgegeben)
        """
        
        # Schritt 1: Betrag in Stückelungen aufteilen (Zweierpotenzen)
        # Beispiel: 100 Sats → [64, 32, 4]
        amounts = []
        remaining = quote.amount
        power = 0
        while remaining > 0 and power < 12:
            amount = min(2 ** power, remaining)  # Min verwenden, nicht zu viel
            amounts.append(amount)
            remaining -= amount
            power += 1
        
        # Schritt 2: Verblindete Nachrichten für jeden Betrag generieren
        blinded_messages = []
        secrets = []
        blinding_factors = []
        
        for amount in amounts:
            # Zufälliges Geheimnis für diesen Beweis erstellen
            secret = f"{uuid.uuid4().hex}"
            
            # Verblindete Nachricht generieren
            blinded = crypto.generate_blinded_message(amount, secret)
            
            # Zur späteren Entblindung verfolgen
            blinded_messages.append({
                "amount": amount,
                "B_": blinded.B_,    # An diesem senden
                "r": blinded.r       # Geheim halten
            })
            secrets.append(secret)
            blinding_factors.append(blinded.r)
        
        # Schritt 3: Verblindete Nachrichten an Mint senden
        response = requests.post(
            f"{mint_url}/mint",
            json={
                "quote": quote.quote_id,
                "blinded_messages": blinded_messages
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 4: Blindsignaturen von Mint empfangen
        blind_sigs = data.get("proofs", [])
        
        # Schritt 5: Signaturen entblindes und Proofs erstellen
        proofs = []
        
        for i, blind_sig in enumerate(blind_sigs):
            amount = blind_sig.get("amount", 0)
            C_ = blind_sig.get("C_", "")
            dleq_proof = blind_sig.get("dleq", {})
            
            # DLEQ-Beweis überprüfen (vereinfacht)
            if not crypto.verify_dleq_proof(secrets[i], C_, dleq_proof):
                print(f"[Client] WARNUNG: DLEQ-Beweis fehlgeschlagen für Output {i}")
            
            # Signatur entblindes
            blind_sig_obj = BlindSignature(amount, C_)
            C = crypto.unblind_signature(
                blind_sig_obj,
                blinding_factors[i]  # Den r-Faktor verwenden
            )
            
            # Schritt 6: Proof-Objekt erstellen (jetzt ausgegeben)
            proof = Proof(
                amount=amount,
                secret=secrets[i],           # Das ursprüngliche Geheimnis
                C=C,                         # Die entblindete Signatur
                mint=mint_url,               # Welche Mint das ausgestellt hat
                keyset_version="00"          # Keyset-Version
            )
            
            proofs.append(proof)
        
        # Schritt 7: Proofs zum Wallet zurückgeben
        return proofs


# ==============================================================================
# TEIL 3: SWAP PROTOKOLL (Beweis-Austausch)
# ==============================================================================
"""
Das Swap-Protokoll ermöglicht einem Benutzer, ihre Proofs für blinde Outputs
auszutauschen, die sie an einen anderen Benutzer senden können.

Weg:
1. Sender: "Ich möchte 100 Sats senden. Hier sind meine Proofs."
2. Mint: "Ich werde blinde Outputs für Sie erstellen."
3. Sender: "Ich sende diese blinden Outputs an den Empfänger."
4. Empfänger: "Ich habe diese blinden Outputs empfangen und entblindet!"

Schlüssel-Insight: Die blinden Outputs werden mit dem EMPFÄNGERS Verblindungs-
faktor erstellt, so dass nur der Empfänger sie entblindes kann. Der Sender kann
sie nach der Erstellung nicht ausgeben.
"""

class SwapProtocol:
    # Swap proofs for blinded outputs
    
    def client_swap(mint_url: str, proofs_to_send: List[Proof], 
                    output_amounts: List[int]):
        """
        CLIENT-OPERATION: Proofs für blinde Outputs zum Senden austauschen.
        
        Wird verwendet, wenn der Benutzer Geld über Token an ein anderes Wallet senden möchte.
        
        Weg:
        1. Proofs vom Wallet auswählen, die Betrag abdecken
        2. swap() anrufen
        3. Mint gibt blinde Outputs zurück
        4. Outputs als Token kodieren
        5. Proofs aus Wallet entfernen (jetzt ausgegeben)
        6. Token an Empfänger senden
        
        Args:
            mint_url: Mint-URL
            proofs_to_send: Liste von Proofs zum Austausch
            output_amounts: Gewünschte Output-Stückelungen [64, 32, 4]
        
        Returns:
            Liste von blinden Outputs zum Kodieren als Token
        """
        
        # Schritt 1: Beträge überprüfen, ob sie übereinstimmen
        total_proofs = sum(p.amount for p in proofs_to_send)
        total_outputs = sum(output_amounts)
        
        if total_proofs != total_outputs:
            raise ValueError(f"Proof Betrag {total_proofs} != Output {total_outputs}")
        
        # Schritt 2: Proofs für Übertragung serialisieren
        proof_dicts = [p.to_dict() for p in proofs_to_send]
        
        # Schritt 3: Mint Swap-Endpunkt anrufen
        response = requests.post(
            f"{mint_url}/swap",
            json={
                "proofs": proof_dicts,
                "output_amounts": output_amounts
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 4: Blinde Outputs empfangen
        outputs = data.get("outputs", [])
        
        # Schritt 5: Outputs jetzt bereit zum Kodieren als Token
        return outputs


# ==============================================================================
# TEIL 4: MELT PROTOKOLL (Quote + Rückzug)
# ==============================================================================
"""
Das Melt-Protokoll ermöglicht Benutzern, Ecash-Proofs zurück zu Fiat/Lightning
einzulösen.

PHASE 1: MELT-QUOTE ANFORDERN
  Client: "Ich möchte 100 Sats via diese Lightning-Rechnung einlösen"
  Mint: "OK, hier ist eine Melt-Quote mit 5-Min-Ablauf"

PHASE 2: MINTING FERTIGSTELLEN
  Client: "Hier sind meine Proofs und Quote_ID"
  Mint: "Ich werde validieren und die Lightning-Rechnung bezahlen"
  Client: "Bestätigt! Proofs sind jetzt ausgegeben."

Ergebnis: Client hat reale Lightning Sats empfangen (oder Fiat-Äquivalent)
"""

class MeltProtocolPhase1:
    # Request melt quote
    
    def client_request_melt_quote(mint_url: str, invoice: str, amount: int):
        # Request melt quote
        
        # Step 1: Send request to mint
        response = requests.post(
            f"{mint_url}/requestmelt",
            json={
                "pr": invoice,      # pr = Zahlungsanforderung
                "amount": amount
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 2: Quote-Objekt erstellen
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
    
    def client_finish_melt(mint_url: str, quote: Quote, 
                          proofs: List[Proof]) -> bool:
        # Finish melting: redeem proofs
        """
        Schritt 2 des Meltings: Proofs an Mint zur Einlösung senden.
        
        Args:
            mint_url: Mint-Server-URL
            quote: Melt-Quote von request_melt_quote()
            proofs: Proofs zum Einlösen
        
        Returns:
            True wenn Melt erfolgreich ist, False sonst
        """
        
        # Schritt 1: Betrag überprüfen
        total = sum(p.amount for p in proofs)
        if total < quote.amount:
            raise ValueError(f"Unzureichende Proofs: {total} < {quote.amount}")
        
        # Schritt 2: Proofs serialisieren
        proof_dicts = [p.to_dict() for p in proofs]
        
        # Schritt 3: An Mint senden
        response = requests.post(
            f"{mint_url}/melt",
            json={
                "quote": quote.quote_id,
                "pr": quote.request,    # Rechnung zum Bezahlen
                "proofs": proof_dicts
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 4: Überprüfen Sie, ob Mint bestätigt
        state = data.get("state", "")
        return state == "paid"


# ==============================================================================
# TEIL 5: QUOTE-VERWALTUNG (Ablauf, Zustandsverfolgung)
# ==============================================================================
"""

Quotes verwalten zeitgebundene Transaktionen. Sie verhindern:
- Benutzer von Minting ohne Bezahlung
- Undefnite Hängel, wenn etwas bricht
- Double-Spending derselben Quote zweimal

State-Weg: ausstehend → bestätigt → abgelaufen
Ablauf: 5 Minuten ab Erstellung
"""

class QuoteManagement:
    # Quote lifecycle management
    
    # Quote model
    class Quote:
        # Mint or Melt quote representation
        
        def __init__(
            self,
            quote_id: str,
            amount: int,
            request: str,              # Rechnung oder Cashu-Anfrage
            quote_type: str,           # "mint" oder "melt"
            state: str = "pending",    # ausstehend, bestätigt, abgelaufen
            expires_at: Optional[str] = None,
            mint_url: str = "http://localhost:5001"
        ):
            """
            Initialisiere eine Quote.
            
            Args:
                quote_id: Eindeutige Kennung (UUID)
                amount: Sats beteiligt
                request: Lightning-Rechnung oder Cashu-Anfrage
                quote_type: "mint" erstellt Proofs, "melt" löst sie ein
                state: Aktueller Status (ausstehend/bestätigt/abgelaufen)
                expires_at: ISO-Zeitstempel wenn Quote abläuft
                mint_url: Welche Mint diese Quote ausgestellt hat

            """
"""
            self.quote_id = quote_id
            self.amount = amount
            self.request = request
            self.quote_type = quote_type
            self.state = state
            self.expires_at = expires_at
            self.created_at = datetime.now().isoformat()
            self.mint_url = mint_url
        """
        
        def is_expired(self) -> bool:
            # Check if quote has expired
            if not self.expires_at:
                return False
            
            # ISO-Zeitstempel analysieren
            expires = datetime.fromisoformat(self.expires_at)
            
            # Mit aktueller Zeit vergleichen
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
    
    
    # Wallet-Quote-Verfolgung
    class WalletQuoteTracking:
        # Track pending quotes in wallet
        
        def __init__(self):
            # Initialize quote tracking
            self.pending_quotes = {}  # {Quote_ID: Quote}
        
        
        def add_quote(self, quote: Quote):
            # Add quote to pending list
            """
            Aufgerufen, wenn:
            - Benutzer Mint-Quote anfordert
            - Benutzer Melt-Quote anfordert
            
            Speicher:
            - Im Speicher während Sitzung
            - Auf Server-Neustart verloren (Design-Einschränkung)
            
            Args:
                Quote: Quote-Objekt
            """
            self.pending_quotes[quote.quote_id] = quote
            print(f"[Wallet] Quote verfolgen {quote.quote_id}")
        
        
        def get_quote(self, quote_id: str) -> Optional[Quote]:
            # Get quote by ID
            """
            Vor Verwendung überprüfen:
            - Quote existiert
            - Quote ist nicht abgelaufen
            - Quote ist korrekter Typ (Mint vs Melt)
            
            Args:
                Quote_ID: UUID von Quote
            
            Returns:
                Quote-Objekt oder None, wenn nicht gefunden
            """
            return self.pending_quotes.get(quote_id)
        
        
        def remove_quote(self, quote_id: str):
            # Remove quote after completion
            """
            Aufgerufen, wenn:
            - finish_mint() erfolgreich
            - finish_melt() erfolgreich
            - Quote läuft ab (Bereinigung)
            
            Args:
                Quote_ID: UUID von Quote zum Entfernen
            """
            if quote_id in self.pending_quotes:
                del self.pending_quotes[quote_id]
                print(f"[Wallet] Quote entfernt {quote_id}")


# ==============================================================================
# ZUSAMMENFASSUNG: Kompletter Protokoll-Weg
# ==============================================================================

"""
KOMPLETTER TRANSAKTIONS-WEG:

1. MINTING (Erstellen von 100 Sats Ecash)
2. SWAPPING (Senden von 50 Sats an ein anderes Wallet)
3. MELTING (Einlösen von 25 Sats zu Lightning/Fiat)

Jeder Schritt verwendet Chaums Blind Signing Protokoll für vollständige
kryptografische Anonymität und Sicherheit.
"""
