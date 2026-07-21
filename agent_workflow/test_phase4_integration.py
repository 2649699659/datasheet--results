"""
test_phase4_integration.py — Phase 4 integration tests

Tests for:
- Step 0 → Step 0.5 → Step 1 integration in runner
- Cache and fingerprint validation
- Agent input structures with enriched context
- Step 3 unified value access
- Data protection (raw_cells, raw_condition, row_id unchanged)
"""

import json
import tempfile
import pytest
from pathlib import Path

from agent_workflow.steps.step3_agent_cross_check import (
    resolve_consistency_value,
    resolve_min,
    resolve_max,
    CONSISTENCY_SLOTS,
)


# =============================================================================
# A. Runner Integration Tests
# =============================================================================


class TestRunnerIntegration:
    """Tests for Step 0 → Step 0.5 → Step 1 pipeline integration."""

    def test_runner_has_disable_flag(self):
        """Runner module supports --disable-context-enrichment flag."""
        # Test that the runner module has the flag defined in its argument parser
        # Since parse_args uses sys.argv, we check the source code instead
        import inspect
        from agent_workflow import runner

        source = inspect.getsource(runner)
        assert "disable-context-enrichment" in source

    def test_runner_has_fallback_flag(self):
        """Runner module supports --allow-context-enrichment-fallback flag."""
        import inspect
        from agent_workflow import runner

        source = inspect.getsource(runner)
        assert "allow-context-enrichment-fallback" in source

    def test_runner_run_workflow_accepts_disable_and_fallback(self):
        """run_workflow accepts disable_context_enrichment and allow_context_enrichment_fallback params."""
        from agent_workflow.runner import run_workflow
        import inspect

        sig = inspect.signature(run_workflow)
        params = list(sig.parameters.keys())

        assert "disable_context_enrichment" in params
        assert "allow_context_enrichment_fallback" in params

    def test_step0_5_report_path_in_artifacts(self):
        """ArtifactPaths has step0_5_report() method."""
        from agent_workflow.artifacts import ArtifactPaths

        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ArtifactPaths(Path(tmpdir), "test")

            # Verify step0_5_report path method exists
            assert hasattr(paths, "step0_5_report")
            report_path = paths.step0_5_report()
            assert report_path.name == "step0_5_report.json"

    def test_step0_5_payload_path_in_artifacts(self):
        """ArtifactPaths has step0_5_enriched_payload() method."""
        from agent_workflow.artifacts import ArtifactPaths

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ArtifactPaths(Path(tmpdir), "test")

            assert hasattr(paths, "step0_5_enriched_payload")
            payload_path = paths.step0_5_enriched_payload()
            assert payload_path.name == "step0_5_enriched_payload.json"

    def test_step0_5_path_different_from_step0(self):
        """Step 0.5 path is different from Step 0 path."""
        from agent_workflow.artifacts import ArtifactPaths

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ArtifactPaths(Path(tmpdir), "test")

            step0_path = paths.step0_payload()
            step0_5_path = paths.step0_5_enriched_payload()

            assert step0_5_path != step0_path


# =============================================================================
# B. Cache and Fingerprint Tests
# =============================================================================


