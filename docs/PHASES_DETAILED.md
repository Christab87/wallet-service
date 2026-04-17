# Cashu e-Wallet: Detailed Phase Explanations

## Overview

The Cashu payment system has three main phases that handle the complete lifecycle of digital proofs (satoshi ownership). Each phase uses **blind signing cryptography** to ensure privacy and security.

---

## Phase 1️⃣: MINT PHASE - Creating Proofs

### Purpose
Generate new proofs (satoshi ownership tokens) from the mint server without revealing the amounts to the server.

### The Problem It Solves
**Traditional Problem:** If you ask a bank for $100, the bank sees:
- Your account
- The amount ($100)
- When you requested it
- They can track everything you do

**Cashu Solution:** The wallet blinds the amounts so the mint can sign them without seeing:
- Individual amounts
- Who the wallet owner is
- Any identifying information

### Step-by-Step Flow

#### Step 1: Health Check
```
User → Flask → Cashu Client → Mint Server
                              ↓
                        "Are you alive?"
                              ↓
                        "Yes! I'm healthy"
```
**Code:** `GET /health`
**Purpose:** Verify mint is running and responding

---

#### Step 2: Request Quote
```
Cashu Client: "I want 100 sats"
              ↓
Mint Server: Creates quote with:
  - quote_id: "d6702017-7321-4fc6-a5f1-6772d3a01edf"
  - amount: 100 sats
  - keyset: Public RSA keys for blind signing
```

**Code Equivalent:**
```python
response = requests.post("http://mint/requestmint", json={"amount": 100})
quote = response.json()  
# {
#   "quote_id": "d6702017-...",
#   "amount": 100,
#   "keyset": {...public_keys...}
# }
```

---

#### Step 3: Blind the Amounts

This is where the **cryptography magic** happens! 

**Goal:** Create messages that the mint will sign, but the mint CANNOT see what amounts they represent.

**How Blind Signing Works (RSA):**

```
1. WALLET SIDE - Blind the Message:
   ┌─────────────────────────────────────────────┐
   │ Original amounts: [1, 2, 4, 8, 16, 32, 37]  │
   │                                              │
   │ For each amount:                             │
   │   message = SHA256(amount)                   │
   │   random_blinding_factor = random()          │
   │   blinded_message = message * r^e mod N      │
   │                                              │
   │ Result: 7 blinded messages (mint can't see)  │
   └─────────────────────────────────────────────┘
   
2. SEND TO MINT:
   Wallet → Mint: [blinded_m1, blinded_m2, ... blinded_m7]
   
   Note: Mint sees only gibberish! Can't extract amounts!

3. MINT SIGNS (Blind):
   For each blinded message:
     blind_signature = blinded_message^d mod N
   
   Mint → Wallet: [blind_sig1, blind_sig2, ... blind_sig7]

4. WALLET UNBLINDS:
   For each blind signature:
     real_signature = blind_sig * r^(-1) mod N
   
   Result: Valid RSA signatures on the original amounts!
   Mint never saw the amounts, but signed them anyway!
```

**In Code:**
```python
# Wallet blinds amounts
amounts = [1, 2, 4, 8, 16, 32, 37]

for amount in amounts:
    # Create hash of amount
    message = int.from_bytes(
        hashlib.sha256(str(amount).encode()).digest(), 
        byteorder='big'
    )
    
    # Generate random blinding factor (keeping r secret!)
    r = randbelow(n)
    
    # Blind the message
    blinded_message = (message * pow(r, e, n)) % n
    
    # Send to mint (mint only sees blinded_message, not amount!)
    blinded_messages.append({
        'amount': amount,
        'blinded_message': blinded_message
    })

# Mint blindly signs and returns blind_signatures
# Wallet unblinds by multiplying by r^(-1)
r_inv = pow(r, -1, n)  # Modular inverse
real_signature = (blind_signature * r_inv) % n
```

**Why This is Secure:**
- Mint signs using private key d
- Even though mint signs blinded messages, the math works out!
- Result is valid signature on original amount
- Mint cannot see the amount → Privacy! ✅

---

#### Step 4: Unblind Signatures

The wallet now has valid signatures on the original amounts!

```python
# After receiving blind_signatures from mint
proofs = []

for i, blind_sig in enumerate(blind_signatures):
    amount = amounts[i]
    
    # Unblind by multiplying by r^(-1)
    r_inv = pow(r[i], -1, n)
    signature = (blind_sig * r_inv) % n
    
    # Create proof: amount + signature
    proof = {
        'amount': amount,
        'secret': random_secret,  # For spending later
        'signature': signature
    }
    proofs.append(proof)
```

