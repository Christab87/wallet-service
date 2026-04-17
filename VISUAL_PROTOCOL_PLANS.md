# Visual Plans

## 1. CHAUM'S BLIND SIGNATURE

```
USER                              MINT
──────────────────────            ──────────────────────

Step 1: Blind
Secret S  
Random r  
B_ = S*r
    │
    ├─ Send B_ ───────────────→

                                   Step 2: Sign Blind
                                   Receive B_
                                   C_ = B_^d
                                   SIGN (forget B_)
                                   
                                   ├─ Return C_ ────→

Step 3: Unblind
Receive C_
C = C_ / r
✓ Valid signature

RESULT: C is valid ✓ 
        Mint can't link ✗
```

---

## 2. CASHU PROTOCOL - 3 PHASES

```
┌────────────────────────────────────────────────────────────┐
│ PHASE 1: MINT (Create 100 sats)                            │
├────────────────────────────────────────────────────────────┤
│ Wallet                    Mint                             │
│   │                        │                               │
│   ├─ Request quote ───────→ Generate quote                 │
│   │                                                        │
│   ├─ Blind messages ──────→ Sign blindly                   │
│   │                                                        │
│   ←─ Blind signatures ─────┤                               │
│   │                                                        │
│   ├─ Unblind                                               │
│   ✓ Have 100 sats                                          │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ PHASE 2: SWAP (Send 50 sats)                               │
├────────────────────────────────────────────────────────────┤
│ Sender           Mint              Recipient               │
│   │               │                  │                     │
│   ├─ Select ─────→ Blind outputs     │                     │
│   │           ←──────  Signatures ───│                     │
│   ├───── Token ─────────────────────→                      │
│   │                                  │                     │
│   │                            Unblind & receive ✓         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ PHASE 3: MELT (Redeem 25 sats)                             │
├────────────────────────────────────────────────────────────┤
│ Wallet                    Mint                             │
│   │                        │                               │
│   ├─ Request melt ────────→ Generate melt quote            │
│   │                                                        │
│   ├─ Send proofs ─────────→ Verify & Pay                   │
│   │                                                        │
│   ←─ Confirmation ────────┤                                │
│   ✓ Funds received                                         │
└────────────────────────────────────────────────────────────┘
```

---

## 3. COMPARISON

```
┌───────────────────────────────────────────────────────────┐
│ CHAUM'S PROTOCOL                                          │
├───────────────────────────────────────────────────────────┤
│ Level:    Cryptographic Algorithm                         │
│ Goal:     Sign without seeing the message                 │
│ Parties:  User + Signer                                   │
│ Steps:    3 (Blind → Sign → Unblind)                      │
│ Result:   Valid signature + Complete anonymity            │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│ CASHU PROTOCOL                                            │
├───────────────────────────────────────────────────────────┤
│ Level:    Payment System                                  │
│ Goal:     Digital cash transactions                       │
│ Parties:  Wallet + Mint + Network                         │
│ Phases:   3 (Mint → Swap → Melt)                          │
│ Result:   Digital cash + Privacy + Security               │
│ Uses:     Chaum for every transaction                     │
└───────────────────────────────────────────────────────────┘

RELATIONSHIP:
Chaum = Foundation/Algorithm
  ↓
Cashu = Complete system built on Chaum
```

---

## 4. PRIVACY PRINCIPLES

```
WITHOUT CHAUM:
──────────────
User → Mint → "User spent 100 sats"
              (Mint tracks identity)

WITH CHAUM:
───────────
User → (Blind) → Mint → (Sign blind) → (Unblind) → Proof
       ✓ User controls secret  ✓ Mint can't link  ✓ Perfect privacy


CASHU'S ADVANTAGE:
──────────────────
Traditional bank:    "Alice paid Bob 50 sats"
                      ✗ Full identity tracking

Cashu + Chaum:       "Someone paid someone 50 sats"
                      ✓ Amount visible only
                      ✓ Users: Anonymous
                      ✓ Transactions: Unlinkable
```

---

## 5. SECURITY LAYERS

```
╔═════════════════════════════════════════╗
║ Layer 5: Application                    ║
║ Cashu E-Wallet (Send/Receive/Melt)      ║
╠═════════════════════════════════════════╣
║ Layer 4: Protocol                       ║
║ Cashu (MINT, SWAP, MELT phases)         ║
╠═════════════════════════════════════════╣
║ Layer 3: Cryptography                   ║
║ RSA-PSS Blind Signing                   ║
╠═════════════════════════════════════════╣
║ Layer 2: Foundation                     ║
║ Chaum's Blind Signature Algorithm       ║
╠═════════════════════════════════════════╣
║ Layer 1: Mathematics                    ║
║ RSA + SHA256                            ║
╚═════════════════════════════════════════╝
```

---

## 6. QUICK REFERENCE

```
CHAUM'S 3-STEP PROCESS:

Step 1 (User):      Secret (S) + Random (r) → Blind (B_)
Step 2 (Mint):      Receive B_ → Sign (C_) → Return C_
Step 3 (User):      Receive C_ → Unblind → Get C

Key: Mint never sees S, only B_. Can't link C to user.


CASHU'S 3-PHASE PROCESS:

Phase 1 (MINT):     Request → Create → Unblind → Have coins
Phase 2 (SWAP):     Send → Blind → Create token → Receive
Phase 3 (MELT):     Request → Send proofs → Verify → Pay

Key: Each phase uses Chaum to maintain privacy.
```

---

## SUMMARY

```
✓ Chaum's Protocol = Anonymous blind signatures
✓ Cashu Protocol = Digital cash system using Chaum
✓ Privacy = Guaranteed by mathematics (RSA)
✓ Security = Unforgeable proofs
✓ Anonymity = Complete, even from Mint

Result: Perfect digital cash with zero tracking
```