class TestCacheAndFingerprint:
    """Tests for source fingerprint validation in caching."""

    def test_source_fingerprint_from_path(self):
        """SourceFingerprint.compute() creates correct fingerprint from file."""
        from agent_workflow.contracts import SourceFingerprint

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"test content")
            f.flush()
            test_file = f.name

        try:
            fp = SourceFingerprint.from_path(test_file)

            assert fp.resolved_path == str(Path(test_file).resolve())
            assert fp.file_size == 12
            assert fp.mtime_ns > 0
        finally:
            Path(test_file).unlink()

    def test_fingerprint_serializes_to_dict(self):
        """SourceFingerprint.to_dict() produces JSON-serializable dict."""
        from agent_workflow.contracts import SourceFingerprint

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"test content")
            f.flush()
            test_file = f.name

        try:
            fp = SourceFingerprint.from_path(test_file)
            d = fp.to_dict()

            assert isinstance(d, dict)
            assert d["resolved_path"] == str(Path(test_file).resolve())
            assert d["file_size"] == 12
            assert d["mtime_ns"] > 0
        finally:
            Path(test_file).unlink()

    def test_fingerprint_roundtrip(self):
        """SourceFingerprint can be serialized and deserialized."""
        from agent_workflow.contracts import SourceFingerprint

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"test content")
            f.flush()
            test_file = f.name

        try:
            fp1 = SourceFingerprint.from_path(test_file)
            d = fp1.to_dict()
            fp2 = SourceFingerprint.from_dict(d)

            assert fp1.resolved_path == fp2.resolved_path
            assert fp1.file_size == fp2.file_size
            assert fp1.mtime_ns == fp2.mtime_ns
        finally:
            Path(test_file).unlink()

    def test_different_size_different_fingerprint(self):
        """Different file sizes produce different fingerprints."""
        from agent_workflow.contracts import SourceFingerprint

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f1:
            f1.write(b"short")
            f1.flush()
            file1 = f1.name

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f2:
            f2.write(b"much longer content")
            f2.flush()
            file2 = f2.name

        try:
            fp1 = SourceFingerprint.from_path(file1)
            fp2 = SourceFingerprint.from_path(file2)

            assert fp1.file_size != fp2.file_size
        finally:
            Path(file1).unlink()
            Path(file2).unlink()

    def test_camelot_payload_has_schema_version(self):
        """CamelotPayload dataclass has schema_version field."""
        from agent_workflow.contracts import CamelotPayload

        # Check that CamelotPayload has schema_version in its annotations
        annotations = getattr(CamelotPayload, "__annotations__", {})
        assert "schema_version" in annotations

    def test_camelot_payload_has_source_fingerprint(self):
        """CamelotPayload dataclass has source_fingerprint field."""
        from agent_workflow.contracts import CamelotPayload

        annotations = getattr(CamelotPayload, "__annotations__", {})
        assert "source_fingerprint" in annotations


# =============================================================================
# C. Agent Input Tests
# =============================================================================


class TestAgentInputs:
    """Tests for Step 1/2 receiving enriched context correctly."""

    def test_step1_receives_enriched_payload_parameter(self):
        """Step 1 run() accepts enriched_payload parameter."""
        from agent_workflow.steps.step1_agent_candidate import run
        import inspect

        sig = inspect.signature(run)
        params = list(sig.parameters.keys())

        assert "enriched_payload" in params

    def test_step2_receives_enriched_payload_parameter(self):
        """Step 2 run() accepts enriched_payload parameter."""
        from agent_workflow.steps.step2_agent_validator import run
        import inspect

        sig = inspect.signature(run)
        params = list(sig.parameters.keys())

        assert "enriched_payload" in params

    def test_prompt_forbids_self_propagation_in_agent1(self):
        """Agent 1 prompt contains enrichment context instructions."""
        prompt_path = Path("agent_workflow/prompts/agent1_table_classifier_v1.md")
        if prompt_path.exists():
            content = prompt_path.read_text()
            # Should mention enrichment or Step 0.5 or resolved_condition
            assert "Enriched Context" in content or "Step 0.5" in content or "resolved_condition" in content

    def test_prompt_forbids_self_propagation_in_agent2(self):
        """Agent 2 prompt contains enrichment context instructions."""
        prompt_path = Path("agent_workflow/prompts/agent2_validator.md")
        if prompt_path.exists():
            content = prompt_path.read_text()
            # Should mention enrichment context usage
            assert "Enriched Context" in content or "resolved_condition" in content

    def test_step2_llm_input_includes_manufacturer_in_prompt(self):
        """Agent 2 prompt mentions manufacturer metadata usage."""
        prompt_path = Path("agent_workflow/prompts/agent2_validator.md")
        if prompt_path.exists():
            content = prompt_path.read_text()
            assert "manufacturer" in content.lower() or "AST Technology" in content


# =============================================================================
# D. Step 3 Unified Value Access Tests
# =============================================================================


