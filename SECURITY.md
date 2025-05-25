# 🔐 Security Policy

## Maintainer

This repository is maintained solely by the original author (you).

Only the maintainer has push or merge access to protected branches.

---

## Branch Protection

The `main` branch is protected with the following rules:

- ✅ Direct pushes are not allowed  
- ✅ Force-pushes and deletions are disabled  
- ✅ Changes must go through a pull request  
- ✅ No approvals are required for pull requests (maintainer-only workflow)

---

## GitHub Secrets

All sensitive values (e.g., Notion API token and database IDs) are securely stored in **GitHub Secrets** and **not included in the codebase**.

- Forks and public viewers cannot access these secrets  
- No secrets are ever printed to logs or exposed through Actions

---

## Forking and Pull Requests

Forks are allowed, but:

- Workflows in forks **do not have access** to the original repository’s secrets  
- Pull requests can be submitted, but they will not trigger secret-reliant actions unless approved and merged by the maintainer  
- Any malicious or untrusted PRs will be ignored or closed

---

## Automation Behavior

This repository runs periodic Notion API updates via GitHub Actions.  
The automation is read/write only to the author’s Notion workspace, controlled by a private API token.

No external party can trigger or influence this automation process.

---

## Contact

If you discover a security vulnerability or concern, please open an issue marked as `security` (no secrets or tokens should be included in public posts).
