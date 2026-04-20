from flask import Flask, request, jsonify, send_from_directory, send_file  # type: ignore
import os
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.wallet import WalletService
from core.mint import MintService
from client.wallet import WalletClient
from core.cashu import CashuClient
from storage.encrypted import StorageService
from core.price import get_bitcoin_price, get_historical_bitcoin_price

from utils.token import encode_token, decode_token
from models.proof import Proof

app = Flask(__name__, static_folder="static")

# Add PWA headers to all responses
@app.after_request
# Add cache and security headers
def add_header(response):
    # Prevent caching of HTML
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    # Cache static assets briefly during development
    elif any(ext in response.headers.get('Content-Type', '') for ext in ['css', 'javascript']):
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    elif any(ext in response.headers.get('Content-Type', '') for ext in ['image', 'font']):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    
    # PWA headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()'
    
    return response

# Get password from environment variable, with fallback for development
PASSWORD = os.getenv("WALLET_PASSWORD", "development-password-only")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WALLET_DATABASE = os.getenv("WALLET_DATABASE", "wallet.dat")
WALLET_PATH = os.path.join(BASE_DIR, WALLET_DATABASE)

storage = StorageService(PASSWORD, WALLET_PATH)
wallet = WalletService(storage)
mint_service = MintService()


# Frontend routes
@app.route("/")
# Serve main frontend HTML
def serve_frontend():
    return send_from_directory("static", "index.html")


@app.route("/static/manifest.json")
def serve_manifest():
    # Serve PWA manifest
    response = send_from_directory("static", "manifest.json")
    response.headers['Content-Type'] = 'application/manifest+json'
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


@app.route("/static/sw.js")
def serve_service_worker():
    # Serve service worker
    response = send_from_directory("static", "sw.js")
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@app.route("/offline.html")
def offline_page():
    # Serve offline fallback page
    return send_from_directory("static", "index.html")


# API endpoints
@app.route("/api/mints")
# Get list of available mints
def get_mints():
    return jsonify({"mints": mint_service.get_mints()})


@app.route("/api/mints/add", methods=["POST"])
def add_mint():
    # Add a new mint by URL
    data = request.json
    url = data.get("url")
    name = data.get("name")
    
    if not url:
        return jsonify({"error": "URL required"}), 400
    
    mint_id = mint_service.add_mint_from_url(url, name)
    return jsonify({
        "status": "ok",
        "mint_id": mint_id,
        "mints": mint_service.get_mints()
    })


@app.route("/api/wallet/balance")
# Get wallet balance for mint
def get_balance():
    mint = request.args.get("mint")
    return jsonify({"balance": wallet.get_balance(mint)})


@app.route("/api/receive", methods=["POST"])
# Receive Cashu token and add proofs to wallet
def receive():
    data = request.json
    token = data.get("token")

    proofs = decode_token(token)
    wallet.add_proofs(proofs)

    amount = sum(p.amount for p in proofs)
    mint = proofs[0].mint if proofs else "unknown"

    wallet.add_transaction("receive", amount, mint)

    return jsonify({
        "status": "ok",
        "received": amount
    })


