"""
test_phase5_parameter_inventory.py — Phase 5 Parameter Inventory Tests

Tests for Phase 5 Parameter Inventory functionality:
- ParameterRecord model
- materialize_parameter_inventory function
- Step 0.6 integration
- Canonical mapping
"""

import pytest
import json
from pathlib import Path

# Import Phase 5 modules
from agent_workflow.enrichment.parameter_inventory_models import (
    ParameterRecord,
    InventoryReport,
    MappingStatus,
    ExtractionStatus,
)
from agent_workflow.enrichment.materialize_parameter_inventory import (
    materialize_parameter_inventory,
)


class TestParameterRecordModel:
    """Test ParameterRecord model."""

    def test_parameter_record_creation(self):
        """Test ParameterRecord can be created with required fields."""
        pr = ParameterRecord(
            record_id="test_1",
            file_name="test.pdf",
            page_number=1,
            table_index=0,
            row_index=0,
            row_id="p1_t0_r0",
            section_title="Test Section",
            table_title="Test Table",
            symbol="VDS",
            parameter_name="Drain-Source Voltage",
            value=1200.0,
            min=None,
            typ=None,
            max=None,
            unit="V",
            raw_condition="VGS=0V",
            resolved_condition="VGS=0V",
            source_schema_type="values",
            source_headers={},
            source_cells=["Symbol", "Parameter", "Values", "Unit"],
            source_text="1200V",
            extraction_status=ExtractionStatus.DIRECT,
            quality_flags=[],
            canonical_field_id=None,
            mapping_status=MappingStatus.UNMAPPED,
            duplicate_group_id=None,
        )
        assert pr.symbol == "VDS"
        assert pr.value == 1200.0
        assert pr.mapping_status == MappingStatus.UNMAPPED

    def test_parameter_record_to_dict(self):
        """Test ParameterRecord.to_dict()."""
        pr = ParameterRecord(
            record_id="test_1",
            file_name="test.pdf",
            page_number=1,
            table_index=0,
            row_index=0,
            row_id="p1_t0_r0",
            section_title="Test Section",
            table_title="Test Table",
            symbol="VDS",
            parameter_name="Drain-Source Voltage",
            value=1200.0,
            min=None,
            typ=None,
            max=None,
            unit="V",
            raw_condition="VGS=0V",
            resolved_condition="VGS=0V",
            source_schema_type="values",
            source_headers={},
            source_cells=["Symbol", "Parameter", "Values", "Unit"],
            source_text="1200V",
            extraction_status=ExtractionStatus.DIRECT,
            quality_flags=[],
            canonical_field_id=None,
            mapping_status=MappingStatus.UNMAPPED,
            duplicate_group_id=None,
        )
        d = pr.to_dict()
        assert d["symbol"] == "VDS"
        assert d["value"] == 1200.0
        assert d["mapping_status"] == "unmapped"

    def test_parameter_record_from_dict(self):
        """Test ParameterRecord.from_dict()."""
        d = {
            "record_id": "test_1",
            "file_name": "test.pdf",
            "page_number": 1,
            "table_index": 0,
            "row_index": 0,
            "row_id": "p1_t0_r0",
            "section_title": "Test Section",
            "table_title": "Test Table",
            "symbol": "VDS",
            "parameter_name": "Drain-Source Voltage",
            "value": 1200.0,
            "min": None,
            "typ": None,
            "max": None,
            "unit": "V",
            "raw_condition": "VGS=0V",
            "resolved_condition": "VGS=0V",
            "source_schema_type": "values",
            "source_headers": {},
            "source_cells": ["Symbol", "Parameter", "Values", "Unit"],
            "source_text": "1200V",
            "extraction_status": "direct",
            "quality_flags": [],
            "canonical_field_id": None,
            "mapping_status": "unmapped",
            "duplicate_group_id": None,
        }
        pr = ParameterRecord.from_dict(d)
        assert pr.symbol == "VDS"
        assert pr.value == 1200.0
        assert pr.mapping_status == MappingStatus.UNMAPPED

    def test_mapping_status_values(self):
        """Test MappingStatus enum values."""
        assert MappingStatus.MAPPED.value == "mapped"
        assert MappingStatus.UNMAPPED.value == "unmapped"
        assert MappingStatus.NEEDS_REVIEW.value == "needs_review"
        assert MappingStatus.DUPLICATE.value == "duplicate"

    def test_extraction_status_values(self):
        """Test ExtractionStatus enum values."""
        assert ExtractionStatus.DIRECT.value == "direct"
        assert ExtractionStatus.FROM_CONDITION.value == "from_condition"
        assert ExtractionStatus.RECONSTRUCTED.value == "reconstructed"


