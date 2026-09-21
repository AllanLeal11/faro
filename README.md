# faro
Personal AI scam shield with verifiable evidence and family alerts

## Security

Faro never opens or fetches links from analyzed messages, never stores
message content, and redacts card numbers/OTP codes/passwords before any
text reaches an LLM. CI runs `gitleaks`, `semgrep`, `bandit`, and
`pip-audit` on every push. See [docs/security.md](docs/security.md) for
the full threat model, implemented controls, and known gaps.
