# Development Guide

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/e_wallet.git`
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Set up development environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Code Style

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small

## Testing

Before submitting a PR:
```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=backend

# Run linting
flake8 backend/ tests/

# Type checking (if enabled)
mypy backend/
```

## Commit Messages

Use clear, descriptive commit messages:
```
[feature] Add mint flow
[fix] Correct balance calculation
[docs] Update API documentation
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Request review from maintainers
5. Address feedback
6. Squash commits if requested

## Reporting Issues

- Check existing issues first
- Use bug report template
- Include Python version and OS
- Provide minimal reproduction steps
- Include error messages and logs

## Questions?

Open a discussion or issue with the `question` label.
