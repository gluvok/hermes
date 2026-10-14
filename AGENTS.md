# AGENTS.md

Behavioral guidelines to eliminate common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines prioritize absolute correctness, safety, and architectural cleanliness over speed.

---

## 1. Think Before Coding

**Never assume. Never hide confusion. Surface tradeoffs upfront.**

Before writing any code:
- State assumptions explicitly. If uncertain, stop and ask.
- If multiple interpretations exist, present them - never pick silently.
- If a simpler approach exists, say so. Push back against complexity.
- If something is unclear or under-specified, stop immediately. Name what is confusing and request clarification.

---

## 2. Simplicity First (Absolute Prohibition on Speculative Code)

**Write only the minimum code required to solve the immediate problem. Speculation is strictly forbidden.**

- Absolutely no features beyond what was explicitly requested.
- Absolutely no abstractions or utility wrappers for single-use code.
- Absolutely no speculative "flexibility," "extensibility," or "configurability."
- Absolutely no defensive error handling for impossible scenarios.
- If an implementation can be done in 30 lines instead of 100, rewrite it immediately.
- Ask: "Would a principal engineer say this is overengineered?" If yes, simplify.

---

## 3. Surgical Changes & Zero Unrelated Churn

**Touch strictly what you must. Clean up your own mess immediately.**

When editing existing code:
- Never "improve," reformat, or re-comment adjacent code unless directly instructed.
- Never refactor working components outside the task scope.
- Match existing style and idioms precisely.
- If unrelated dead code is discovered, mention it in your response - do not delete it in the same change.

When your changes create orphans:
- Immediately remove all imports, variables, functions, and models that YOUR changes made unused.
- Do not leave unused imports or dead references behind.

The Golden Test: **Every single changed line in a diff must trace directly to the user's prompt.**

---

## 4. Goal-Driven Execution

**Define verifiable success criteria. Loop independently until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write unit tests for invalid inputs, then make them pass."
- "Fix the bug" → "Write a reproduction test, then make it pass."
- "Refactor X" → "Ensure full test suite passes before and after."

For multi-step tasks, state a verifiable plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Loop independently against concrete criteria. Never claim completion without running verification.

---

## 5. Python Quality & Verification Gates (Non-Negotiable)

**The 3 verification gates are absolute law. All three must pass with 0 errors and 0 warnings.**

For any Python modifications, the following loop must be enforced iteratively:
1. **Lint & Code Style**: Run `uv run ruff check --fix`. All checks must pass cleanly.
2. **Type Checking**: Run `uv run ty check`. All diagnostics must be resolved cleanly.
3. **Test Suite**: Run `uv run pytest`. All unit and integration tests must pass with 100% success.
4. **Zero-Tolerance Suppression Ban**:
   - Strictly prohibited from using `# noqa` or `# ruff: noqa` to suppress lint errors.
   - Strictly prohibited from using `# type: ignore` to bypass typing checks.
   - Strictly prohibited from marking failing tests as `@pytest.mark.skip` or `xfail` to fake a pass.
   - Every lint issue and type error must be solved cleanly at the root cause.

**The 3 mandatory commands that must always exit with code 0:**
- `uv run ruff check --fix` (0 errors, 0 warnings)
- `uv run ty check` (0 errors, 0 warnings)
- `uv run pytest` (all tests pass)

---

## 6. Update Documentation (`docs/` and `README.md`)

**Documentation must remain in continuous sync with codebase changes.**

- Explicitly update `README.md` and relevant guides in `docs/` (such as `docs/ARCHITECTURE.md`) whenever adding, modifying, or removing features, API endpoints, environment variables, architecture patterns, dependencies, or workflows.
- Keep setup instructions, configuration options, usage examples, and architectural diagrams accurate and up to date in the same turn.

---

## 7. Dependency Management via `uv`

**Always use `uv` commands. Never manually edit `pyproject.toml` dependencies.**

- Use `uv add <package>` to install and record new dependencies.
- Use `uv remove <package>` to uninstall and remove dependencies.
- Strictly prohibited from manually editing `dependencies` or `dependency-groups` arrays in `pyproject.toml`; let `uv` manage lockfile synchronization (`uv.lock`) and environment state.

---

## 8. No Backward-Compatibility Shims (Absolute Strictness)

**Zero tolerance for backward-compatibility code, forwarding wrappers, or defensive shims.**

- **Immediate Deletion of Superseded Code**:
  - When replacing a function, class, pattern, or module, **delete the old implementation immediately**.
  - Strictly prohibited from leaving legacy forwarding wrappers, procedural aliases, or duplicate dispatch layers (e.g. leaving procedural `_scan_crops` to call `Strategy.scan_crops`).
  - Strictly prohibited from alias pointers (`old_name = new_name`).
- **No Defensive / Dual-Type Parameter Shims**:
  - Never introduce union parameters (`x: tuple | BoundingBox` or `data: dict | Model`) solely so old test fixtures or legacy callers don't fail.
  - Never add runtime type branching (`if isinstance(x, dict): ...`) to handle obsolete formats.
- **Production Dictates Tests, Never the Reverse**:
  - Production code defines the clean architectural contract.
  - If an existing test fails because it imports a deleted function, targets a deleted module, patches an obsolete namespace, or passes outdated mock structures, **update the test to match the clean production contract immediately**.
  - **Never compromise or bend production signatures, types, or architectures backward to satisfy stale test mocks.**
