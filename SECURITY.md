# Security Policy for Graphite

## Supported Versions

We actively maintain and support the following Graphite versions:

| Version | Supported    | Note                 |
|---------|--------------|----------------------|
| v0.1.x  | ✅ Yes        | Supported until v1.x |
| v0.2.x  | ✅ Yes        | Supported until v1.x |
| Main    | ✅ Latest Dev |                      |

Security fixes are applied to all supported versions.

---

## Reporting a Vulnerability

If you discover a security issue in Graphite, **do not create a public issue**.

Please report it privately to the maintainers:

- **Email:** mahan.khalili.001@gmail.com

When reporting, include:

1. A detailed description of the vulnerability
2. Steps to reproduce or proof-of-concept
3. Impact assessment (if possible)
4. Affected version(s)
5. Any suggested mitigation (optional)

We will respond within 48 hours.

---

## Security Response Process

1. **Acknowledgment:** We confirm receipt of the report within 48 hours.
2. **Investigation:** The maintainers verify the issue and assess its impact.
3. **Resolution:** A fix or mitigation plan is created.
4. **Disclosure Coordination:** Coordinated disclosure is agreed upon with the reporter.
5. **Release:** Security patch is released for all supported versions.
6. **Public Advisory:** A security advisory is published in the repository and release notes.

---

## Guidelines for Contributors

- Do not commit secrets (API keys, passwords, tokens) in the repository.
- Follow secure coding practices for all features.
- Validate all input and handle errors safely.
- Dependencies must be up-to-date and maintained.
- Avoid unsafe Rust code unless strictly necessary, and document justification.

---

## Reporting Policy Abuse

If you believe someone is using Graphite to perform malicious actions or misusing security features:

- Contact the maintainers via email: mahan.khalili.001@gmail.com
- Include a detailed description and any evidence.

---

## References

- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
