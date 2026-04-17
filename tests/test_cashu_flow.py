#!/usr/bin/env python
"""
Full Cashu e-wallet flow test.

This script demonstrates a complete Cashu payment flow:
1. Mint new proofs (100 sats) using Lightning
2. Send proofs to another wallet via swap
3. Receive the blinded outputs
4. Melt proofs back to Lightning

Requires both servers running:
- Mint server: python backend/mint/server.py (port 5001)
- Wallet server: python backend/app.py (port 8000)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests # type: ignore
import json
import time
import logging
from models.cashu import Proof  # type: ignore

# Configure detailed logging focused on transactions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


MINT_URL = "http://localhost:5001"
WALLET_URL = "http://localhost:8000"

def test_mint_flow():
    """Test minting new proofs."""
    print("\n" + "="*60)
    print("TEST 1: MINT FLOW (100 sats)")
    print("="*60)
    
    # Step 1: Request mint quote
    print("\n[1] Requesting mint quote for 100 sats...")
    resp = requests.post(f"{WALLET_URL}/api/mint/request", json={
        "amount": 100,
        "mint": MINT_URL
    })
    if resp.status_code != 200:
        logger.error(f"Mint request failed: {resp.json()}")
        print(f"ERROR: {resp.json()}")
        return False
    
    data = resp.json()
    quote_id = data["quote_id"]
    invoice = data["request"]
    logger.info(f"[OK] Mint quote created | Quote ID: {quote_id}")
    print(f"    Quote ID: {quote_id}")
    print(f"    Invoice: {invoice[:50]}...")
    
    # Step 2: Finish mint (in production, invoice would be paid first)
    print("\n[2] Finishing mint (sending blinded messages)...")
    resp = requests.post(f"{WALLET_URL}/api/mint/finish", json={
        "quote_id": quote_id
    })
    if resp.status_code != 200:
        logger.error(f"Mint finish failed: {resp.json()}")
        print(f"ERROR: {resp.json()}")
        return False
    
    data = resp.json()
    amount = data['amount']
    proofs = data['proofs']
    
    # Handle proofs - could be a list or an integer count
    if isinstance(proofs, list):
        num_proofs = len(proofs)
        logger.info(f"[OK] Proofs minted | Amount: {amount} sats | # of Proofs: {num_proofs}")
        print(f"    Amount: {amount} sats")
        print(f"    Proofs received: {num_proofs}")
        for i, proof in enumerate(proofs[:3]):  # Show first 3 proofs
            print(f"      Proof {i+1}: {str(proof)[:60]}...")
        if num_proofs > 3:
            print(f"      ... and {num_proofs-3} more proofs")
    else:
        # proofs is likely a count (int)
        logger.info(f"[OK] Proofs minted | Amount: {amount} sats | # of Proofs: {proofs}")
        print(f"    Amount: {amount} sats")
        print(f"    Proofs received: {proofs}")
    
    # Check wallet balance
    print("\n[3] Checking wallet balance...")
    resp = requests.get(f"{WALLET_URL}/api/wallet/balance")
    balance = resp.json()["balance"]
    logger.info(f"[OK] Wallet balance: {balance} sats")
    print(f"    Wallet balance: {balance} sats")
    
    return True

def test_send_flow():
    """Test sending proofs via swap."""
    print("\n" + "="*60)
    print("TEST 2: SEND FLOW (50 sats via swap)")
    print("="*60)
    
    # Get current balance
    resp = requests.get(f"{WALLET_URL}/api/wallet/balance")
    initial_balance = resp.json()["balance"]
    logger.info(f"Send flow starting | Initial balance: {initial_balance} sats")
    print(f"\n[1] Starting balance: {initial_balance} sats")
    
    # Send 50 sats
    print("\n[2] Sending 50 sats...")
    resp = requests.post(f"{WALLET_URL}/api/send", json={
        "amount": 50,
        "mint": MINT_URL
    })
    if resp.status_code != 200:
        logger.error(f"Send failed: {resp.json()}")
        print(f"ERROR: {resp.json()}")
        return False
    
    data = resp.json()
    token = data["token"]
    mint = data['mint']
    logger.info(f"[OK] Payment token created | Token: {token[:40]}... | Mint: {mint}")
    print(f"    Transaction Token: {token[:60]}...")
    print(f"    Mint: {mint}")
    
    # Check balance after send
    resp = requests.get(f"{WALLET_URL}/api/wallet/balance")
    balance_after = resp.json()["balance"]
    logger.info(f"[OK] Balance updated | Before: {initial_balance} sats | After: {balance_after} sats | Spent: {initial_balance - balance_after} sats")
    
    print(f"\n[3] Balance after send: {balance_after} sats")
    print(f"    Amount spent: {initial_balance - balance_after} sats")
    
    return True

def test_melt_flow():
    """Test melting proofs to Lightning."""
    print("\n" + "="*60)
    print("TEST 3: MELT FLOW (Lightning redemption)")
    print("="*60)
    
    # Get current balance
    resp = requests.get(f"{WALLET_URL}/api/wallet/balance")
    balance = resp.json()["balance"]
    logger.info(f"Melt flow starting | Current balance: {balance} sats")
    print(f"\n[1] Current balance: {balance} sats")
    
    if balance < 10:
        logger.warning(f"Insufficient balance for melt (need 10 sats, have {balance})")
        print("    Not enough balance for melt test")
        return False
    
    # Create fake Lightning invoice
    test_invoice = "lnbc100u1pdummy"
    
    # Step 1: Request melt quote
    print(f"\n[2] Requesting melt quote for 10 sats...")
    resp = requests.post(f"{WALLET_URL}/api/melt/request", json={
        "amount": 10,
        "invoice": test_invoice,
        "mint": MINT_URL
    })
    if resp.status_code != 200:
        logger.error(f"Melt request failed: {resp.json()}")
        print(f"ERROR: {resp.json()}")
        return False
    
    data = resp.json()
    quote_id = data["quote_id"]
    expires_at = data.get('expires_at', 'N/A')
    logger.info(f"[OK] Melt quote created | Quote ID: {quote_id} | Expires: {expires_at}")
    print(f"    Quote ID: {quote_id}")
    print(f"    Expires: {expires_at}")
    
    # Step 2: Finish melt
    print("\n[3] Finishing melt (redeeming proofs)...")
    resp = requests.post(f"{WALLET_URL}/api/melt/finish", json={
        "quote_id": quote_id
    })
    if resp.status_code != 200:
        logger.error(f"Melt finish failed: {resp.json()}")
        print(f"ERROR: {resp.json()}")
        return False
    
    data = resp.json()
    amount_redeemed = data['amount']
    status = data['status']
    logger.info(f"[OK] Proofs melted to Lightning | Amount: {amount_redeemed} sats | Status: {status}")
    print(f"    Status: {status}")
    print(f"    Amount redeemed: {amount_redeemed} sats")
    
    # Check final balance
    resp = requests.get(f"{WALLET_URL}/api/wallet/balance")
    final_balance = resp.json()["balance"]
    logger.info(f"[OK] Final balance: {final_balance} sats (reduced by {balance - final_balance} sats)")
    print(f"\n[4] Final wallet balance: {final_balance} sats")
    print(f"    Amount spent: {balance - final_balance} sats")
    
    return True

def main():
    logger.info("="*70)
    logger.info("CASHU E-WALLET FULL FLOW TEST - STARTING")
    logger.info("="*70)
    
    print("\nCASHU E-WALLET FULL FLOW TEST")
    print("="*60)
    print(f"Wallet: {WALLET_URL}")
    print(f"Mint:   {MINT_URL}\n")
    
    logger.info(f"Wallet: {WALLET_URL}")
    logger.info(f"Mint: {MINT_URL}")
    
    # Check servers are running
    logger.info("Checking server availability...")
    try:
        requests.get(f"{WALLET_URL}/api/wallet/balance", timeout=2)
        requests.get(f"{MINT_URL}/health", timeout=2)
        logger.info("[OK] Both servers are running")
    except Exception as e:
        logger.error(f"Server check failed: {e}")
        print("\nERROR: Servers not running!")
        print("\nStart both servers in separate terminals:")
        print("  Terminal 1: python backend/mint/server.py")
        print("  Terminal 2: python backend/app.py")
        return
    
    # Run tests
    logger.info("Starting test sequence...")
    try:
        success = True
        
        success = test_mint_flow() and success
        time.sleep(1)
        
        success = test_send_flow() and success
        time.sleep(1)
        
        success = test_melt_flow() and success
        
        print("\n" + "="*60)
        if success:
            logger.info("[PASS] ALL TESTS PASSED")
            print("[PASS] ALL TESTS PASSED")
        else:
            logger.warning("[FAIL] SOME TESTS FAILED")
            print("[FAIL] SOME TESTS FAILED")
        print("="*60)
    except Exception as e:
        logger.exception(f"TEST ERROR: {str(e)}")
        print(f"\n[ERROR] TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
