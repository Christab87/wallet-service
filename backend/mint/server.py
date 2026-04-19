"""
Mock Cashu Mint Server (Port 5001)

Simulates a real Cashu mint for local testing.
Implements full Cashu protocol:
- /keys: Return signing keyset
- /requestmint: Create mint quote
- /mint: Finish minting (blind sign proofs)
- /requestmelt: Create melt quote  
- /melt: Redeem proofs for Lightning
- /swap: Exchange proofs for blinded outputs
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import os
import json
import uuid
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crypto.blind_signing import BlindSignature, BlindedMessage
from crypto import crypto

app = Flask(__name__)

# Mint state
MINT_ID = "http://localhost:5001"
KEYSET_VERSION = "00"
MINT_PRIVATE_KEY = None
MINT_PUBLIC_KEY = None

# Quotes in flight
MINT_QUOTES = {}  # {quote_id: {request: ..., proofs: [...], expires_at: ...}}
MELT_QUOTES = {}  # {quote_id: {amount, invoice, expires_at, ...}}

# Storage for minted proofs (for validation)
VALID_PROOFS = {}  # {proof_C: {amount, keyset_version, created_at}}


def init_mint():
    # Initialize mint keyset
    global MINT_PRIVATE_KEY, MINT_PUBLIC_KEY
    
    pub, priv = crypto.generate_keyset()
    MINT_PUBLIC_KEY = pub
    MINT_PRIVATE_KEY = priv
    print(f"[Mint] Initialized with keyset version {KEYSET_VERSION}")


@app.route("/keys", methods=["GET"])
def get_keys():
    # Return mint's public keys for verification
    return jsonify({
        "keysets": [
            {
                "id": KEYSET_VERSION,
                "unit": "sat",
                "active": True,
                "public_keys": {
                    "1": MINT_PUBLIC_KEY,
                    "2": MINT_PUBLIC_KEY,
                    "4": MINT_PUBLIC_KEY,
                    "8": MINT_PUBLIC_KEY,
                    "16": MINT_PUBLIC_KEY,
                    "32": MINT_PUBLIC_KEY,
                    "64": MINT_PUBLIC_KEY,
                    "128": MINT_PUBLIC_KEY,
                    "256": MINT_PUBLIC_KEY,
                    "512": MINT_PUBLIC_KEY,
                    "1024": MINT_PUBLIC_KEY,
                    "2048": MINT_PUBLIC_KEY,
                }
            }
        ]
    })


@app.route("/requestmint", methods=["POST"])
def request_mint():
    # Request mint quote
    data = request.json
    amount = int(data.get("amount", 0))
    
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    
    quote_id = str(uuid.uuid4())
    
    # In production, this would generate a real Lightning invoice
    # For testing, we'll just create a fake invoice
    invoice = f"lnbc{amount}u1p0mockivv"
    
    MINT_QUOTES[quote_id] = {
        "amount": amount,
        "invoice": invoice,
        "state": "pending",
        "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    print(f"[Mint] Created mint quote {quote_id} for {amount} sats")
    
    return jsonify({
        "quote": quote_id,
        "request": invoice,
        "state": "unpaid"
    })


@app.route("/mint", methods=["POST"])
def mint():
    # Finish minting: blind sign proofs
    data = request.json
    quote_id = data.get("quote")
    blinded_messages = data.get("blinded_messages", [])
    
    # Check quote exists and is valid
    if quote_id not in MINT_QUOTES:
        return jsonify({"error": "Quote not found"}), 400
    
    quote = MINT_QUOTES[quote_id]
    
    # In production, verify Lightning invoice is paid
    # For testing, auto-pay
    quote["state"] = "paid"
    
    # Blind sign each message
    proofs = []
    for msg in blinded_messages:
        try:
            blinded = BlindedMessage(
                amount=int(msg["amount"]),
                B_=msg["B_"],
                r=msg["r"]
            )
            
            # Mint blindly signs
            if not MINT_PRIVATE_KEY:
                raise RuntimeError("Mint not initialized")
            blind_sig = crypto.blind_sign(blinded, MINT_PRIVATE_KEY)
            
            # Create DLEQ proof (simplified)
            dleq = {
                "z": os.urandom(32).hex(),
                "r": os.urandom(32).hex(),
                "e": os.urandom(32).hex()
            }
            
            proof_dict = {
                "amount": blind_sig.amount,
                "C_": blind_sig.C_,
                "dleq": dleq
            }
            
            proofs.append(proof_dict)
            
        except Exception as e:
            return jsonify({"error": f"Failed to sign: {str(e)}"}), 400
    
    quote["proofs"] = proofs
    quote["state"] = "confirmed"
    
    print(f"[Mint] Minted {len(proofs)} proofs for quote {quote_id}")
    
    return jsonify({
        "proofs": proofs
    })


@app.route("/requestmelt", methods=["POST"])
def request_melt():
    # Request melt quote
    data = request.json
    invoice = data.get("pr", "")
    amount = data.get("amount", 0)
    
    if not invoice:
        return jsonify({"error": "Invoice required"}), 400
    
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    
    quote_id = str(uuid.uuid4())
    
    MELT_QUOTES[quote_id] = {
        "amount": amount,
        "invoice": invoice,
        "state": "pending",
        "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    print(f"[Mint] Created melt quote {quote_id} for {amount} sats")
    
    return jsonify({
        "quote": quote_id,
        "amount": amount,
        "state": "pending"
    })


@app.route("/melt", methods=["POST"])
def melt():
    # Finish melting: redeem proofs for Lightning payout
    data = request.json
    quote_id = data.get("quote")
    proofs = data.get("proofs", [])
    invoice = data.get("pr", "")
    
    if quote_id not in MELT_QUOTES:
        return jsonify({"error": "Melt quote not found"}), 400
    
    melt_quote = MELT_QUOTES[quote_id]
    
    # Verify proofs (simplified - in production, verify they're valid and not double-spent)
    total_amount = sum(int(p.get("amount", 0)) for p in proofs)
    
    if total_amount < melt_quote["amount"]:
        return jsonify({"error": "Insufficient proof amount"}), 400
    
    # Mark quote as paid (in production, actually pay via Lightning)
    melt_quote["state"] = "confirmed"
    melt_quote["paid_amount"] = total_amount
    
    print(f"[Mint] Melted {len(proofs)} proofs for {total_amount} sats (quote {quote_id})")
    
    return jsonify({
        "state": "paid",
        "amount": total_amount
    })


@app.route("/swap", methods=["POST"])
def swap():
    # Swap proofs for blinded outputs to send
    data = request.json
    proofs = data.get("proofs", [])
    output_amounts = data.get("output_amounts", [])
    
    if not proofs or not output_amounts:
        return jsonify({"error": "Proofs and output amounts required"}), 400
    
    total_proof = sum(int(p.get("amount", 0)) for p in proofs)
    total_output = sum(output_amounts)
    
    if total_proof != total_output:
        return jsonify({
            "error": f"Proof amount {total_proof} != output amount {total_output}"
        }), 400
    
    # Create blind-signed outputs for each amount
    outputs = []
    for amount in output_amounts:
        # Create blinded message for this output
        output = crypto.create_swap_output(amount, "recipient_ephemeral_key")
        output["amount"] = amount
        
        # Mint signs it
        if not MINT_PRIVATE_KEY:
            raise RuntimeError("Mint not initialized")
        blinded = BlindedMessage(amount, output["B_"], output["r"])
        blind_sig = crypto.blind_sign(blinded, MINT_PRIVATE_KEY)
        
        # Create DLEQ proof
        dleq = {
            "z": os.urandom(32).hex(),
            "r": os.urandom(32).hex(),
            "e": os.urandom(32).hex()
        }
        
        outputs.append({
            "amount": amount,
            "B_": output["B_"],
            "C_": blind_sig.C_,
            "dleq": dleq
        })
    
    print(f"[Mint] Swapped {len(proofs)} proofs for {len(outputs)} outputs")
    
    return jsonify({
        "outputs": outputs
    })


@app.route("/health", methods=["GET"])
def health_check():
    # Health check endpoint
    return jsonify({
        "status": "ok",
        "mint_id": MINT_ID,
        "keyset_version": KEYSET_VERSION
    })


if __name__ == "__main__":
    init_mint()
    print("\n" + "="*50)
    print("🏦 Mock Cashu Mint Server running on port 5001")
    print("="*50 + "\n")
    app.run(host="localhost", port=5001, debug=True, use_reloader=False)
