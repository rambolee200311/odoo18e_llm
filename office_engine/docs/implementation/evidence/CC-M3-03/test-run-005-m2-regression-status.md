# M2 Regression Triage — CC-M3-03

Environment: Odoo 18 development, existing database `odoo18e_llm`; no production or other database.

## Attempts

1. Normal module test discovery for `/office_engine_m2` stopped while importing `addons/auditlog/tests/common.py`:

   ```text
   ImportError: cannot import name 'SETATTR_SOURCES' from 'odoo.tests.common'
   ```

   Archived raw output: `test-run-005-m2-regression-normal-import.log` (SHA-256 `8639efab43a4c5c3263eebbda5c96f74f6bc49539c4123749a46ba2ef2b5be96`).

2. A local compatibility shim allowed the test runner to continue. The full run reported **13 failures and 69 errors out of 208 tests**. Triage of the recorded results:

   - **67 errors** end in `OfficeCoreError: Office 处理进程异常退出。` from OfficeCore's isolated worker. The captured cause is `multiprocessing` receiving `EOFError` on the worker pipe (`office_core/service.py`, `_run_worker`). The worker intentionally hides internal tracebacks; the log therefore proves abrupt worker exit but not why the child exited. These errors occur across M2 tests which call the same OfficeCore inspect/render path.
   - **12 of 13 failures** follow the worker failures in the recorded paths: Candidate verification fails closed, so assertions expecting a reviewable Candidate, successful fileless V1, or subsequent edit state fail. The chained fileless-current `AccessError` follows a failed create and is retained as a raw test error; its initiating worker exit remains unexplained.
   - **1 additional failure and 1 setup error** belong to cross-company access tests whose fixtures require a second company. The frozen CC-M3-03 scope does not require a second company or cross-company fixture, so these two test outcomes are **N/A for this CC**. They are not counted as M3 regressions or acceptance blockers.

   The CC-M3-03 source changes are in `office_engine_m3`; this CC did not modify `office_engine_m2` or `office_core`. The worker error stacks terminate in the existing OfficeCore process boundary and do not show an M3 frame. No pre-change full-suite baseline exists, so the **67 worker exits remain unexplained and are not classified as environmental or as M3 regressions**. This full run remains non-green and is preserved as raw evidence; it is not represented as a passing M2 suite.

3. Ran a focused M2 regression using an isolated compatibility shim and the same existing `odoo18e_llm` database. The selection covered the full `TestWorkbookVersionState` class plus `TestNativeOfficeChatIntegration.test_fileless_xlsx_request_binds_route_b_tools_for_create_and_followup_turns`: **12 tests, 0 failures, 0 errors**. This validates Candidate / Accept / Finalize version behavior and the no-upload Route B export-tool binding, but does not replace the full M2 suite.

   Evidence: `test-run-007-targeted-m2-regression.log`. The temporary runner and log were under `/tmp`; the runner only patched the missing test-framework constant in memory and did not change repository or database configuration.

   Archived raw output: `test-run-005-m2-regression-full-compat.log` (SHA-256 `7f5757447b57e597ec5a5e721b37165b32ee5efefd5fd7b1b77b30bcdb2a0fdc`). The file is copied byte-for-byte from the original `/tmp` run log; it retains the worker `EOFError` traces.

## Disposition

No M2 or OfficeCore code/test was changed to force a pass. The M3 suite passed 42/42 tests; the focused M2 regression passed 12/12; and the real HVR completed Candidate → explicit Accept → Finalize. **Proposed TEST-REG-001 conclusion: PASS (scope-limited; no CC-M3-03 regression identified)** based on these in-scope checks. The raw full M2 suite remains non-green at 13 failures / 69 errors; worker exits remain unclassified, and the two second-company-dependent test outcomes are N/A to this CC. This conclusion does not claim the M2 full suite passed.