**Result:** 7 valid, unspendable proofs totaling 100 sats! ✅

---

#### Step 5: Store Proofs Encrypted

Proofs must never be exposed in plain text!

```python
# Encrypt proofs using Fernet (AES-128)
from cryptography.fernet import Fernet

encryption_key = derive_key(passphrase="wallet_password")
cipher = Fernet(encryption_key)

encrypted_proofs = cipher.encrypt(json.dumps(proofs).encode())

# Save to wallet.dat
with open('wallet.dat', 'wb') as f:
    f.write(encrypted_proofs)
```

**Security:**
- Only unlock with correct passphrase
- Proofs never exist unencrypted on disk
- Even if someone steals wallet.dat, they can't use proofs without key

---

### Why MINT Phase is Brilliant

| Aspect | Traditional Banking | Cashu |
|--------|-------------------|-------|
| **What server sees** | Account, amount, time, identity | Nothing! Just random gibberish |
| **Privacy** | ❌ Complete tracking | ✅ Perfect anonymity |
| **Double-spend** | Bank tracks all transactions | Mint only tracks signed proofs |
| **User ID** | Required | Not needed! |

---

## Phase 2️⃣: SWAP PHASE - Breaking the Transaction Link

### Purpose
Replace spent proofs with fresh ones to break the link between sender and receiver (essential for privacy in payments).

### The Privacy Problem

**Scenario:**
1. User gets 100 sats from mint (8 proofs)
2. User wants to send some to Alice
3. User sends Alice proof #3 (the "8 sats proof")
4. If Alice spends that same proof, the mint now knows:
   - Mint issued proof #3 to someone
   - Someone sent proof #3 to Alice
   - Mint saw Alice redeem proof #3
   - **Transaction link established!** ❌

### The Solution: Swap

Instead of sending the original proof (which has history), the wallet:
1. Creates brand new proofs with the same value
2. Swaps old proofs for new ones with the mint
3. Sends the brand new proofs to recipient

Now the chain is broken! ✅

### Step-by-Step Flow

#### Step 1: Get Mint Keys

```
Cashu Client → Mint: "Give me your public keys"
                     ↓
Mint → Cashu Client: {
    "keyset_1": {"1": "public_key_1", "2": "public_key_2", ...},
    "keyset_2": {...more public keys...}
}
```

**Why needed:** Wallet uses these keys to blind messages for the new proofs.

---

#### Step 2: Select Proofs to Swap

```
Wallet has 8 proofs:
  [1 sat, 2 sats, 4 sats, 8 sats, 16 sats, 32 sats, 37 sats, and one more]

User wants to send payment. Wallet picks:
  [1 sat, 2 sats, 4 sats] = 7 sats to swap
  (Keeping [8, 16, 32, 37, ...] = 93 sats safe at home)
```

---

#### Step 3: Blank New Outputs

The wallet creates 7 new blinded messages for new proofs:

```
For each new denomination needed:
  1. Generate new secret (random)
  2. Create message = SHA256(secret)
  3. Blind message = message * r^e mod N
  4. Store r in wallet (keep seed safe!)

Result: 7 completely new blinded messages
(These don't exist yet - just random gibberish!)
```

---

#### Step 4: Request Swap from Mint

```
Wallet → Mint: {
    "quote_id": "swap_123",
    "old_proofs": [
        {amount: 1, signature: sig1, secret: secret1},
        {amount: 2, signature: sig2, secret: secret2},
        {amount: 4, signature: sig3, secret: secret3}
    ],
    "new_blinded_messages": [
        blinded_m1, blinded_m2, blinded_m3, ...
    ]
}
```

---

#### Step 5: Mint Verifies and Swaps

```
Mint validates:
  ✓ Each old proof hasn't been spent before
  ✓ Each old proof has valid signature
  ✓ Signatures match the amounts
  
If valid:
  Mint signs each new blinded message
  
  Mint → Wallet: [
    blind_sig1, blind_sig2, blind_sig3, ...
  ]
```

---

#### Step 6: Wallet Unblinds New Proofs

