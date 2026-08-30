"""Verdict conjunction unit tests: verdicts are computed, never hand-entered."""

from __future__ import annotations

from newlife.conform.verdict import (
    VERDICT_PASS,
    VERDICT_REJECT,
    VERDICT_WITHHELD,
    compute_verdict,
    pytest_output_passed,
)


def test_all_checks_pass_yields_the_frozen_verdict():
    assert (
        compute_verdict(
            {"cell_a": True, "cell_b": True}, {"eng_a": True, "eng_b": True}
        )
        == VERDICT_PASS
    )


def test_one_false_cell_check_forces_reject():
    verdict = compute_verdict(
        {"cell_a": True, "cell_b": False}, {"eng_a": True}
    )
    assert verdict == VERDICT_REJECT


def test_cells_pass_but_engineering_fails_withholds_the_verdict():
    # a missed tampered-lowering control voids the positives retroactively —
    # the verdict is withheld, never qualified
    verdict = compute_verdict(
        {"cell_a": True, "cell_b": True},
        {"tamper_control_detected": False, "eng_b": True},
    )
    assert verdict == VERDICT_WITHHELD


def test_missing_check_key_is_an_error_not_a_pass():
    import pytest

    from newlife.conform.manifest import ManifestValidationError, build_manifest

    manifest = build_manifest()
    del manifest["proofroot_version"]
    with pytest.raises(ManifestValidationError):
        # validate is invoked by canonical_manifest_bytes / build_manifest
        from newlife.conform.manifest import validate_manifest

        validate_manifest(manifest)


def test_pytest_output_requires_an_exact_success_summary():
    assert pytest_output_passed("................................ [100%]\n89 passed in 1.52s\n")
    assert not pytest_output_passed("88 passed, 1 error in 1.52s\n")
    assert not pytest_output_passed("89 passed in 1.52s\ncollection error\n")