- **No Phased or Transitional Deprecations**:
  - Refactors in this codebase are atomic. Strictly prohibited from adding `DeprecationWarning`, fallback adapters, or transitional shims. Migrate all callers and tests in the exact same atomic change.

---

## 9. NASA JPL Rule 4: Single Sheet of Paper Architecture (≤ 60 Lines)

**Every file and function must fit on a single printed sheet of standard paper.**

Derived from Gerard J. Holzmann's NASA JPL *Power of 10* safety-critical code rules (Rule 4):
- **Function Limit**: No function may exceed **60 lines of code**.
- **Module Limit**: Service files must be compact and single-purpose, targeting **≤ 60 lines per file** (hard ceiling of 60 lines).
- **One Substantive Class Per File**: When introducing patterns with multiple concrete classes (strategies, specifications, rules, adapters), **never pack multiple sibling classes into a single file**. Place each class in its own dedicated file inside a structured subpackage (e.g., `src/services/ocr/strategies/fast_alpr.py`, `src/services/ocr/strategies/rapidocr.py`).
- **Absolute Prohibition on Code Golfing**:
  - Strictly prohibited from compressing syntax, removing empty lines, stripping docstrings, joining statements with semicolons/commas, or squeezing multiple classes to beat the 60-line ceiling.
  - If a file approaches 50+ lines due to multiple classes or concerns, **the only acceptable solution is structural decomposition into a subfolder with an `__init__.py` facade**.
- **Subpackage Hierarchy**: Decompose multi-step or multi-concern domains into structured subpackages (e.g. `app/services/detector/`, `app/services/ocr/`, `app/services/plate_rules/`) rather than large monolithic files.
- **Single Cohesive Concern**: Each module must do one thing (e.g. geometry, occupancy policy, enhancement, spatial clustering).
- **Harmony with Surgical Changes (§3)**: Apply this standard to new or refactored components; do not arbitrarily refactor untouched adjacent code unless requested.

---

## 10. Python 3.14 Standards & Modern Idioms

**Write native Python 3.14 code. Leverage modern typing and runtime enhancements.**

- **PEP 649 Deferred Evaluation of Annotations**:
  - Never use string quotes for forward references (e.g. use `def add(node: Node) -> Node:`, not `'Node'`).
  - Strictly prohibited from using `from __future__ import annotations`.
- **PEP 695 Type Parameter Syntax**:
  - Prefer the `type` statement for type aliases (e.g. `type TokenMap = dict[str, str]`).
  - Use native generic parameter syntax for functions and classes (`class Pipeline[T]:`, `def process[T](item: T) -> T:`).
- **Modern Collections & Unions**:
  - Exclusively use built-in collection types (`list`, `dict`, `tuple`, `set`) and pipe unions (`str | None`, `int | float`).
  - Strictly prohibited from importing `List`, `Dict`, `Optional`, or `Union` from `typing`.

---

## 11. Code Modularization Protocol & Master Prompt

**Systematically decompose monolithic code into compact, cohesive modules.**

When breaking down large files, services, or functions:
1. **Target Single Concerns**: Map responsibilities into dedicated subpackages (e.g., `app/services/<domain>/`).
2. **One Class Per File in Subpackages**: Never pack sibling classes into a single module. Use dedicated subfolders with an `__init__.py` facade.
3. **Enforce NASA JPL Rule 4**: Every resulting file and function must be strictly ≤ 60 lines without code golfing.
4. **FastAPI & Async Conventions**:
   - Use `Annotated[..., Depends(...)]` for all parameter and dependency declarations.
   - Attach route prefixes, tags, and shared dependencies directly to `APIRouter(...)`.
   - Keep route handlers thin; delegate all business logic to service layers.
   - Use regular `def` for synchronous/CPU-bound tasks, `async def` only for non-blocking I/O, and `asyncer` when bridging.
5. **Standard Modularization Master Prompt**:
   Use the following structured prompt for LLMs or subagents performing refactoring:

   ```markdown
   ### Role & Context
   Senior Python Architect enforcing Python 3.14, FastAPI conventions, and NASA JPL Rule 4.

   ### Objectives
   1. Decompose: Break monolithic code into cohesive, single-responsibility files (≤ 60 lines each). Use subfolders (`<domain>/<subpackage>/`) with one substantive class per file.
   2. Modernize: Apply Python 3.14 native deferred annotations (PEP 649), `type` aliases (PEP 695), and `|` unions.
   3. Decouple: Separate API endpoints, schemas, dependencies, and business logic.
   4. Absolute Zero Tolerance on Shims & Code Golfing: Never retain backwards-compatibility shims, forwarding functions, or dual-type parameters. Never compress code to satisfy line limits. Update callers and test mocks directly.

   ### Verification Criteria
   Must pass `uv run ruff check --fix`, `uv run ty check`, and `uv run pytest` with 0 errors.
   ```

---

**These guidelines are working if:** fewer unnecessary changes in diffs, zero backwards-compatibility shims in production code, zero code-golfing workarounds, and clarifying questions come before implementation rather than after mistakes.
