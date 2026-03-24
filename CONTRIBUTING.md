# Contributing

Thank you for your interest in contributing to WiFi Quality Tester!

## Getting started

```bash
git clone https://github.com/your-username/wifi-quality-tester.git
cd wifi-quality-tester
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How to contribute

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** — keep them focused and minimal.

3. **Test manually** by running `python3 main.py` and verifying all menu options work.

4. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add Windows WiFi signal support"
   ```

5. **Open a Pull Request** against `main` with a description of what and why.

## Commit message convention

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

| Prefix | Use for |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | README / documentation only |
| `refactor:` | Code restructure, no behaviour change |
| `chore:` | Tooling, deps, config |

## Ideas for contributions

- Windows WiFi signal support (`netsh wlan show interfaces`)
- HTML/CSV export of results
- Continuous background monitoring with alerts
- Graphs of ping over time (using `plotext`)
- Auto-run on startup as a pre-meeting check
