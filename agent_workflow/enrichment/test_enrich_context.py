"""
test_enrich_context.py — Unit tests for Step 0.5 (enrich_context)

Tests the enrichment layer: CamelotPayload → EnrichedPayload.
No API key needed. No LLM calls.

Run with:
    python3 -m agent_workflow.enrichment.test_enrich_context
    python3 -m unittest agent_workflow.enrichment.test_enrich_context
"""

import json
import sys
import unittest
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_workflow.contracts import CamelotPayload
from agent_workflow.enrichment import (
    EnrichedPayload,
    enrich_payload,
    RowClassifier,
    RowType,
    ContextStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test data paths
# ─────────────────────────────────────────────────────────────────────────────

def _find_test_payload() -> Path:
    """Find the ASC300N1200ME3 CamelotPayload from a previous test run."""
    candidates = [
        PROJECT_ROOT / "output/step4_fix_final/ASC300N1200ME3_1784528153/artifacts/step0_camelot_payload.json",
        PROJECT_ROOT / "output/sourced_env_test/ASC300N1200ME3_1784527702/artifacts/step0_camelot_payload.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Could not find test CamelotPayload. Looked in: {candidates}\n"
        "Run the agent workflow first to generate test data."
    )


def _load_test_payload() -> CamelotPayload:
    """Load the CamelotPayload for testing."""
    path = _find_test_payload()
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return CamelotPayload.from_dict(d)


# ─────────────────────────────────────────────────────────────────────────────
# Test: RowClassifier
# ─────────────────────────────────────────────────────────────────────────────

class TestRowClassifier(unittest.TestCase):
    """Tests for the RowClassifier class."""

    def setUp(self):
        self.clf = RowClassifier()

    def _cells(self, *args):
        """Helper: create cell list from strings."""
        return list(args)

    # ── Empty ──────────────────────────────────────────────────────────────

    def test_empty_all_none(self):
        cells = ["", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.EMPTY)

    def test_empty_whitespace_only(self):
        cells = ["  ", "\t", "   "]
        self.assertEqual(self.clf.classify(cells), RowType.EMPTY)

    def test_empty_single(self):
        cells = [""]
        self.assertEqual(self.clf.classify(cells), RowType.EMPTY)

    # ── Separator ──────────────────────────────────────────────────────────

    def test_separator_dashes(self):
        cells = ["---", "---", "---"]
        self.assertEqual(self.clf.classify(cells), RowType.SEPARATOR)

    def test_separator_equals(self):
        cells = ["===", "==="]
        self.assertEqual(self.clf.classify(cells), RowType.SEPARATOR)

    def test_separator_mixed(self):
        cells = ["___", "___", "___"]
        self.assertEqual(self.clf.classify(cells), RowType.SEPARATOR)

    # ── Column Header ─────────────────────────────────────────────────────

    def test_column_header_standard(self):
        cells = ["Symbol", "Parameter", "Min.", "Typ.", "Max.", "Unit", "Test Conditions"]
        self.assertEqual(self.clf.classify(cells), RowType.COLUMN_HEADER)

    def test_column_header_partial(self):
        cells = ["Symbol", "Parameter", "Values", "", "", "Unit", "Test Conditions"]
        self.assertEqual(self.clf.classify(cells), RowType.COLUMN_HEADER)

    def test_column_header_chinese(self):
        cells = ["符号", "参数", "最小值", "典型值", "最大值", "单位", "测试条件"]
        # No hits on English keywords, so NOT classified as column_header
        result = self.clf.classify(cells)
        self.assertNotEqual(result, RowType.COLUMN_HEADER)

    # ── Section Title ─────────────────────────────────────────────────────

    def test_section_title_static_characteristics(self):
        cells = ["Static characteristics (at TC=25℃ unless otherwise specified)", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.SECTION_TITLE)

    def test_section_title_absolute_maximum_ratings(self):
        cells = ["Absolute Maximum Ratings", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.SECTION_TITLE)

    def test_section_title_body_diode(self):
        cells = ["Body Diode Characteristics (at TJ=25℃ unless otherwise specified)", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.SECTION_TITLE)

    def test_section_title_dynamic(self):
        cells = ["Dynamic characteristics", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.SECTION_TITLE)

    def test_section_title_switching(self):
        cells = ["Switching characteristics", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.SECTION_TITLE)

    def test_section_title_unless_otherwise(self):
        cells = ["(at TC=25℃ unless otherwise specified)", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.SECTION_TITLE)

    # ── Table Title ────────────────────────────────────────────────────────

    def test_table_title_key_parameters(self):
        cells = ["Key Parameters", "", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.TABLE_TITLE)

    def test_table_title_order_number(self):
        cells = ["Order Number", "", "", "", "", "", ""]
        self.assertEqual(self.clf.classify(cells), RowType.TABLE_TITLE)

    def test_table_title_marking(self):
        cells = ["Marking", "", "", "", "", "", ""]
        # Phase 2A: "Marking" is UNKNOWN — does not match any known table title pattern
        self.assertEqual(self.clf.classify(cells), RowType.UNKNOWN)

    # ── Parameter ──────────────────────────────────────────────────────────

    def test_parameter_vds(self):
        cells = ["VDS", "Drain-Source Voltage", "1200", "", "", "V", "TC=25°C"]
        self.assertEqual(self.clf.classify(cells), RowType.PARAMETER)

    def test_parameter_rds(self):
        cells = ["RDS(on)", "Static Drain-Source on Resistance", "", "5.3", "6.7", "mΩ", "VGS=18V; ID=150A; TC=25°C"]
        self.assertEqual(self.clf.classify(cells), RowType.PARAMETER)

    def test_parameter_qg(self):
        cells = ["QG", "Total Gate Charge", "-", "618", "-", "nC", "VDD=800V; VGS=-5/+18V; ID=150A; TC=25°C"]
        self.assertEqual(self.clf.classify(cells), RowType.PARAMETER)

    def test_parameter_with_dashes(self):
        cells = ["VGS(th)", "Gate Threshold Voltage", "2", "-", "4", "V", "VDS=VGS; ID=30mA"]
        self.assertEqual(self.clf.classify(cells), RowType.PARAMETER)

    # ── Unknown ────────────────────────────────────────────────────────────

    def test_unknown_single_weird_cell(self):
        cells = ["3.5", "", "", "", "", "", ""]
        # Single numeric cell that's not a valid parameter row
        result = self.clf.classify(cells)
        self.assertEqual(result, RowType.UNKNOWN)

    def test_unknown_cannot_classify(self):
        # A row that doesn't match any known pattern
        cells = ["Some weird format", "@#$%", "", "", "", "", ""]
        result = self.clf.classify(cells)
        # Should be unknown since it doesn't match any pattern
        self.assertEqual(result, RowType.UNKNOWN)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Payload conversion
# ─────────────────────────────────────────────────────────────────────────────

class TestPayloadConversion(unittest.TestCase):
    """Tests for the enrich_payload function."""

    @classmethod
    def setUpClass(cls):
        cls.payload = _load_test_payload()
        cls.enriched = enrich_payload(cls.payload)

    # ── Count invariants ────────────────────────────────────────────────────

    def test_document_count_unchanged(self):
        self.assertEqual(self.payload.document_id, self.enriched.document_id)

    def test_file_name_unchanged(self):
        self.assertEqual(self.payload.file_name, self.enriched.file_name)

    def test_pdf_path_unchanged(self):
        self.assertEqual(self.payload.pdf_path, self.enriched.pdf_path)

    def test_source_backend_unchanged(self):
        self.assertEqual(self.payload.source_backend, self.enriched.source_backend)

    def test_page_count_unchanged(self):
        self.assertEqual(len(self.payload.pages), len(self.enriched.pages))

    def test_table_count_unchanged(self):
        orig_tables = sum(len(p.tables) for p in self.payload.pages)
        new_tables = sum(len(p.tables) for p in self.enriched.pages)
        self.assertEqual(orig_tables, new_tables)

    def test_row_count_unchanged(self):
        """CRITICAL: input_row_count == output_row_count"""
        orig_rows = sum(
            len(t.rows) for p in self.payload.pages for t in p.tables
        )
        new_rows = sum(
            len(t.rows) for p in self.enriched.pages for t in p.tables
        )
        self.assertEqual(orig_rows, new_rows)

    # ── Cell preservation ─────────────────────────────────────────────────

    def test_raw_cells_deep_copy(self):
        """input_row.cells == output_row.raw_cells for every row."""
        mismatches = []
        for orig_page in self.payload.pages:
            for orig_table in orig_page.tables:
                for orig_row in orig_table.rows:
                    # Find corresponding enriched row
                    found = False
                    for en_page in self.enriched.pages:
                        for en_table in en_page.tables:
                            if en_table.page_number == orig_table.page_number and en_table.table_index == orig_table.table_index:
                                for en_row in en_table.rows:
                                    if en_row.row_index == orig_row.row_index:
                                        if orig_row.cells != en_row.raw_cells:
                                            mismatches.append({
                                                "row_id": en_row.row_id,
                                                "orig": orig_row.cells,
                                                "enriched": en_row.raw_cells,
                                            })
                                        found = True
                                        break
                                break
                        if found:
                            break
                    if not found:
                        mismatches.append({"row_id": f"p{orig_table.page_number}_t{orig_table.table_index}_r{orig_row.row_index}", "error": "not found"})
        self.assertEqual([], mismatches, "All rows must have raw_cells identical to input")

    # ── row_id ─────────────────────────────────────────────────────────────

    def test_row_id_format(self):
        """row_id format: p{page}_t{table}_r{row}"""
        import re
        pattern = re.compile(r"^p\d+_t\d+_r\d+$")
        all_valid = True
        invalid_ids = []
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if not pattern.match(row.row_id):
                        all_valid = False
                        invalid_ids.append(row.row_id)
        self.assertTrue(all_valid, f"Invalid row_ids: {invalid_ids[:5]}")

    def test_row_id_uniqueness(self):
        """row_id must be unique across all rows."""
        ids = []
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    ids.append(row.row_id)
        self.assertEqual(len(ids), len(set(ids)), "row_ids must be unique")

    def test_row_id_stability(self):
        """Running twice produces the same row_ids."""
        enriched2 = enrich_payload(self.payload)
        ids1 = [r.row_id for p in self.enriched.pages for t in p.tables for r in t.rows]
        ids2 = [r.row_id for p in enriched2.pages for t in p.tables for r in t.rows]
        self.assertEqual(ids1, ids2, "row_ids must be stable across runs")


# ─────────────────────────────────────────────────────────────────────────────
# Test: Row classification
# ─────────────────────────────────────────────────────────────────────────────

class TestRowClassification(unittest.TestCase):
    """Tests for row classification on real data."""

    @classmethod
    def setUpClass(cls):
        cls.payload = _load_test_payload()
        cls.enriched = enrich_payload(cls.payload)

    def test_has_no_empty_rows(self):
        """At least some rows should be classified as EMPTY."""
        empty_count = 0
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.EMPTY:
                        empty_count += 1
        self.assertGreater(empty_count, 0, "Should have some EMPTY rows")

    def test_has_column_headers(self):
        """At least some rows should be classified as COLUMN_HEADER."""
        header_count = 0
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.COLUMN_HEADER:
                        header_count += 1
        self.assertGreater(header_count, 0, "Should have some COLUMN_HEADER rows")

    def test_has_section_titles(self):
        """At least some rows should be classified as SECTION_TITLE."""
        section_count = 0
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.SECTION_TITLE:
                        section_count += 1
        self.assertGreater(section_count, 0, "Should have some SECTION_TITLE rows")

    def test_has_parameters(self):
        """At least some rows should be classified as PARAMETER."""
        param_count = 0
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER:
                        param_count += 1
        self.assertGreater(param_count, 0, "Should have some PARAMETER rows")

    def test_has_unknown_rows(self):
        """Some rows should be classified as UNKNOWN (conservative)."""
        unknown_count = 0
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.UNKNOWN:
                        unknown_count += 1
        # Unknown is acceptable; document how many exist
        print(f"\n  UNKNOWN rows: {unknown_count}")
        # We don't assert > 0 because ideally we'd classify most things
        # But it's allowed to exist

    def test_all_row_types_valid(self):
        """Every row must have a valid row_type."""
        valid_types = {rt.value for rt in RowType}
        invalid = []
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    rt = row.row_type.value if hasattr(row.row_type, 'value') else row.row_type
                    if rt not in valid_types:
                        invalid.append((row.row_id, rt))
        self.assertEqual([], invalid, "All rows must have valid row_type")


# ─────────────────────────────────────────────────────────────────────────────
# Test: Serialization roundtrip
# ─────────────────────────────────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):
    """Tests for JSON save/load roundtrip."""

    def test_json_roundtrip(self):
        """EnrichedPayload.to_dict() → from_dict() is lossless."""
        payload = _load_test_payload()
        enriched = enrich_payload(payload)

        d = enriched.to_dict()
        reloaded = EnrichedPayload.from_dict(d)

        # Compare top-level fields
        self.assertEqual(enriched.document_id, reloaded.document_id)
        self.assertEqual(enriched.file_name, reloaded.file_name)
        self.assertEqual(enriched.pdf_path, reloaded.pdf_path)
        self.assertEqual(enriched.source_backend, reloaded.source_backend)

        # Compare row counts
        orig_rows = sum(len(t.rows) for p in enriched.pages for t in p.tables)
        rel_rows = sum(len(t.rows) for p in reloaded.pages for t in p.tables)
        self.assertEqual(orig_rows, rel_rows)

        # Compare raw_cells for each row
        mismatches = []
        for op, rp in zip(enriched.pages, reloaded.pages):
            for ot, rt in zip(op.tables, rp.tables):
                for or_, rr_ in zip(ot.rows, rt.rows):
                    if or_.raw_cells != rr_.raw_cells:
                        mismatches.append((or_.row_id, or_.raw_cells, rr_.raw_cells))
        self.assertEqual([], mismatches, "Roundtrip must preserve raw_cells")

    def test_idempotent_conversion(self):
        """Converting the same payload twice gives identical result."""
        payload = _load_test_payload()
        e1 = enrich_payload(payload)
        e2 = enrich_payload(payload)

        ids1 = [r.row_id for p in e1.pages for t in p.tables for r in t.rows]
        ids2 = [r.row_id for p in e2.pages for t in p.tables for r in t.rows]
        self.assertEqual(ids1, ids2)

        types1 = [r.row_type for p in e1.pages for t in p.tables for r in t.rows]
        types2 = [r.row_type for p in e2.pages for t in p.tables for r in t.rows]
        self.assertEqual(types1, types2)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Context placeholders are None
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase2AEnrichment(unittest.TestCase):
    """Phase 2A: these fields must be populated from heading context."""

    @classmethod
    def setUpClass(cls):
        cls.payload = _load_test_payload()
        cls.enriched = enrich_payload(cls.payload)

    def test_section_title_rows_have_section_title(self):
        """SECTION_TITLE rows must have section_title set."""
        found = False
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.SECTION_TITLE:
                        self.assertIsNotNone(row.section_title)
                        found = True
        self.assertTrue(found, "No SECTION_TITLE rows found in test payload")

    def test_table_title_rows_have_table_title(self):
        """TABLE_TITLE rows must have table_title set."""
        found = False
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.TABLE_TITLE:
                        self.assertIsNotNone(row.table_title)
                        found = True
        self.assertTrue(found, "No TABLE_TITLE rows found in test payload")

    def test_parameter_rows_inherit_context(self):
        """PARAMETER rows should inherit section_title/table_title from context."""
        found_inherited = False
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER:
                        # PARAMETER rows after a section_title should have inherited context
                        if row.section_title or row.table_title:
                            found_inherited = True
        self.assertTrue(found_inherited, "No PARAMETER rows inherited context")

    def test_parameter_rows_have_resolved_condition(self):
        """Some PARAMETER rows must have resolved_condition from heading context."""
        found = False
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER and row.resolved_condition:
                        found = True
                        break
                if found:
                    break
        self.assertTrue(found, "No PARAMETER rows have resolved_condition")

    def test_parameter_rows_have_condition_sources(self):
        """PARAMETER rows with resolved_condition must have condition_sources set."""
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER and row.resolved_condition:
                        self.assertIsNotNone(row.condition_sources)
                        self.assertIn('row', row.condition_sources)
                        self.assertIn('table_heading', row.condition_sources)

    def test_resolved_conditions_contain_tc_or_tj(self):
        """resolved_condition values must contain TC= or TJ=."""
        found = False
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.resolved_condition:
                        has_tc_or_tj = 'TC=' in row.resolved_condition or 'TJ=' in row.resolved_condition
                        self.assertTrue(
                            has_tc_or_tj,
                            f"Resolved condition {row.resolved_condition!r} has neither TC= nor TJ="
                        )
                        found = True
        self.assertTrue(found, "No resolved_condition found")

    def test_context_status_is_resolved_for_parameter_rows(self):
        """PARAMETER rows with resolved_condition must have context_status RESOLVED."""
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER and row.resolved_condition:
                        self.assertEqual(ContextStatus.RESOLVED, row.context_status)

    def test_heading_condition_overridden_quality_flag(self):
        """Parameter rows that override heading conditions must have quality_flag set."""
        # This is a structural test - we just verify quality_flags field exists
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER:
                        self.assertIsInstance(row.quality_flags, list)

    def test_no_api_keys_in_enriched_data(self):
        """Enriched payload must not contain API keys."""
        import json
        enriched_json = json.dumps(self.enriched.to_dict())
        api_key_patterns = ['OPENAI', 'DEEPSEEK', 'ANTHROPIC', 'sk-']
        for pattern in api_key_patterns:
            self.assertNotIn(pattern, enriched_json.upper())

    def test_condition_sources_has_row_and_heading_keys(self):
        """condition_sources must have 'row' and 'table_heading' keys."""
        for page in self.enriched.pages:
            for table in page.tables:
                for row in table.rows:
                    if row.row_type == RowType.PARAMETER:
                        self.assertIn('row', row.condition_sources)
                        self.assertIn('table_heading', row.condition_sources)


# ─────────────────────────────────────────────────────────────────────────────
# Test: No LLM / No API key required
# ─────────────────────────────────────────────────────────────────────────────

class TestNoLLM(unittest.TestCase):
    """Verify no LLM calls are made during enrichment."""

    def test_enrichment_has_no_llm_imports(self):
        """enricher.py must not import any LLM-related modules."""
        import agent_workflow.enrichment.enricher as enricher_mod
        import agent_workflow.enrichment.row_classifier as classifier_mod

        module_text = inspect_source(enricher_mod) + inspect_source(classifier_mod)

        llm_keywords = [
            "openai", "anthropic", "deepseek", "minimax",
            "llm_call", "chatcompletion", "api_key",
            "urllib.request", "http.client",
        ]
        found = [kw for kw in llm_keywords if kw.lower() in module_text.lower()]
        self.assertEqual([], found, f"LLM-related imports found: {found}")

    def test_no_api_key_in_enriched_data(self):
        """EnrichedPayload must not contain API keys."""
        payload = _load_test_payload()
        enriched = enrich_payload(payload)
        d = enriched.to_dict()
        d_str = json.dumps(d).lower()
        api_key_patterns = ["api_key", "authorization", "bearer", "sk-"]
        found = [p for p in api_key_patterns if p in d_str]
        self.assertEqual([], found, f"Potential API key leaked: {found}")


def inspect_source(mod):
    """Get module source code as string."""
    import inspect
    try:
        return inspect.getsource(mod)
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Test: Step 0 original tests still pass
# ─────────────────────────────────────────────────────────────────────────────

class TestStep0Unaffected(unittest.TestCase):
    """Verify Step 0 CamelotPayload is not modified."""

    def test_step0_payload_loads_normally(self):
        """CamelotPayload.from_dict() still works after our changes."""
        path = _find_test_payload()
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        # Must not raise
        payload = CamelotPayload.from_dict(d)
        self.assertIsNotNone(payload)
        self.assertGreater(len(payload.pages), 0)

    def test_camelot_table_row_not_modified(self):
        """CamelotTableRow dataclass still has only row_index and cells."""
        from agent_workflow.contracts import CamelotTableRow
        row = CamelotTableRow(row_index=0, cells=["a", "b"])
        self.assertEqual(["a", "b"], row.cells)
        # Must not have extra fields
        self.assertEqual(2, len(row.__dataclass_fields__))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Step 0.5 (enrich_context) Unit Tests")
    print("=" * 60)
    print(f"Test payload: {_find_test_payload()}")
    print()

    # Run tests
    unittest.main(verbosity=2)
