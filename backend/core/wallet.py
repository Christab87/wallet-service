import time
from typing import List, Optional, Dict
from models.proof import Proof
from models.cashu import Quote, KeySet


class WalletService:
    def __init__(self, storage):
        self.storage = storage

        loaded = self.storage.load()

        # Handle both legacy (tuple) and current (dict) storage formats
        if isinstance(loaded, tuple):
            proofs, transactions = loaded
        else:
            proofs = loaded
            transactions = []

        # Normalize proofs to ensure all items are Proof objects
        # Handles cases where proofs might be stored as dicts or have nested structures
        self.proofs = []
        for p in proofs:
            if isinstance(p, Proof):
                self.proofs.append(p)
            elif isinstance(p, dict):
                self.proofs.append(Proof.from_dict(p))
            elif isinstance(p, list):
                # Handle edge case of nested lists from malformed storage
                for sub in p:
                    if isinstance(sub, dict):
                        self.proofs.append(Proof.from_dict(sub))

        self.transactions = transactions if isinstance(transactions, list) else []
        
        # Cashu protocol state
        self.pending_quotes: Dict[str, Quote] = {}  # {quote_id: Quote}
        self.keysets: Dict[str, KeySet] = {}  # {mint_url: KeySet}

    def get_balance(self, mint=None):
        if mint:
            return sum(p.amount for p in self.proofs if p.mint == mint)
        return sum(p.amount for p in self.proofs)

    def add_proofs(self, proofs: List[Proof]):
        if isinstance(proofs, tuple):
            proofs = list(proofs)

        self.proofs.extend(proofs)
        self._save()

    def remove_proofs(self, proofs: List[Proof]):
        for p in proofs:
            if p in self.proofs:
                self.proofs.remove(p)
        self._save()

    def get_proofs_for_amount(self, amount, mint):
        selected = []
        total = 0

        for p in self.proofs:
            if p.mint != mint:
                continue

            selected.append(p)
            total += p.amount

            if total >= amount:
                return selected

        raise ValueError("Not enough balance")

    def add_transaction(self, tx_type, amount, mint):
        tx = {
            "type": tx_type,
            "amount": amount,
            "mint": mint,
            "timestamp": int(time.time())
        }
        self.transactions.append(tx)
        self._save()

    def get_transactions(self):
        return list(reversed(self.transactions))
    
    # --- Cashu Protocol State Management ---
    
    def add_quote(self, quote: Quote) -> None:
        # Track pending mint or melt quote
        self.pending_quotes[quote.quote_id] = quote
        print(f"[Wallet] Added {quote.quote_type} quote {quote.quote_id}")
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        # Retrieve quote by ID
        return self.pending_quotes.get(quote_id)
    
    def remove_quote(self, quote_id: str) -> None:
        # Remove quote after completion
        if quote_id in self.pending_quotes:
            del self.pending_quotes[quote_id]
            print(f"[Wallet] Removed quote {quote_id}")
    
    def get_active_quotes(self) -> List[Quote]:
        # Get all non-expired pending quotes
        return [q for q in self.pending_quotes.values() if not q.is_expired()]
    
    def cache_keyset(self, mint_url: str, keyset: KeySet) -> None:
        # Cache mint's keyset locally
        self.keysets[mint_url] = keyset
        print(f"[Wallet] Cached keyset for {mint_url}")
    
    def get_keyset(self, mint_url: str) -> Optional[KeySet]:
        # Retrieve cached keyset for mint
        return self.keysets.get(mint_url)

    def _save(self):
        self.storage.save(self.proofs, self.transactions)
