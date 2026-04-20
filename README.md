
# E-Wallet - Cashu Implementation 

A complete Cashu e-wallet implementation with Lightning Network integration for privacy-preserving digital payments.

> **Development Status**: This is an experimental proof-of-concept project built for learning and testing the Cashu protocol. Code is exploratory and may change significantly. Not recommended for production use with real funds yet.

## Features

- **Cashu Protocol**: Full implementation of the Cashu payment protocol
- **Blind Signatures**: Cryptographic blind signature support using BDHAKE
- **Lightning Integration**: Convert between Cashu proofs and Lightning payments
- **Mint & Melt**: Create new proofs and redeem them back to Lightning
- **Token Swaps**: Send and receive proofs with transaction tokens
- **Wallet Management**: Full wallet functionality with balance tracking

## Screenshots

![E-Wallet Interface](docs/screenshot/Wallet.png)


## Project Structure

```
e_wallet/
├── backend/
│   ├── app.py                     # Main Flask wallet application
│   ├── config.py                  # Configuration settings
│   ├── test_token.py              # Token encoding/decoding tests
│   ├── wallet.dat                 # Encrypted wallet database
│   ├── client/                    # Wallet client utilities
│   ├── core/                      # Core Cashu protocol logic
│   │   ├── __init__.py
│   │   ├── cashu.py              # CashuClient implementation
│   │   ├── wallet.py             # WalletService (proof management)
│   │   ├── mint.py               # MintService
│   │   └── price.py              # Bitcoin price utilities
│   ├── crypto/                    # Cryptographic functions
│   │   ├── __init__.py
│   │   └── blind_signing.py      # RSA-PSS blind signatures
│   ├── mint/                      # Mock Cashu mint server
│   │   └── server.py              # Mock mint implementation (port 5001)
│   ├── models/                    # Data models
│   │   ├── __init__.py
│   │   ├── cashu.py              # Quote, KeySet, Token models
│   │   └── proof.py              # Proof model
│   ├── storage/                   # Storage & encryption
│   │   ├── __init__.py
│   │   └── encrypted.py          # StorageService (Fernet encryption)
│   ├── utils/                     # Utility functions
│   │   ├── __init__.py
│   │   └── token.py              # Token encoding/decoding
│   └── static/                    # PWA frontend assets
├── tests/
│   ├── __init__.py
│   └── test_cashu_flow.py        # End-to-end integration test
├── docs/
│   ├── screenshot/               # Project screenshots
│   │   └── Wallet.png
│   ├── diagrams/                 # Architecture diagrams
│   └── Git Commands Overview/    # Git reference guide
├── .github/                       # GitHub configuration
│   ├── SECURITY.md               # Security policy
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── LICENSE                       # MIT License
├── ROADMAP.md                    # Development roadmap
├── PROJECT_STATUS.md             # Current project status
└── Core Cashu documentation files
    ├── ALGORITHM_INTEGRATION.md
    ├── CASHU_PROTOCOL_IMPLEMENTATION_GUIDE_DE.md
    └── CHAUMS_BLIND_SIGNATURE_INTEGRATION_DE.md
```

## Requirements

- Python 3.8+
- pip or conda for package management

## Security

This project uses environment variables to manage sensitive configuration. Never commit `.env` files to version control.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/e_wallet.git
cd e_wallet
```

2. Create environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
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

**Wallet Management:**
- `GET /api/wallet/balance` - Get current wallet balance
- `GET /api/transactions` - Get transaction history
- `GET /api/health` - Health check

**Cashu Operations:**
- `POST /api/mint/request` - Request mint quote from mint server
- `POST /api/mint/finish` - Complete mint operation
- `POST /api/melt/request` - Request melt quote (redeem to Lightning)
- `POST /api/melt/finish` - Complete melt operation

**Proof Management:**
- `POST /api/send` - Send/swap proofs to another wallet
- `POST /api/receive` - Receive proofs from a payment token
- `GET /api/debug/proofs` - Debug endpoint to view proofs

**Utilities:**
- `GET /api/mints` - List available mints
- `POST /api/mints/add` - Add new mint server
- `GET /api/btc-price` - Get current Bitcoin price in USD/EUR
- `GET /api/btc-price-history` - Get Bitcoin price history

### Mint API (port 5001)

- `GET /health` - Health check
- `POST /api/mint` - Mint new proofs (internal use)
- `POST /api/melt` - Melt proofs

## Configuration

Edit `backend/config.py` to customize:
- Server ports
- Database settings
- Lightning network parameters
- Cryptographic settings

## Development

For development and testing, uncomment optional dependencies in `requirements.txt`:
```bash
# Uncomment these lines in requirements.txt, then:
pip install -r requirements.txt
```

Or install specific tools:
```bash
pip install pytest pytest-cov black flake8 mypy
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

