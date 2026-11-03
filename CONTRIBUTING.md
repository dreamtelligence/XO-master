# 🤝 Contributing to AI Music Studio Platform

First off, thank you for considering contributing to this project! This is primarily a portfolio project, but I welcome contributions that improve the platform, fix bugs, or add valuable features.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Development Process](#development-process)
4. [Pull Request Guidelines](#pull-request-guidelines)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)

---

## Code of Conduct

This project and everyone participating in it is governed by respect, professionalism, and collaboration. By participating, you are expected to uphold these values.

**Expected Behavior:**
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**When submitting a bug report, include:**
- **Clear title** describing the issue
- **Steps to reproduce** the problem
- **Expected behavior** vs actual behavior
- **Screenshots** if applicable
- **Environment details**:
  - Browser (Chrome, Firefox, Safari, etc.)
  - Operating System
  - Relevant error messages or logs

**Example:**
```markdown
## Bug: Credit deduction fails after service completion

**Steps to reproduce:**
1. Upload audio file to Music Separation service
2. Wait for processing to complete
3. Download stems
4. Check credit balance

**Expected:** Credits should decrease by 1
**Actual:** Credits remain unchanged

**Environment:**
- Browser: Chrome 120.0
- OS: macOS 14.1
- User ID: user_123

**Logs:**
```
Error: Failed to deduct credits: insufficient balance
```
```

### 💡 Suggesting Features

Feature suggestions are welcome! Please provide:

- **Clear description** of the feature
- **Use case** - why is this valuable?
- **Implementation ideas** (optional)
- **Mockups or examples** (optional)

**Example:**
```markdown
## Feature: Batch Audio Processing

**Description:**
Allow users to upload multiple audio files and process them in a queue.

**Use Case:**
Musicians often need to process entire albums (10-15 tracks). Currently, they must upload files one by one, which is time-consuming.

**Proposed Implementation:**
- Add "Upload Multiple" button
- Show queue UI with progress indicators
- Process files sequentially on Modal
- Download all results as ZIP

**Benefits:**
- Saves user time
- Increases credit usage per session
- Improves user experience
```

### 🔧 Contributing Code

**Areas where contributions are especially welcome:**

1. **Frontend Enhancements**
   - UI/UX improvements
   - Mobile responsiveness
   - Accessibility (WCAG compliance)
   - Performance optimizations

2. **Backend Improvements**
   - API optimization
   - Error handling
   - Database query performance
   - Security enhancements

3. **AI/ML Features**
   - New AI models integration
   - Model parameter tuning
   - GPU optimization
   - Quality improvements

4. **Documentation**
   - Code comments
   - API documentation
   - Tutorial videos
   - Translation (German, Spanish, etc.)

5. **Testing**
   - Unit tests
   - Integration tests
   - E2E tests
   - Performance benchmarks

---

## Development Process

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/<your-username>/XO-master.git
cd XO-master

# Add upstream remote
git remote add upstream https://github.com/dreamtelligence/XO-master.git
```

### 2. Create a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

**Branch Naming Convention:**
- `feature/` - New features (e.g., `feature/batch-processing`)
- `fix/` - Bug fixes (e.g., `fix/credit-deduction`)
- `docs/` - Documentation (e.g., `docs/api-reference`)
- `refactor/` - Code refactoring (e.g., `refactor/audio-service`)
- `test/` - Adding tests (e.g., `test/payment-flow`)

### 3. Set Up Development Environment

Follow the [SETUP.md](./docs/SETUP.md) guide to configure your local environment.

```bash
# Install dependencies
npm install
pip install modal

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
psql -h [SUPABASE_HOST] -U postgres -f supabase_credit_schema.sql

# Start dev server
npm run dev
```

### 4. Make Your Changes

**Before coding:**
- Check if there's an existing issue or PR for this change
- Discuss major changes in an issue first
- Follow the coding standards (see below)

**While coding:**
- Write clear, commented code
- Add tests for new functionality
- Update documentation as needed
- Test your changes thoroughly

### 5. Commit Your Changes

**Commit Message Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, no logic change)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**
```bash
git commit -m "feat(separation): Add support for 6-stem separation model"

git commit -m "fix(credits): Resolve race condition in credit deduction

- Add database transaction lock
- Implement retry logic
- Add tests for concurrent requests

Fixes #42"

git commit -m "docs(setup): Add troubleshooting section for Modal deployment"
```

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Create Pull Request

1. Go to [github.com/dreamtelligence/XO-master](https://github.com/dreamtelligence/XO-master)
2. Click "Pull Requests" → "New Pull Request"
3. Select your fork and branch
4. Fill in the PR template (see below)

---

## Pull Request Guidelines

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issue
Fixes #(issue number)

## How Has This Been Tested?
Describe the tests you ran to verify your changes.

- [ ] Test A
- [ ] Test B

## Screenshots (if applicable)
Add screenshots to help explain your changes.

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
```

### PR Review Process

1. **Automated Checks** (when CI/CD is set up):
   - Linting passes
   - Tests pass
   - Build succeeds

2. **Code Review**:
   - I'll review your code within 1-3 days
   - May request changes or ask questions
   - Please respond to feedback

3. **Approval & Merge**:
   - Once approved, I'll merge your PR
   - Your contribution will be credited in releases

---

## Coding Standards

### JavaScript / Frontend

**Style Guide:**
- Use ES6+ features (const/let, arrow functions, template literals)
- 2-space indentation
- Semicolons required
- Single quotes for strings
- Meaningful variable names

**Example:**
```javascript
// ✅ Good
const audioService = {
  async processAudio(file, options) {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(ENDPOINT, {
        method: 'POST',
        body: formData
      })
      return await response.json()
    } catch (error) {
      console.error('Processing failed:', error)
      throw error
    }
  }
}

// ❌ Bad
var audioService={processAudio:function(file,options){formData=new FormData();formData.append("file",file);fetch(ENDPOINT,{method:"POST",body:formData}).then(r=>r.json())}}
```

### Python / Backend

**Style Guide:**
- Follow PEP 8
- 4-space indentation
- Type hints for function signatures
- Docstrings for all functions
- Max line length: 100 characters

**Example:**
```python
# ✅ Good
def separate_audio(
    audio_bytes: bytes,
    model: str = "stems",
    use_tta: bool = False
) -> dict[str, bytes]:
    """
    Separates audio into stems using specified model.

    Args:
        audio_bytes: Input audio file as bytes
        model: Model key ("stems" = SCNet XL IHF, "vocals" = Mel-Band RoFormer)
        use_tta: Test-time augmentation (better quality, about twice as slow)

    Returns:
        Dictionary mapping stem names to audio bytes

    Raises:
        ValueError: If model is not supported
        RuntimeError: If GPU processing fails
    """
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model: {model}")

    try:
        return run_separation(audio_bytes, model, use_tta=use_tta)
    except torch.cuda.OutOfMemoryError:
        logger.warning("GPU OOM, retrying without TTA")
        return run_separation(audio_bytes, model, use_tta=False)

# ❌ Bad
def separate(a,m="stems",t=False):
    return run_separation(a,m,t)
```

### SQL / Database

**Style Guide:**
- UPPERCASE keywords
- Lowercase table/column names
- Indent nested queries
- Always use explicit JOIN syntax

**Example:**
```sql
-- ✅ Good
SELECT
    u.id,
    u.email,
    u.credits,
    COUNT(p.id) AS total_purchases,
    SUM(p.credits) AS lifetime_credits
FROM credit_users u
LEFT JOIN credit_purchases p ON u.id = p.user_id
WHERE u.created_at > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.email, u.credits
ORDER BY lifetime_credits DESC;

-- ❌ Bad
select * from credit_users,credit_purchases where credit_users.id=credit_purchases.user_id;
```

---

## Testing Guidelines

### Frontend Testing

```javascript
// Example: Test credit manager
describe('CreditManager', () => {
  let creditManager

  beforeEach(() => {
    creditManager = new CreditManager()
  })

  test('should fetch user balance', async () => {
    const balance = await creditManager.getBalance('user_123')
    expect(balance.credits).toBeGreaterThanOrEqual(0)
  })

  test('should deduct credits after service use', async () => {
    const before = await creditManager.getBalance('user_123')
    await creditManager.deductCredits('user_123', 'separation', 'job_456')
    const after = await creditManager.getBalance('user_123')
    expect(after.credits).toBe(before.credits - 1)
  })
})
```

### Backend Testing

```python
# Example: Test Modal function
import pytest
from modal_app_zfturbo_complete import separate_audio

def test_separate_audio_success():
    """Test audio separation with valid input."""
    with open('test_audio.mp3', 'rb') as f:
        audio_bytes = f.read()

    result = separate_audio(audio_bytes, model='stems')

    assert 'vocals' in result
    assert 'drums' in result
    assert 'bass' in result
    assert 'other' in result
    assert len(result['vocals']) > 0

def test_separate_audio_invalid_model():
    """Test error handling for invalid model."""
    with open('test_audio.mp3', 'rb') as f:
        audio_bytes = f.read()

    with pytest.raises(ValueError, match="Unsupported model"):
        separate_audio(audio_bytes, model='invalid_model')
```

### Integration Testing

```bash
# Test full payment flow
curl -X POST http://localhost:3000/api/create-checkout-session \
  -H "Content-Type: application/json" \
  -d '{"packageType":"starter"}'

# Test webhook handling
stripe trigger checkout.session.completed

# Verify credit allocation
curl http://localhost:3000/api/credits?userId=user_123
```

---

## Documentation

### Code Comments

**When to comment:**
- Complex algorithms
- Non-obvious business logic
- Performance optimizations
- Workarounds for known issues

**Example:**
```javascript
// Process audio in segments to avoid GPU memory overflow
// Segment size of 25 provides optimal quality-speed tradeoff on A10G
const SEGMENT_SIZE = 25

// Use 2 shifts for ensemble prediction (improves SDR by ~0.5dB)
// See: https://github.com/ZFTurbo/MSSR/issues/42
const NUM_SHIFTS = 2
```

### API Documentation

Use JSDoc/docstrings for all public functions:

```javascript
/**
 * Processes audio file through AI separation service
 *
 * @param {File} audioFile - Audio file to process
 * @param {Object} options - Processing options
 * @param {string} options.model - Model key ('stems' = SCNet XL IHF, 'vocals' = Mel-Band RoFormer)
 * @param {boolean} options.useTta - Test-time augmentation (default: false)
 * @returns {Promise<Object>} Separated audio stems
 * @throws {Error} If processing fails or credits insufficient
 *
 * @example
 * const stems = await processAudio(file, {
 *   model: 'stems',
 *   useTta: false
 * })
 */
async function processAudio(audioFile, options) {
  // Implementation
}
```

---

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- Release notes
- README acknowledgments section

**Thank you for contributing to make this project better!**

---

## Questions?

If you have questions about contributing:
- Open an issue with the `question` label
- Reach out via email: [Your email if you want to provide it]
- Check existing documentation in `/docs`

**Happy coding!** 🎵