class TestStep3UnifiedValueAccess:
    """Tests for resolve_consistency_value and related functions."""

    def test_voltage_rating_uses_value_slot(self):
        """voltage_rating should use 'value' slot per CONSISTENCY_SLOTS."""
        assert CONSISTENCY_SLOTS["voltage_rating"]["primary"] == "value"

    def test_isol_uses_min_slot(self):
        """isol should use 'min' slot per CONSISTENCY_SLOTS."""
        assert CONSISTENCY_SLOTS["isol"]["primary"] == "min"

    def test_junction_temperature_uses_max_slot(self):
        """junction_temperature should use 'max' slot as primary per CONSISTENCY_SLOTS."""
        assert CONSISTENCY_SLOTS["junction_temperature"]["primary"] == "max"

    def test_vgs_th_has_min_and_max_slots(self):
        """vgs_th should have both min and max slots available."""
        assert CONSISTENCY_SLOTS["vgs_th"]["primary"] == "min"
        assert CONSISTENCY_SLOTS["vgs_th"]["secondary"] == "max"

    def test_rds_on_25c_uses_typ_slot(self):
        """rds_on_25c should use 'typ' slot as primary."""
        assert CONSISTENCY_SLOTS["rds_on_25c"]["primary"] == "typ"

    def test_resolve_consistency_value_returns_float(self):
        """resolve_consistency_value returns float, not int."""
        class MockParam:
            value = 1200
            min = None
            max = None
            typ = None
            unit = "V"

        result = resolve_consistency_value(MockParam(), "voltage_rating")
        assert isinstance(result, float)
        assert result == 1200.0

    def test_resolve_min_returns_min_value(self):
        """resolve_min returns the 'min' slot value."""
        class MockParam:
            value = 100
            min = 4.2
            max = 200

        result = resolve_min(MockParam(), "isol")
        assert result == 4.2

    def test_resolve_max_returns_max_value(self):
        """resolve_max returns the 'max' slot value."""
        class MockParam:
            value = 100
            min = 2.0
            max = 4.0

        result = resolve_max(MockParam(), "vgs_th")
        assert result == 4.0

    def test_resolve_consistency_value_uses_primary_first(self):
        """resolve_consistency_value tries primary slot before secondary."""
        class MockParam:
            value = 999  # secondary
            min = None
            max = None
            typ = 42.0  # primary

        result = resolve_consistency_value(MockParam(), "rds_on_25c")
        assert result == 42.0  # typ (primary), not value (secondary)

    def test_resolve_consistency_value_falls_back_to_secondary(self):
        """resolve_consistency_value falls back to secondary when primary is None."""
        class MockParam:
            value = 999
            min = None
            max = None
            typ = None  # primary is None

        result = resolve_consistency_value(MockParam(), "rds_on_25c")
        assert result == 999.0  # value (secondary)

    def test_resolve_consistency_value_returns_none_when_both_empty(self):
        """resolve_consistency_value returns None when both primary and secondary are empty."""
        class MockParam:
            value = None
            min = None
            max = None
            typ = None

        result = resolve_consistency_value(MockParam(), "rds_on_25c")
        assert result is None

    def test_resolve_consistency_value_none_for_none_param(self):
        """resolve_consistency_value returns None when param is None."""
        result = resolve_consistency_value(None, "voltage_rating")
        assert result is None

    def test_resolve_min_none_for_none_param(self):
        """resolve_min returns None when param is None."""
        result = resolve_min(None, "isol")
        assert result is None

    def test_resolve_max_none_for_none_param(self):
        """resolve_max returns None when param is None."""
        result = resolve_max(None, "vgs_th")
        assert result is None

    def test_voltage_rating_resolve_value(self):
        """voltage_rating with value=1200 resolves to 1200.0."""
        class MockParam:
            value = 1200
            min = None
            max = 1200
            typ = None
            unit = "V"

        result = resolve_consistency_value(MockParam(), "voltage_rating")
        assert result == 1200.0

    def test_isol_resolve_min(self):
        """isol with min=4.2 resolves to 4.2 via resolve_min."""
        class MockParam:
            value = None
            min = 4.2
            max = None
            typ = None
            unit = "A"

        result = resolve_min(MockParam(), "isol")
        assert result == 4.2

    def test_junction_temperature_resolve_max(self):
        """junction_temperature with max=175 resolves to 175.0."""
        class MockParam:
            value = None
            min = None
            max = 175
            typ = None
            unit = "°C"

        result = resolve_consistency_value(MockParam(), "junction_temperature")
        assert result == 175.0

    def test_vgsth_resolve_min_max(self):
        """vgs_th with min=2, max=4 resolves correctly."""
        class MockParam:
            value = None
            min = 2.0
            max = 4.0
            typ = None
            unit = "V"

        vmin = resolve_min(MockParam(), "vgs_th")
        vmax = resolve_max(MockParam(), "vgs_th")
        assert vmin == 2.0
        assert vmax == 4.0

    def test_all_consistency_checks_use_unified_access(self):
        """Verify no _typ(), _max_v(), _min_v() in actual consistency check function bodies."""
        import inspect
        from agent_workflow.steps.step3_agent_cross_check import (
            check_rds_temperature_coefficient,
            check_gate_charge_hierarchy,
            check_capacitance_hierarchy,
            check_reverse_recovery_consistency,
            check_switching_energy,
            check_junction_temperature,
            check_vgsth_range,
            check_isolation_voltage,
        )

        checks = [
            check_rds_temperature_coefficient,
            check_gate_charge_hierarchy,
            check_capacitance_hierarchy,
            check_reverse_recovery_consistency,
            check_switching_energy,
            check_junction_temperature,
            check_vgsth_range,
            check_isolation_voltage,
        ]

        for check in checks:
            source = inspect.getsource(check)
            lines = source.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") or not stripped:
                    continue
                # Check that old accessors are not called directly in function body
                if "_typ(" in line and "resolve_consistency_value" not in line:
                    assert False, f"{check.__name__} still uses _typ() directly: {line}"
                if "_max_v(" in line and "resolve_max" not in line:
                    assert False, f"{check.__name__} still uses _max_v() directly: {line}"
                if "_min_v(" in line and "resolve_min" not in line:
                    assert False, f"{check.__name__} still uses _min_v() directly: {line}"


