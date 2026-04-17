# E-Wallet - Cashu Implementation

A complete Cashu e-wallet implementation with Lightning Network integration for privacy-preserving digital payments.

## Features

- **Cashu Protocol**: Full implementation of the Cashu payment protocol
- **Blind Signatures**: Cryptographic blind signature support using BDHAKE
- **Lightning Integration**: Convert between Cashu proofs and Lightning payments
- **Mint & Melt**: Create new proofs and redeem them back to Lightning
- **Token Swaps**: Send and receive proofs with transaction tokens
- **Wallet Management**: Full wallet functionality with balance tracking

## Project Structure

```
e_wallet/
├── backend/
│   ├── app.py                 # Wallet Flask application
│   ├── config.py              # Configuration settings
│   ├── wallet.dat             # Wallet database
│   ├── client/                # Client utilities
│   ├── core/                  # Core Cashu protocol logic
│   ├── crypto/                # Cryptographic functions
│   ├── mint/                  # Mint server implementation
│   ├── models/                # Data models
│   ├── storage/               # Storage/database layer
│   ├── utils/                 # Utility functions
│   └── static/                # Static web assets
├── tests/
│   ├── test_cashu_flow.py    # End-to-end test flow
│   └── __init__.py
├── docs/
│   └── ALGORITHM_INTEGRATION.md
├── requirements.txt           # Python dependencies
└── requirements-dev.txt       # Development dependencies
```

## Requirements

- Python 3.8+
- pip or conda for package management

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/e_wallet.git
cd e_wallet
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Start the Wallet Server

```bash
python backend/app.py
```
The wallet API will be available at `http://localhost:8000`

### Start the Mint Server

```bash
python backend/mint/server.py
```
The mint will be available at `http://localhost:5001`

### Run Tests

Execute the full e-wallet flow test:
```bash
python tests/test_cashu_flow.py
```

This will:
1. Mint new proofs (100 sats) using Lightning
2. Send proofs to another wallet via swap
3. Receive blinded outputs
4. Melt proofs back to Lightning

## API Endpoints

### Wallet API (port 8000)

- `GET /api/wallet/balance` - Get wallet balance
- `POST /api/mint/request` - Request mint quote
- `POST /api/mint/finish` - Finish mint operation
- `POST /api/send` - Send proofs
- `POST /api/melt/request` - Request melt quote
- `POST /api/melt/finish` - Finish melt operation

### Mint API (port 5001)

- `GET /health` - Health check
- `POST /api/mint` - Mint proofs
- `POST /api/melt` - Melt proofs

## Configuration

Edit `backend/config.py` to customize:
- Server ports
- Database settings
- Lightning network parameters
- Cryptographic settings

## Development

For development dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests with coverage:
```bash
pytest tests/ --cov=backend
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Security Notice

This is an experimental implementation. Use with caution in production environments. Always keep private keys secure and never expose wallet data.

## References

- [Cashu Protocol](https://github.com/cashubtc/cashu)
- [Blind Signatures](https://en.wikipedia.org/wiki/Blind_signature)
- [Lightning Network](https://lightning.network/)
