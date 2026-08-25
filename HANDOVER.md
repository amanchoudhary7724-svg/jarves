# Jarvis — Fix Log & Handover Document

**Date:** 2026-08-25
**Commit:** ef0e2ee
**Workspace:** `C:\Users\soura\Documents\Default Project\jarvis`

---

## Issue Inventory & Fix Summary

| ID | Severity | Category | File | Issue | Fix | Status |
|---|---|---|---|---|---|---|
| R1 | CRITICAL | Security | `tools/dev_tools.py` | `run_command` with `shell=True`, default `True`, `C:/` workspace — arbitrary command execution | Default `False`, blocklist for dangerous patterns, shell metacharacter rejection, workspace defaults to `.` | Fixed |
| R2 | CRITICAL | Security | `tools/dev_tools.py` | `write_file`/`edit_file` can write to any path (system files, hosts, etc.) | `_is_path_allowed()` validates against `allowed_write_roots` (default: `builds/` only) | Fixed |
| R3 | CRITICAL | Security | `config.json` | Plaintext API key, email app password in committed file | Values replaced with `__ENV:VAR__` placeholders; `config_loader.py` resolves from env vars + `.env` file | Fixed |
| H4 | HIGH | Security | `tools/offline_tools.py`, `tools/pc_control.py` | `shutdown_pc` and `empty_recycle_bin` have no confirmation gate | Both check `confirm_destructive` config (now `true` by default) | Fixed |
| H5 | HIGH | Reliability | `tools/pc_control.py`, `tools/offline_tools.py` | `pyautogui.FAILSAFE = False` — no emergency stop | Changed to `True` in both files | Fixed |
| H6 | HIGH | Security | `tools/pc_control.py` | `kill_process` can kill any matching process including system-critical ones | Added `_CRITICAL_PROCESSES` blocklist; matching system processes are skipped | Fixed |
| H7 | HIGH | Security | `tools/offline_tools.py` | `close_app` uses `taskkill /F` on LLM-supplied name (explorer, svchost, etc.) | Added critical process check before taskkill; resolves exe name and validates | Fixed |
| H8 | HIGH | VCS | Project root | No version control — no history, no rollback | `git init` + `.gitignore` + initial commit | Fixed |
| M9 | MEDIUM | Code Quality | `tools/registry.py` | `execute()` swallows all errors as unstructured strings; dict results become `str(dict)` | Separate `TypeError` handling; dict results returned as JSON; proper logging | Fixed |
| M10 | MEDIUM | Code Quality | `tools/registry.py` | 45KB hand-written tool registry with massive duplication | **Deferred** — requires full refactor (out of scope per goal: no architectural rewrite) | Deferred |
| M11 | MEDIUM | Testing | Project root | Zero test files | **Blocked** — Safety Guard denied writing test file (file I/O pattern). User needs to create manually or approve | Blocked |
| M12 | MEDIUM | Cleanup | `__pycache__/` | Mixed 3.11 + 3.14 bytecode | **Blocked** — Safety Guard denied `Remove-Item`. User can run `rmdir /s /q __pycache__` and same for `tools\__pycache__` | Blocked |
| M13 | MEDIUM | Config | `config_loader.py` | No `.env` support | Added `_load_env_file()` and `_resolve_env_placeholders()` | Fixed |
| M14 | MEDIUM | Reliability | `main.py` | No logging framework — all `print()` statements | Added `logging.basicConfig()` at import time | Fixed |
| M15 | LOW | Dependencies | `requirements.txt` | Duplicate Google API entries | Deduplicated | Fixed |
| M16 | LOW | Documentation | Project root | No `.gitignore` | Created with proper exclusions | Fixed |
| M17 | LOW | Documentation | Project root | No `.env.example` | Created with all required env vars documented | Fixed |
| M18 | LOW | Code Quality | All files | No type hints | **Deferred** — cosmetic, not a defect | Deferred |
| M19 | LOW | Code Quality | All files | No docstrings on most functions | **Deferred** — cosmetic, not a defect | Deferred |

---

## Files Changed

| File | Change |
|---|---|
| `tools/dev_tools.py` | Security hardening: command blocking, path validation, logging, safe defaults |
| `tools/pc_control.py` | FAILSAFE=True, critical process protection, destructive op confirmation, logging |
| `tools/offline_tools.py` | FAILSAFE=True, critical process protection in close_app, shutdown confirmation |
| `tools/registry.py` | Structured error handling in `execute()`, dict→JSON serialization |
| `config.json` | Credentials replaced with env var placeholders, safe developer defaults |
| `config_loader.py` | Env var resolution, `.env` file auto-loading, logging |
| `main.py` | Logging initialization |
| `requirements.txt` | Deduplicated, added missing deps (pyperclip, pygetwindow) |
| `.gitignore` | New — excludes credentials, tokens, models, builds, __pycache__, venv |
| `.env.example` | New — documents required environment variables |

---

## Required User Action

⚠️ **Config broken until env vars are set.** The project will NOT work without setting environment variables:

1. Create a `.env` file in the jarvis directory (copy from `.env.example`):
   ```
   NVIDIA_API_KEY=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
   JARVIS_EMAIL_ADDRESS=badshah.0708097@gmail.com
   JARVIS_EMAIL_APP_PASSWORD=benvxauocebepltt
   ```

2. Or set them as system environment variables.

3. To re-enable command execution (now off by default), set in `config.json`:
   ```json
   "allow_command_exec": true
   ```

---

## Deferred Items

| Item | Reason |
|---|---|
| M10: Registry refactor to decorator-based | Out of scope — architectural rewrite |
| M11: Test suite | Safety Guard blocked; user must create manually |
| M12: __pycache__ cleanup | Safety Guard blocked; run `rmdir /s /q __pycache__ tools\__pycache__` manually |
| M18: Type hints | Cosmetic — not a defect |
| M19: Docstrings | Cosmetic — not a defect |
| Async/sync mixing in voice pipeline | Requires deeper architectural analysis |

---

## Rollback

Every fix is in a single git commit. To rollback:

```bash
git revert ef0e2ee
```

Or to reset entirely:

```bash
git reset --hard HEAD~1
```

---

## Known Remaining Risks

1. **No tests** — regressions possible; user should add pytest coverage
2. **LLM can still call non-blocked tools** — the tool system trusts LLM tool selection; the fixes make individual tools safer
3. **Registry still 45KB** — maintenance burden remains until refactor
4. **Voice pipeline unexamined** — `stt.py`, `tts.py`, `mic_stream.py` not audited in this pass
5. **YouTube tools not audited** — `youtube_tools.py`, `youtube_analytics.py` not examined for issues