```
For each blind signature:
  signature = blind_sig * r^(-1) mod N
  
Result: 7 brand new valid proofs with same total value!

Old proofs: [1, 2, 4] - FORGET THESE (or mark as sent)
New proofs: [1, 2, 4] - These are brand new!

Now wallet can:
  • Send new proofs to Alice (she can spend them)
  • Mint can't link: old proofs → Alice → new proofs
  • Privacy maintained! ✅
```

### Why SWAP is Cryptographically Sound

```
Mathematical Property:
  Signature(SHA256(secret)) = valid_signature_on_secret
  
  Even though:
  - Mint signed blind_message = SHA256(secret) * r^e
  - Mint never saw secret
  - Wallet unblinds to get: valid_signature_on_secret
  
  This is mathematically guaranteed by RSA properties!
```

### Privacy Guarantee

| Knowledge | Before Swap | After Swap |
|-----------|------------|-----------|
| **Mint knows** | Which proofs were issued to whom | Only that proofs exist |
| **Receiver knows** | Received tokens (but no source) | Same tokens |
| **Sender knows** | Sent these tokens | Sent tokens from different issuing batch |
| **Link established** | YES - sender → original proofs | NO - unbreakable ✅ |

---

## Phase 3️⃣: MELT PHASE - Redeeming Proofs

### Purpose
Convert proofs back to Lightning payment (redeem for value outside the mint).

### The Flow

#### Step 1: Request Melt Quote

```
User: "I want to pay Alice 10 sats via Lightning"

Wallet → Mint: {
    "amount": 10,
    "invoice": "lnbc100n1p0ptzv0..."
}
```

Mint creates a **melt quote**:
```
{
    "quote_id": "melt_123",
    "amount": 10,
    "invoice": "lnbc...",
    "expiry": 3600  // Seconds until quote expires
}
```

---

#### Step 2: Select Proofs

Wallet needs exactly 10 sats (or more, for change).

```
Wallet has: [1, 2, 4, 8, 16, 32, 37]

To pay 10 sats, could pick:
  Option A: [2, 8] = 10 sats exactly
  Option B: [1, 2, 4, 8] = 15 sats (will get 5 sats change)
  Option C: [1, 2, 4, 8, 16] = 31 sats (will get 21 sats change)

Wallet chooses Option B (smart choice - 15 sats)
```

---

#### Step 3: Submit Proofs to Mint

```
Wallet → Mint: {
    "quote_id": "melt_123",
    "proofs": [
        {amount: 1, secret: s1, signature: sig1},
        {amount: 2, secret: s2, signature: sig2},
        {amount: 4, secret: s4, signature: sig4},
        {amount: 8, secret: s8, signature: sig8}
    ]
}

Total: 15 sats
```

---

#### Step 4: Mint Verifies Proofs

```
For each proof, mint verifies:
  1. Is this proof already spent? (Check database)
  2. Is the signature valid? (Check RSA signature)
  3. Is the secret correct? (Hash the secret, match to stored commitments)
  
If all valid:
  ✅ Mark proofs as SPENT (prevent double-spend)
  ✅ Pay Lightning invoice for 10 sats
  ⚡ Get payment hash from Lightning network
```

---

#### Step 5: Return Payment Hash

```
Mint → Wallet: {
    "preimage": "...",
    "paid": true,
    "change": 5  // 15 - 10 = 5 sats change
}
```

---

#### Step 6: Wallet Deletes Spent Proofs

```
Remove from wallet.dat:
  [1, 2, 4, 8] sats - DELETED (these were melted)

Remaining: [16, 32, 37] = 85 sats (still safe in wallet)

Or wallet receives 5 sats change:
  Remaining: [16, 32, 37, 5] = 90 sats
```

---

### Why MELT is Secure

| Guarantee | How It's Achieved |
|-----------|-------------------|
| **No double-spend** | Mint marks proof as spent immediately, rejects future use |
| **Atomic payment** | Either payment succeeds AND proofs burned, or both fail |
| **Change handling** | Mint creates new proofs for change (using same mint signing) |
| **Privacy maintained** | Mint doesn't know sender's identity, only that invoice was paid |

---

## Complete Example Walkthrough

### Scenario: Alice Pays Bob 10 Sats

**Initial State:**
- Alice has 100 sats (7 proofs from MINT phase)
- Alice wants to send Bob 10 sats via Lightning invoice
- Bob's Lightning node provides invoice: `lnbc100n1p0ptzv0...`

---

### Step 1: Alice's Wallet Does SWAP (Break Link)

**Purpose:** Don't send original proofs (which have Alice's minting history)