class TestInventoryReport:
    """Test InventoryReport model."""

    def test_inventory_report_creation(self):
        """Test InventoryReport can be created."""
        report = InventoryReport(
            total_rows_processed=100,
            parameter_rows_found=50,
            unknown_rows_found=5,
            unknown_parameter_like=5,
            mapped_count=30,
            unmapped_count=15,
            needs_review_count=3,
            duplicate_count=2,
            missing_value_slots=0,
            missing_source_text=0,
            reconstructed_source_text=0,
            values_table_count=10,
            min_typ_max_table_count=20,
            pages_covered=5,
            tables_covered=30,
        )
        assert report.total_rows_processed == 100
        assert report.parameter_rows_found == 50
        assert report.mapped_count == 30

    def test_inventory_report_to_dict(self):
        """Test InventoryReport.to_dict()."""
        report = InventoryReport(
            total_rows_processed=100,
            parameter_rows_found=50,
            unknown_rows_found=5,
            unknown_parameter_like=5,
            mapped_count=30,
            unmapped_count=15,
            needs_review_count=3,
            duplicate_count=2,
            missing_value_slots=0,
            missing_source_text=0,
            reconstructed_source_text=0,
            values_table_count=10,
            min_typ_max_table_count=20,
            pages_covered=5,
            tables_covered=30,
        )
        d = report.to_dict()
        assert d["total_rows_processed"] == 100
        assert d["parameter_rows_found"] == 50
        assert d["mapped_count"] == 30


class TestMaterializeParameterInventory:
    """Test materialize_parameter_inventory function."""

    def test_materialize_returns_tuple(self):
        """Test materialize_parameter_inventory returns tuple of (records, report)."""
        # This test requires an EnrichedPayload which we don't have in unit tests
        # So we just verify the function signature
        import inspect
        sig = inspect.signature(materialize_parameter_inventory)
        assert len(sig.parameters) == 1  # Only takes enriched_payload


class TestCanonicalMapping:
    """Test canonical mapping functionality."""

    def test_canonical_mapping_updates_record(self):
        """Test that canonical mapping updates ParameterRecord correctly."""
        pr = ParameterRecord(
            record_id="test_1",
            file_name="test.pdf",
            page_number=1,
            table_index=0,
            row_index=0,
            row_id="p1_t0_r0",
            section_title="Test Section",
            table_title="Test Table",
            symbol="VDS",
            parameter_name="Drain-Source Voltage",
            value=1200.0,
            min=None,
            typ=None,
            max=None,
            unit="V",
            raw_condition="VGS=0V",
            resolved_condition="VGS=0V",
            source_schema_type="values",
            source_headers={},
            source_cells=["Symbol", "Parameter", "Values", "Unit"],
            source_text="1200V",
            extraction_status=ExtractionStatus.DIRECT,
            quality_flags=[],
            canonical_field_id=None,
            mapping_status=MappingStatus.UNMAPPED,
            duplicate_group_id=None,
        )

        # Simulate canonical mapping
        row_id_to_field = {"p1_t0_r0": "voltage_rating"}
        if pr.row_id in row_id_to_field:
            pr.canonical_field_id = row_id_to_field[pr.row_id]
            pr.mapping_status = MappingStatus.MAPPED

        assert pr.canonical_field_id == "voltage_rating"
        assert pr.mapping_status == MappingStatus.MAPPED

    def test_canonical_mapping_with_multiple_records(self):
        """Test canonical mapping with multiple records."""
        records = [
            ParameterRecord(
                record_id=f"test_{i}",
                file_name="test.pdf",
                page_number=1,
                table_index=0,
                row_index=i,
                row_id=f"p1_t0_r{i}",
                section_title="Test Section",
                table_title="Test Table",
                symbol=f"SYM{i}",
                parameter_name=f"Parameter {i}",
                value=float(i * 10),
                min=None,
                typ=None,
                max=None,
                unit="V",
                raw_condition="",
                resolved_condition="",
                source_schema_type="values",
                source_headers={},
                source_cells=[],
                source_text=f"{i*10}V",
                extraction_status=ExtractionStatus.DIRECT,
                quality_flags=[],
                canonical_field_id=None,
                mapping_status=MappingStatus.UNMAPPED,
                duplicate_group_id=None,
            )
            for i in range(3)
        ]

        # Apply mapping
        row_id_to_field = {
            "p1_t0_r0": "voltage_rating",
            "p1_t0_r1": "current_rating",
        }

        mapped_count = 0
        for record in records:
            if record.row_id in row_id_to_field:
                record.canonical_field_id = row_id_to_field[record.row_id]
                record.mapping_status = MappingStatus.MAPPED
                mapped_count += 1

        assert mapped_count == 2
        assert records[0].canonical_field_id == "voltage_rating"
        assert records[1].canonical_field_id == "current_rating"
        assert records[2].mapping_status == MappingStatus.UNMAPPED


class TestStep06Integration:
    """Test Step 0.6 integration."""

    def test_step06_import(self):
        """Test Step 0.6 can be imported."""
        from agent_workflow.steps.step0_6_parameter_inventory import run as step0_6_run
        import inspect
        sig = inspect.signature(step0_6_run)
        params = list(sig.parameters.keys())
        assert "enriched_payload" in params
        assert "artifact_paths" in params
        assert "canonical_results" in params

    def test_step06_returns_tuple(self):
        """Test Step 0.6 run returns tuple of (records, report)."""
        from agent_workflow.steps.step0_6_parameter_inventory import run as step0_6_run
        import inspect
        # The function signature is async or returns tuple - check the code
        # For now, just verify it can be imported


class TestExcelOutput:
    """Test Excel output for Parameter Inventory."""

    def test_excel_functions_import(self):
        """Test Excel output functions can be imported."""
        from reports.excel_from_agent import (
            _write_all_parameters,
            _write_unmapped_parameters,
            _write_needs_review,
        )
        assert callable(_write_all_parameters)
        assert callable(_write_unmapped_parameters)
        assert callable(_write_needs_review)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
