import requests


class WalletClient:
    def __init__(self, mint_url: str):
        self.mint_url = mint_url.rstrip("/")

    def get_keys(self):
        res = requests.get(f"{self.mint_url}/keys", timeout=10)
        res.raise_for_status()
        return res.json()

    def split(self, proofs: list[dict], amount: int):
        res = requests.post(
            f"{self.mint_url}/split",
            json={
                "proofs": proofs,
                "amount": amount
            },
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def melt(self, proofs: list[dict], invoice: str):
        res = requests.post(
            f"{self.mint_url}/melt",
            json={
                "proofs": proofs,
                "pr": invoice
            },
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    def mint(self, invoice: str):
        res = requests.post(
            f"{self.mint_url}/mint",
            json={"pr": invoice},
            timeout=10
        )
        res.raise_for_status()
        return res.json()