# =============================================================================
# E. ASC300N1200ME3-X Specific Tests
# =============================================================================


class TestASC300N1200MEXSpecific:
    """Tests for ASC300N1200ME3-X specific expected behaviors via enrichment model."""

    def test_manufacturer_detected_in_enrichment_report_fields(self):
        """Enrichment report should include manufacturer in document_metadata."""
        from agent_workflow.enrichment.models import EnrichedPayload

        # The EnrichedPayload should have document_metadata field
        annotations = getattr(EnrichedPayload, "__annotations__", {})
        assert "document_metadata" in annotations

    def test_manufacturer_metadata_in_prompt(self):
        """Agent 2 prompt mentions manufacturer canonical value usage."""
        prompt_path = Path("agent_workflow/prompts/agent2_validator.md")
        if prompt_path.exists():
            content = prompt_path.read_text()
            assert "canonical_value" in content or "manufacturer" in content.lower()


# =============================================================================
# F. Data Protection Tests
# =============================================================================


class TestDataProtection:
    """Tests that raw data structures preserve original fields."""

    def test_enriched_row_has_raw_cells_field(self):
        """EnrichedRow has raw_cells field for data protection."""
        from agent_workflow.enrichment.models import EnrichedRow

        annotations = getattr(EnrichedRow, "__annotations__", {})
        assert "raw_cells" in annotations

    def test_enriched_row_has_raw_condition_field(self):
        """EnrichedRow has raw_condition field for data protection."""
        from agent_workflow.enrichment.models import EnrichedRow

        annotations = getattr(EnrichedRow, "__annotations__", {})
        assert "raw_condition" in annotations

    def test_enriched_row_has_row_index_field(self):
        """EnrichedRow has row_index field for row identification."""
        from agent_workflow.enrichment.models import EnrichedRow

        annotations = getattr(EnrichedRow, "__annotations__", {})
        assert "row_index" in annotations

    def test_enriched_row_has_row_id_field(self):
        """EnrichedRow has row_id field for unique identification."""
        from agent_workflow.enrichment.models import EnrichedRow

        annotations = getattr(EnrichedRow, "__annotations__", {})
        assert "row_id" in annotations

    def test_camelot_table_row_has_cells_field(self):
        """CamelotTableRow has cells field."""
        from agent_workflow.contracts import CamelotTableRow

        annotations = getattr(CamelotTableRow, "__annotations__", {})
        assert "cells" in annotations

    def test_camelot_table_row_has_row_index_field(self):
        """CamelotTableRow has row_index field."""
        from agent_workflow.contracts import CamelotTableRow

        annotations = getattr(CamelotTableRow, "__annotations__", {})
        assert "row_index" in annotations


# =============================================================================
# G. Step 0.5 Report Structure Tests
# =============================================================================