@app.route("/api/send", methods=["POST"])
def send():
    # Send sats by performing Cashu swap
    data = request.json
    amount = int(data["amount"])
    mint_url = data.get("mint", "http://localhost:5001")

    try:
        # Find proofs from the target mint
        matching = [p for p in wallet.proofs if p.mint == mint_url]
        if not matching:
            matching = wallet.proofs[:]
        
        if not matching:
            return jsonify({"error": "No proofs available"}), 400

        # Select proofs covering the amount
        selected = []
        total = 0
        for p in matching:
            selected.append(p)
            total += p.amount
            if total >= amount:
                break

        if total < amount:
            return jsonify({
                "error": f"Not enough balance. Have {total}, need {amount}"
            }), 400

        # Determine outputs (powers of 2 for change)
        output_amounts = []
        remaining = total
        power = 0
        while remaining > 0 and power < 12:
            out_amount = min(2 ** power, remaining)
            output_amounts.append(out_amount)
            remaining -= out_amount
            power += 1

        # Connect to mint and perform swap
        client = CashuClient(mint_url)
        
        # Fetch mint's keysets first
        client.fetch_keysets()
        
        # Perform swap: proofs → blinded outputs
        swap_outputs = client.swap(selected, output_amounts)
        
        # The swap outputs are blinded and can only be unblinded by the recipient
        # Encode them as a token for sharing
        token_output = {
            "mint": mint_url,
            "outputs": swap_outputs  # Blinded outputs
        }
        
        import json
        import base64
        token_json = json.dumps(token_output)
        token_b64 = base64.urlsafe_b64encode(token_json.encode()).decode()
        token = f"cashuA{token_b64}"

        # Remove selected proofs from wallet (they were swapped)
        wallet.remove_proofs(selected)
        
        # Record transaction
        wallet.add_transaction("send", amount, mint_url)

        print(f"[Send] Swapped {total} sats for {len(swap_outputs)} blinded outputs")

        return jsonify({
            "token": token,
            "amount": total,
            "mint": mint_url
        })

    except Exception as e:
        print(f"[Send Error] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@app.route("/api/mint/request", methods=["POST"])
def mint_request():
    # Request mint quote from mint
    data = request.json
    amount = int(data.get("amount", 0))
    mint_url = data.get("mint", "http://localhost:5001")
    
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    
    try:
        client = CashuClient(mint_url)
        quote = client.request_mint_quote(amount)
        wallet.add_quote(quote)
        
        return jsonify({
            "quote_id": quote.quote_id,
            "request": quote.request,
            "state": "pending"
        })
    except Exception as e:
        print(f"[Mint Request Error] {str(e)}")
        return jsonify({"error": str(e)}), 400


@app.route("/api/mint/finish", methods=["POST"])
def mint_finish():
    # Finish minting: exchange blinded messages for proofs
    data = request.json
    quote_id = data.get("quote_id")
    
    if not quote_id:
        return jsonify({"error": "quote_id required"}), 400
    
    try:
        quote = wallet.get_quote(quote_id)
        if not quote:
            return jsonify({"error": "Quote not found"}), 400
        
        if quote.is_expired():
            return jsonify({"error": "Quote expired"}), 400
        
        client = CashuClient(quote.mint_url)
        proofs = client.finish_mint(quote)
        
        # Add proofs to wallet
        wallet.add_proofs(proofs)
        wallet.remove_quote(quote_id)
        
        wallet.add_transaction("mint", quote.amount, quote.request)
        
        print(f"[Mint] Completed: received {len(proofs)} proofs for {quote.amount} sats")
        
        return jsonify({
            "status": "ok",
            "proofs": len(proofs),
            "amount": quote.amount
        })
    except Exception as e:
        print(f"[Mint Finish Error] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@app.route("/api/melt/request", methods=["POST"])
def melt_request():
    # Request melt quote to redeem proofs as Lightning
    data = request.json
    amount = int(data.get("amount", 0))
    invoice = data.get("invoice", "")
    mint_url = data.get("mint", "http://localhost:5001")
    
    if amount <= 0 or not invoice:
        return jsonify({"error": "Invalid amount or invoice"}), 400
    
    try:
        client = CashuClient(mint_url)
        quote = client.request_melt_quote(invoice, amount)
        wallet.add_quote(quote)
        
        return jsonify({
            "quote_id": quote.quote_id,
            "state": "pending",
            "expires_at": quote.expires_at
        })
    except Exception as e:
        print(f"[Melt Request Error] {str(e)}")
        return jsonify({"error": str(e)}), 400


@app.route("/api/melt/finish", methods=["POST"])
def melt_finish():
    # Finish melting: redeem proofs for Lightning payout
    data = request.json
    quote_id = data.get("quote_id")
    
    if not quote_id:
        return jsonify({"error": "quote_id required"}), 400
    
    try:
        quote = wallet.get_quote(quote_id)
        if not quote:
            return jsonify({"error": "Quote not found"}), 400
        
        if quote.is_expired():
            return jsonify({"error": "Quote expired"}), 400
        
        # Find proofs to redeem
        matching = [p for p in wallet.proofs if p.amount <= quote.amount]
        selected = []
        total = 0
        for p in matching:
            selected.append(p)
            total += p.amount
            if total >= quote.amount:
                break
        
        if total < quote.amount:
            return jsonify({
                "error": f"Insufficient proofs: {total} available, {quote.amount} needed"
            }), 400
        
        client = CashuClient(quote.mint_url)
        success = client.finish_melt(quote, selected)
        
        if success:
            wallet.remove_proofs(selected)
            wallet.remove_quote(quote_id)
            wallet.add_transaction("melt", total, quote.request)
            
            print(f"[Melt] Completed: redeemed {total} sats via Lightning")
            
            return jsonify({
                "status": "ok",
                "amount": total
            })
        else:
            return jsonify({"error": "Melt failed on server"}), 400
            
    except Exception as e:
        print(f"[Melt Finish Error] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@app.route("/api/transactions")
# Get transaction history
def transactions():
    return jsonify({"transactions": wallet.get_transactions()})


@app.route("/api/btc-price")
# Get current Bitcoin price
def btc_price():
    try:
        prices = get_bitcoin_price()
        if prices:
            return jsonify(prices)
        return jsonify({"error": "price unavailable", "usd": 62000, "eur": 57000}), 200
    except Exception as e:
        print(f"[API Error] btc-price endpoint failed: {str(e)}")
        # Return fallback prices instead of 500 error
        return jsonify({"usd": 62000, "eur": 57000}), 200


@app.route("/api/btc-price-history")
def btc_price_history():
    # Get Bitcoin price history for last 7 days
    try:
        days = request.args.get("days", 7, type=int)
        history = get_historical_bitcoin_price(days)
        if history:
            return jsonify({"prices": history})
        # Return empty if no data available
        return jsonify({"prices": []}), 200
    except Exception as e:
        print(f"[API Error] btc-price-history endpoint failed: {str(e)}")
        # Return empty array instead of 500 error
        return jsonify({"prices": []}), 200


@app.route("/api/debug/proofs")
def debug_proofs():
    # Debug endpoint to view wallet proofs
    proofs_info = []
    for p in wallet.proofs:
        proofs_info.append({
            "amount": p.amount,
            "secret": p.secret[:16] + "..." if len(p.secret) > 16 else p.secret,
            "mint": p.mint,
            "keyset": p.keyset_version
        })
    return jsonify({
        "total_balance": wallet.get_balance(),
        "total_proofs": len(wallet.proofs),
        "proofs": proofs_info
    })


@app.route("/api/health")
# Health check endpoint
def health():
    return {"status": "running"}


if __name__ == "__main__":
    app.run(debug=True, port=8000)