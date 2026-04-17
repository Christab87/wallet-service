class Proof:
    def __init__(self, amount: int, secret: str, C: str, mint: str):
        self.amount = amount
        self.secret = secret
        self.C = C
        self.mint = mint

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "secret": self.secret,
            "C": self.C,
            "mint": self.mint
        }

    @staticmethod
    def from_dict(data: dict):
        return Proof(
            amount=data["amount"],
            secret=data["secret"],
            C=data["C"],
            mint=data.get("mint", "")
        )

    def __repr__(self):
        return f"<Proof {self.amount} sats @ {self.mint}>"

    def __eq__(self, other):
        return (
            isinstance(other, Proof) and
            self.secret == other.secret and
            self.C == other.C
        )