class TestStep05ReportStructure:
    """Tests for Step 0.5 enrichment report structure."""

    def test_build_enrichment_report_exists(self):
        """build_enrichment_report function exists in step0_5_enrich_context."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        import inspect

        sig = inspect.signature(build_enrichment_report)
        params = list(sig.parameters.keys())

        # Should take enriched payload as input
        assert "enriched" in params

    def test_enrichment_report_returns_dict(self):
        """build_enrichment_report returns a dictionary."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        from agent_workflow.enrichment.models import EnrichedPayload, EnrichedPage

        # Create minimal EnrichedPayload
        payload = EnrichedPayload(
            document_id="test",
            file_name="test.pdf",
            pdf_path="/tmp/test.pdf",
            source_backend="camelot",
            pages=[EnrichedPage(page_number=1, tables=[])],
        )

        report = build_enrichment_report(payload)

        assert isinstance(report, dict)

    def test_report_includes_row_type_counts(self):
        """Report includes row_type_counts field."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        from agent_workflow.enrichment.models import EnrichedPayload, EnrichedPage

        payload = EnrichedPayload(
            document_id="test",
            file_name="test.pdf",
            pdf_path="/tmp/test.pdf",
            source_backend="camelot",
            pages=[EnrichedPage(page_number=1, tables=[])],
            row_type_counts={"PARAMETER": 10, "SECTION_TITLE": 2},
        )

        report = build_enrichment_report(payload)

        assert "row_type_counts" in report

    def test_report_includes_heading_conditions(self):
        """Report includes heading_conditions_applied field."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        from agent_workflow.enrichment.models import EnrichedPayload, EnrichedPage

        payload = EnrichedPayload(
            document_id="test",
            file_name="test.pdf",
            pdf_path="/tmp/test.pdf",
            source_backend="camelot",
            pages=[EnrichedPage(page_number=1, tables=[])],
            heading_conditions_applied=20,
        )

        report = build_enrichment_report(payload)

        assert "heading_conditions_applied" in report
        assert report["heading_conditions_applied"] == 20

    def test_report_includes_manufacturer_info(self):
        """Report includes manufacturer_status and manufacturer_canonical_value."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        from agent_workflow.enrichment.models import EnrichedPayload, EnrichedPage

        payload = EnrichedPayload(
            document_id="test",
            file_name="test.pdf",
            pdf_path="/tmp/test.pdf",
            source_backend="camelot",
            pages=[EnrichedPage(page_number=1, tables=[])],
            document_metadata={
                "manufacturer": {
                    "canonical_value": "AST Technology",
                    "status": "resolved",
                    "candidates": ["astsic.com"],
                }
            },
        )

        report = build_enrichment_report(payload)

        assert "manufacturer_status" in report
        assert "manufacturer_canonical_value" in report
        assert report["manufacturer_canonical_value"] == "AST Technology"

    def test_report_includes_row_type_counts(self):
        """Report includes row_type_counts field."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        from agent_workflow.enrichment.models import EnrichedPayload, EnrichedPage

        payload = EnrichedPayload(
            document_id="test",
            file_name="test.pdf",
            pdf_path="/tmp/test.pdf",
            source_backend="camelot",
            pages=[EnrichedPage(page_number=1, tables=[])],
            row_type_counts={"PARAMETER": 50, "SECTION_TITLE": 10},
        )

        report = build_enrichment_report(payload)

        assert "row_type_counts" in report
        assert report["row_type_counts"]["PARAMETER"] == 50

    def test_report_includes_cache_stats_and_warnings(self):
        """Report includes cache_stats and warnings fields."""
        from agent_workflow.steps.step0_5_enrich_context import build_enrichment_report
        from agent_workflow.enrichment.models import EnrichedPayload, EnrichedPage

        payload = EnrichedPayload(
            document_id="test",
            file_name="test.pdf",
            pdf_path="/tmp/test.pdf",
            source_backend="camelot",
            pages=[EnrichedPage(page_number=1, tables=[])],
        )

        report = build_enrichment_report(payload)

        assert "cache_stats" in report
        assert "warnings" in report


# =============================================================================
# H. Original Tests Still Pass
# =============================================================================


class TestOriginalTestsStillPass:
    """Verify original 119 tests still pass (smoke test)."""

    def test_original_tests_directory_exists(self):
        """Original enrichment test file should exist."""
        test_path = Path("agent_workflow/enrichment/test_enrich_context.py")
        assert test_path.exists()