```
Alice's proofs: [1, 2, 4, 8, 16, 32, 37]
                ↓
                [Create 7 brand new blinded messages]
                ↓
Mint signs them blindly
                ↓
Alice unblinds to get [1, 2, 4, 8, 16, 32, 37] (brand new!)
                ↓
Old proofs: [MARKED AS SENT - don't reuse]
New proofs: [1, 2, 4, 8, 16, 32, 37] (fresh from swap)
```

---

### Step 2: Alice's Wallet Selects Proofs for Payment

```
Alice wants to pay 10 sats

Options:
  • Need at least 10 sats to cover payment
  • Prefer to minimize change
  
Alice selects: [2, 8] = 10 sats exactly ✅

No change needed!
```

---

### Step 3: Alice Sends to Bob's Invoice

```
Alice → Bitcoin Lightning Network → Bob:
  "Take these 2 proofs [2, 8 sats]"
  
But first, Alice's wallet does one more SWAP to break even this link!

New blinded outputs: 2 sats + 8 sats = 10 sats in new form
Mint signs: [blind_sig_2, blind_sig_8]
Alice unblinds: [proof_2_new, proof_8_new]
                ↓
Alice sends [proof_2_new, proof_8_new] to Bob
```

---

### Step 4: Bob Receives & Can Spend

```
Bob now has: [2 sats proof, 8 sats proof]
                ↓
Bob can MELT these to get value:
  Bob → Mint: "Redeem these 10 sats for Lightning payment to my account"
  Mint: Validates signatures, pays Lightning
  Bob: Gets payment confirmed ✅
```

---

### Final Verification

```
From Mint's perspective:
  • Issued 100 sats to someone (not Alice specifically)
  • Someone swapped, asked to redeem 10 sats
  • Invoice paid to Bob's node
  • Don't know who the sender was ✓ (Privacy!)

From Bob's perspective:
  • Received 10 sats from unknown peer
  • Can spend immediately without worrying about history
  • Money is clean ✓

From Alice's perspective:
  • Sent payment, amount confirmed
  • Original amount never linked to receiver
  • Perfect privacy ✓
```

---

## Security Summary

### What's Protected

**Against Mint:**
- ✅ Wallet can have privacy (blind signing prevents tracking)
- ✅ Amounts hidden during minting (blinding)
- ✅ Sender/receiver not linked (swap phase)

**Against Double-Spend:**
- ✅ Each proof can only be spent once (marked in database)
- ✅ Proofs are unforgeable (RSA signatures)
- ✅ Invalid proofs rejected immediately

**Against Tampering:**
- ✅ Cannot modify amounts (would invalidate signature)
- ✅ Cannot forge new proofs (need mint's private key)
- ✅ Cannot steal unencrypted proofs (stored with Fernet encryption)

### What's NOT Protected

**In This Implementation:**
- ❌ No network privacy (IP addresses visible)
- ❌ No protection if mint is compromised (would need multi-sig)
- ❌ No recourse system (proofs are final)

---

## Code Architecture

```
1. MINT PHASE
   backend/core/cashu.py:mint()
   ├─ Request quote from mint
   ├─ backend/crypto/blind_signing.py:blind()
   ├─ Send blinded messages
   ├─ backend/crypto/blind_signing.py:unblind()
   └─ backend/storage/encrypted.py:save_proofs()

2. SWAP PHASE
   backend/core/cashu.py:swap()
   ├─ Get mint keys
   ├─ backend/crypto/blind_signing.py:blind() [new proofs]
   ├─ Request swap with old + new blinded
   ├─ backend/crypto/blind_signing.py:unblind() [new signatures]
   └─ backend/storage/encrypted.py:replace_proofs()

3. MELT PHASE
   backend/core/cashu.py:melt()
   ├─ Request melt quote
   ├─ backend/storage/encrypted.py:select_proofs()
   ├─ Submit proofs to mint
   ├─ Verify payment from Lightning
   └─ backend/storage/encrypted.py:delete_proofs()
```

---

## Key Takeaway

The three phases work together to create a **privacy-preserving digital cash system:**

- **MINT** = Issue proofs securely (blind signing)
- **SWAP** = Maintain privacy (break spending history link)
- **MELT** = Redeem for real value (irreversible)

All three phases rely on **RSA blind signing mathematics** to ensure the mint cannot track users while still being able to verify proofs haven't been double-spent.

This is the innovation of Cashu! 🚀
