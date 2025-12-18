# Contributing to Blue Psychology Test Bot

Thank you for your interest in contributing to Blue Psychology Test Bot! 🎉

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/blue-psychology-test.git
   cd blue-psychology-test
   ```

3. **Set up development environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow existing code style
   - Add tests if applicable

3. **Test your changes**
   ```bash
   # Run tests
   pytest tests/
   
   # Test specific functionality
   python test_profile_extractor.py
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Describe your changes

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Comment complex logic

## Commit Message Convention

Use conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example:
```
feat: add voice input support for psychology tests
fix: resolve memory leak in profile extraction
docs: update API documentation
```

## Testing

- Write tests for new features
- Ensure existing tests pass
- Test edge cases
- Test with different configurations

## Documentation

- Update README.md if needed
- Document new API endpoints
- Add inline comments for complex logic
- Update .env.example for new variables

## Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Provide clear description of changes
- Reference related issues
- Ensure all tests pass
- Update documentation as needed

## Reporting Issues

When reporting issues, please include:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant logs or error messages

## Questions?

Feel free to open an issue for questions or discussions!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
