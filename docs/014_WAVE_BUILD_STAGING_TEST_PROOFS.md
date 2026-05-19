# Wave Build and Staging Test Proofs

Date: 2026-05-19

## Scope

This note records proof for:

1. Wave Build Website scenario
2. Wave Staging Area Edits scenario

## Scenario 1: Wave Build Website

### Testcases

1. `test_wave_build_website_queues_and_tracks_status`
2. `test_wave_build_website_rejects_unknown_output_target`

File:

- `tests/test_wave_build_website.py`

### Validation evidence

Command run:

```bash
pytest -q tests/test_wave_build_website.py
```

Observed status:

- Passed as part of combined verification run (see final section).

## Scenario 2: Wave Staging Area Edits

### Testcases

1. `test_wave_staging_area_get_uses_manifest_entry`
2. `test_wave_staging_area_put_updates_entry_and_manifest`

File:

- `tests/test_wave_staging_area_edits.py`

### Initial error proof

Failing assertion observed during first run:

```text
FAILED tests/test_wave_staging_area_edits.py::test_wave_staging_area_get_uses_manifest_entry
AssertionError: assert 'landing.html' == 'pages/landing.html'
```

This proved the staged entry metadata was being reduced to basename and lost nested entry path information.

### Fix applied

API fix location:

- `api/routes/website_builder.py`

Fix summary:

1. Preserve full relative entry path from `local_path` using `Path(index_file).relative_to(Path(local_path)).as_posix()`.
2. Pass that relative path to staging snapshot output instead of `os.path.basename(index_file)`.

### Post-fix validation evidence

Command run:

```bash
pytest -q tests/test_wave_staging_area_edits.py tests/test_staging_artifacts.py
```

Observed status:

- Passed as part of combined verification run (see final section).

## Final combined test proof

Command run:

```bash
pytest -q tests/test_wave_build_website.py tests/test_wave_staging_area_edits.py tests/test_staging_artifacts.py
```

Observed result:

```text
collected 7 items

tests/test_wave_build_website.py ..
tests/test_wave_staging_area_edits.py ..
tests/test_staging_artifacts.py ...

7 passed
```

## CI proof artifacts

Both dedicated workflows now upload:

1. Coverage XML
2. JUnit XML test report

Workflow files:

1. `.github/workflows/test-wave-build-website.yml`
2. `.github/workflows/test-wave-staging-area-edits.yml`

## Execution order (must follow)

1. Run workflow: `Test | Wave Build Website | Build Queue and Status Gate`.
2. Require success: `wave-build-website-tests`.
3. Verify artifacts exist:
	- `coverage-wave-build-website-xml`
	- `test-results-wave-build-website-xml`
4. Check JUnit report: failures = 0 and errors = 0.
5. Run workflow: `Test | Wave Staging Area Edits | Staged HTML and Manifest Gate`.
6. Require success: `wave-staging-area-edits-tests`.
7. Verify artifacts exist:
	- `coverage-wave-staging-area-edits-xml`
	- `test-results-wave-staging-area-edits-xml`
8. Check JUnit report: failures = 0 and errors = 0.

## Release gate criteria

PASS only if all of the following are true:

1. Both workflows completed successfully.
2. All required artifacts were generated and downloadable.
3. JUnit test reports show zero failures and zero errors.
4. Evidence in this document remains aligned with latest run output.

FAIL if any single condition above fails.

## Failure handling loop

1. Identify the exact failing testcase from JUnit XML artifact.
2. Reproduce locally using targeted `pytest` command.
3. Fix code.
4. Re-run:
	- `tests/test_wave_build_website.py`
	- `tests/test_wave_staging_area_edits.py`
	- `tests/test_staging_artifacts.py`
5. Push changes and re-run workflows in the same order.
