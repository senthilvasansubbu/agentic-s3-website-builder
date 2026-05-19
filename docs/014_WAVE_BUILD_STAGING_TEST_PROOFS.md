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
