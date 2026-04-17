# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please email me directly instead of using the public issue tracker.

**Do not disclose security issues publicly.**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

I will acknowledge receipt and work on a fix promptly.

## Security Guidelines

### For Users
- Never expose your wallet's private keys
- Keep your `wallet.dat` file secure and backed up
- Do not share Lightning invoices or payment tokens with untrusted parties
- Test thoroughly before using with real funds

### For Contributors
- Never commit sensitive data (keys, tokens, passwords)
- Use `.env` files for local configuration (ignored by git)
- Follow principle of least privilege
- Report security issues responsibly

## Known Limitations

This is an experimental implementation. Be aware of:
- Use only for testing/development purposes
- Not audited for production use
- Blind signature implementation should be reviewed by cryptography experts
- Lightning integration uses test networks

## Dependencies

Security updates for dependencies are important. Run regularly:
```bash
pip install --upgrade pip
pip list --outdated
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version updates and security fixes.
