# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.4.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in HAIR, please report it responsibly.

**Do not open a public issue.** Instead, email **david.a.bailey@gmail.com** with:

- A description of the vulnerability
- Steps to reproduce
- The potential impact
- Any suggested fix (optional)

You should receive an acknowledgment within 48 hours. We will work with you to
understand the issue and coordinate a fix before any public disclosure.

## Scope

HAIR is a Home Assistant custom integration that runs locally on your HA
instance. It does not make external network requests or store data outside your
HA installation. Security concerns most likely relate to:

- WebSocket API input validation
- Signal store data integrity
- Frontend XSS vectors
- Config flow input handling
