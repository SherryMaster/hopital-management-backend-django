# Contributing to Hospital Management API

We love your input! We want to make contributing to Hospital Management API as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/hospital-management-api.git
   cd hospital-management-api
   ```

2. **Set up development environment**
   ```bash
   python -m venv hospital_env
   source hospital_env/bin/activate  # On Windows: hospital_env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up pre-commit hooks** (optional but recommended)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Run tests to ensure everything works**
   ```bash
   python manage.py test
   ```

## Coding Standards

### Python Code Style
- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Maximum line length: 88 characters (Black formatter standard)

### Django Best Practices
- Use Django's built-in features when possible
- Follow Django naming conventions
- Use proper model relationships
- Implement proper error handling

### API Design
- Follow RESTful principles
- Use proper HTTP status codes
- Implement consistent error responses
- Add comprehensive API documentation

## Testing

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test patients

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Writing Tests
- Write tests for all new features
- Maintain test coverage above 80%
- Use Django's TestCase for database-related tests
- Use factory_boy for test data generation

### Test Structure
```
tests/
├── test_models.py          # Model tests
├── test_views.py           # View/API tests
├── test_serializers.py     # Serializer tests
├── test_utils.py           # Utility function tests
└── factories.py            # Test data factories
```

## Documentation

### Code Documentation
- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Document complex algorithms and business logic

### API Documentation
- Use drf-spectacular decorators for API documentation
- Add examples for request/response bodies
- Document all query parameters and filters

## Commit Messages

Use clear and meaningful commit messages:

```
feat: add patient search functionality
fix: resolve appointment scheduling conflict
docs: update API documentation for billing
test: add integration tests for medical records
refactor: optimize database queries in patient views
```

### Commit Message Format
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

## Issue Reporting

### Bug Reports
When filing a bug report, please include:

1. **Environment details**
   - Python version
   - Django version
   - Database type and version
   - Operating system

2. **Steps to reproduce**
   - Clear, numbered steps
   - Expected behavior
   - Actual behavior

3. **Additional context**
   - Error messages
   - Screenshots (if applicable)
   - Related issues

### Feature Requests
When proposing a new feature:

1. **Use case description**
   - Why is this feature needed?
   - Who would benefit from it?

2. **Proposed solution**
   - How should it work?
   - Any implementation ideas?

3. **Alternatives considered**
   - What other approaches were considered?

## Security

### Reporting Security Issues
Please do not report security vulnerabilities through public GitHub issues. Instead, send an email to security@hospital-api.com with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Best Practices
- Never commit sensitive data (passwords, API keys, etc.)
- Use environment variables for configuration
- Follow OWASP guidelines for web application security
- Implement proper input validation and sanitization

## Code Review Process

### For Contributors
- Ensure your code follows the coding standards
- Write comprehensive tests
- Update documentation as needed
- Respond to review feedback promptly

### For Reviewers
- Be constructive and respectful
- Focus on code quality and maintainability
- Check for security implications
- Verify test coverage

## Release Process

1. **Version Numbering**
   - Follow Semantic Versioning (SemVer)
   - Format: MAJOR.MINOR.PATCH

2. **Release Checklist**
   - All tests pass
   - Documentation is updated
   - CHANGELOG.md is updated
   - Version numbers are bumped

## Community Guidelines

### Be Respectful
- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully

### Be Collaborative
- Help others learn and grow
- Share knowledge and best practices
- Provide helpful feedback

## Getting Help

- **Documentation**: Check the README and API docs first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Email**: Contact maintainers at maintainers@hospital-api.com

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Hospital Management API! 🏥❤️
