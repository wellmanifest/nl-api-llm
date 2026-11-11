# Ticket 008: Modularize nl_api_llm under 500 lines and fix HTML XSS, symlink/JSON I/O, and query bounds

- **ID**: ticket-008
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: On 2026-11-11 user authorized auditing, fixing bugs, optimizing, and hardening `wellmanifest/*` standard repositories.

Modularize the 1,146-line `standard/nl_api_llm.py` monolith into focused modules strictly below 500 lines (`standard/nl_api_models.py`, `standard/nl_api_menu.py`, `standard/nl_api_matcher.py`, and `standard/nl_api_llm.py` re-exporting the full public API); eliminate stored/reflected `<script>` breakout and `innerHTML` / inline `onclick="..."` XSS in `MenuGenerator.export_html_component` via script-safe JSON escaping (`\u003c`/`\u003e`/`\u0026`/`\u2028`/`\u2029`) and `textContent` / `addEventListener` DOM construction; harden CLI and profile file I/O via `read_strict_json` (`lstat`/`fstat` inode guard, symlink-parent traversal protection before `os.path.abspath`, duplicate-key/non-finite/309-digit/lone-surrogate/depth bounds) and `write_atomic_text` (`mkstemp` + `fsync` + `os.replace`); bound natural-language query length (`<= 8192`), guard empty/punctuation-only queries against false-positive phrase matches, and prevent 5000-digit integer `ValueError` in log-line extraction; expand `standard/test_conformance.py`; and mark merged `project/ticket-006/README.md` and `project/ticket-007/README.md` `DONE`.

## Acceptance criteria

- [x] AC-01: Split `standard/nl_api_llm.py` (`1146L`) into `nl_api_models.py`, `nl_api_menu.py`, `nl_api_matcher.py`, and `nl_api_llm.py` with every `standard/*.py` module strictly `< 500` lines and full public backward compatibility, and mark `project/ticket-006/README.md` and `project/ticket-007/README.md` `DONE`.
- [x] AC-02: Eliminate `</script>` and `innerHTML`/`onclick` XSS in `export_html_component`, enforce bounded regular-file/non-symlink JSON reading and atomic writing, clamp huge digit strings in `NLIntentMatcher.parse`, and pass `ruff check --no-cache standard`, `pytest -q`, `python3 standard/nl_api_llm.py --self-test`, `python3 .governance/standard_pack_check.py --root .`, `./project/governance-check.sh --base origin/main`, and `wellman check` with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
