from utils.token import encode_token
from models.proof import Proof

# Create fake proofs (like "fake money")
proofs = [
    Proof(
        amount=1000,
        secret="test-secret-1",
        C="test-C-1",
        mint="https://mint.cashu.me"
    ),
    Proof(
        amount=500,
        secret="test-secret-2",
        C="test-C-2",
        mint="https://mint.cashu.me"
    )
]

# Encode into Cashu token
token = encode_token(proofs, "https://mint.cashu.me")

print("\n=== YOUR TEST TOKEN ===\n")
print(token)