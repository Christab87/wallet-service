import json
import base64
from models.proof import Proof


def encode_token(proofs: list[Proof], mint: str) -> str:
    payload = {
        "token": [
            {
                "mint": mint,
                "proofs": [p.to_dict() for p in proofs]
            }
        ]
    }

    json_str = json.dumps(payload)
    b64 = base64.urlsafe_b64encode(json_str.encode()).decode()

    return f"cashuA{b64}"


def decode_token(token: str) -> list[Proof]:
    if not token.startswith("cashuA"):
        raise ValueError("Invalid token format")

    b64 = token[6:]
    decoded = base64.urlsafe_b64decode(b64.encode()).decode()

    data = json.loads(decoded)

    proofs = []

    for entry in data.get("token", []):
        mint = entry.get("mint", "")

        for p in entry.get("proofs", []):
            proofs.append(Proof.from_dict({
                **p,
                "mint": mint
            }))

    return proofs