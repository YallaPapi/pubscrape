# 🔐 Security Guidelines

## API Key Protection

**CRITICAL**: This project uses API keys that must be kept secure. Follow these guidelines:

### ✅ DO:
- Copy `.env.example` to `.env` and add your real API keys there
- Keep your `.env` file private and never share it
- Use individual API keys with minimal required permissions
- Regularly rotate your API keys
- Monitor API usage for unusual activity

### ❌ DON'T:
- Never commit `.env` files to version control
- Never share API keys in chat, email, or public forums
- Never hardcode API keys in source code
- Never use production keys for testing

## Current API Keys Required

### Core Functionality:
- **YouTube Data API**: For podcast discovery on YouTube
- **OpenAI API**: For AI analysis and guest scoring
- **Google Drive API**: For CSV file uploads

### Enhanced Features:
- **Hunter.io**: Email discovery (25 free searches/month)
- **Apollo.io**: Contact enrichment (120 free credits/month)
- **Perplexity API**: Research capabilities via TaskMaster

### Optional:
- **Anthropic API**: Claude models for advanced analysis
- **OpenRouter API**: Access to multiple AI models

## Getting API Keys

1. **YouTube Data API**: [Get free key](https://developers.google.com/youtube/v3/getting-started)
2. **OpenAI API**: [Get key](https://platform.openai.com/api-keys) (requires payment)
3. **Hunter.io**: [Free account](https://hunter.io/users/sign_up) (25 searches/month)
4. **Apollo.io**: [Free account](https://app.apollo.io) (120 credits/month)

## Emergency Response

If API keys are accidentally exposed:

1. **Immediately revoke** all exposed keys at their respective platforms
2. **Generate new keys** with minimal required permissions
3. **Update your local `.env`** file with new keys
4. **Check API usage logs** for unauthorized activity
5. **Enable monitoring/alerts** if available

## Secure Deployment

For production deployments:
- Use environment variables instead of `.env` files
- Enable API key restrictions (IP whitelist, domain restrictions)
- Use secrets management services (AWS Secrets Manager, etc.)
- Enable comprehensive logging and monitoring

## Questions?

If you suspect a security issue, contact the maintainer immediately.