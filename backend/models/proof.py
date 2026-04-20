# Ecash proof representing ownership of satoshis
class Proof:
    # Initialize proof with amount and secret
    def __init__(self, amount: int, secret: str, C: str, mint: str):
        self.amount = amount
        self.secret = secret
        self.C = C
        self.mint = mint

    # Convert proof to dictionary
    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "secret": self.secret,
            "C": self.C,
            "mint": self.mint
        }

    # Create proof from dictionary
    @staticmethod
    def from_dict(data: dict):
        return Proof(
            amount=data["amount"],
            secret=data["secret"],
            C=data["C"],
            mint=data.get("mint", "")
        )

    # String representation of proof
    def __repr__(self):
        return f"<Proof {self.amount} sats @ {self.mint}>"

    # Check equality of proofs
    def __eq__(self, other):
        return (
            isinstance(other, Proof) and
            self.secret == other.secret and
            self.C == other.C
        )