# E-Wallet Development Roadmap

This document outlines the next steps and planned improvements for the Cashu e-wallet project.

## Phase 1: Core Stability (Current Focus)

### Code Quality & Refactoring
- [ ] Add type hints to all functions (Python 3.10+ compatibility)
- [ ] Refactor large functions (app.py, mint/server.py) into smaller modules
- [ ] Add docstrings to all classes and methods
- [ ] Remove German documentation files or translate to English
- [ ] Clean up test files (remove old test_token.py)

### Environment & Configuration
- [ ] Create `.env.example` file for configuration template
- [ ] Convert hardcoded URLs to environment variables
- [ ] Implement proper config management (development, testing, production)
- [ ] Add logging instead of print statements
- [ ] Set DEBUG=False as default for production

### Testing
- [ ] Add unit tests for crypto functions
- [ ] Add unit tests for models and validators
- [ ] Add integration tests for wallet operations
- [ ] Improve test_cashu_flow.py with error cases
- [ ] Add pytest fixtures and parametrized tests
- [ ] Achieve 70%+ code coverage

## Phase 2: Feature Enhancements

### Wallet Features
- [ ] Add transaction history/audit trail
- [ ] Implement proof expiration (timestamps)
- [ ] Add proof grouping/tagging by purpose
- [ ] Wallet backup and restore functionality
- [ ] Multi-wallet support in single instance

### Mint Features
- [ ] Implement proof revocation mechanism
- [ ] Add mint key rotation support
- [ ] Improve quote expiration handling
- [ ] Add mint statistics/monitoring
- [ ] Support multiple denominations

### Lightning Integration
- [ ] Test with real Lightning testnet
- [ ] Add LNURL payment support
- [ ] Implement keysend payments
- [ ] Add payment status tracking
- [ ] Support for invoicing

## Phase 3: Security & Performance

### Security Hardening
- [ ] Security audit of cryptographic implementations
- [ ] Add input validation and sanitization
- [ ] Implement rate limiting on API endpoints
- [ ] Add CORS configuration
- [ ] Implement authentication/authorization (tokens)
- [ ] Add audit logging for sensitive operations

### Performance Optimization
- [ ] Database query optimization
- [ ] Add caching layer (Redis)
- [ ] Profile and optimize crypto operations
- [ ] Implement async operations where possible
- [ ] Add database indexing

### Data Protection
- [ ] Encrypt wallet data at rest
- [ ] Implement proof encryption
- [ ] Add secure key storage (not plaintext)
- [ ] Database backup strategy
- [ ] Implement secure deletion of sensitive data

## Phase 4: User Experience & Deployment

### API Improvements
- [ ] Add comprehensive API documentation (OpenAPI/Swagger)
- [ ] Rate limiting and throttling
- [ ] Better error messages and codes
- [ ] Request/response validation
- [ ] API versioning support

### Frontend Development
- [ ] Create web UI for wallet
- [ ] Add real-time balance updates (WebSocket)
- [ ] Transaction history UI
- [ ] QR code generation for tokens
- [ ] Mobile-friendly design

### Deployment & DevOps
- [ ] Docker containerization
- [ ] Docker Compose for local development
- [ ] GitHub Actions CI/CD pipeline
- [ ] Database migration scripts
- [ ] Deployment documentation
- [ ] Health check endpoints

## Phase 5: Production Readiness

### Documentation
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Architecture documentation
- [ ] Deployment guide
- [ ] Security best practices guide
- [ ] Troubleshooting guide

### Monitoring & Operations
- [ ] Structured logging (JSON logs)
- [ ] Metrics/monitoring (Prometheus)
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring
- [ ] Alerting system

### Compliance & Standards
- [ ] Cashu protocol compliance testing
- [ ] Lightning spec compliance
- [ ] Follow Bitcoin/cryptographic standards
- [ ] Create CHANGELOG.md
- [ ] Version tagging strategy

## Quick Wins (Do First!)

These can be done quickly and improve code quality immediately:

1. **Add .env.example**
   ```
   MINT_URL=http://localhost:5001
   WALLET_URL=http://localhost:8000
   FLASK_ENV=development
   DEBUG=False
   ```

2. **Create CHANGELOG.md**
   - Document version history
   - Track changes and improvements

3. **Add GitHub Actions Workflow**
   - Run tests on push
   - Check code quality
   - Validate requirements.txt

4. **Add improved error handling**
   - Better exception messages
   - Proper HTTP status codes
   - JSON error responses

5. **Create API documentation**
   - Comment all endpoints
   - Document request/response format
   - Include curl examples

## Long-Term Vision

- Production-ready Cashu implementation
- Web-based wallet interface
- Mobile app support
- Community ecosystem
- Integration with other Lightning services
- Educational resource for Cashu protocol

## Contributing

Want to help with any of these items? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines!

---

**Last Updated**: April 2026  
**Status**: Active Development
