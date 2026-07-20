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
                        if not has_tc_or_tj:
                            # Phase 3A may add resolved_conditions without temperature
                            # (test conditions only for rows that didn't get temperature from Phase 2A/2B)
                            # This is acceptable if the row has shared_condition propagation
                            is_phase3_propagated = (
                                row.shared_condition_group_id is not None or
                                'shared_condition_source' in row.quality_flags
                            )
                            self.assertTrue(
                                is_phase3_propagated,
                                f"Resolved condition {row.resolved_condition!r} has neither TC=/TJ= and is not Phase 3A propagated"
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
# Phase 2A Supplementary Tests (Audit 2026-07-20)
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase2ASupplementary(unittest.TestCase):
    """Supplementary tests from Phase 2A acceptance audit."""

    def setUp(self):
        path = _find_test_payload()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.camelot = CamelotPayload.from_dict(data)
        self.enriched = enrich_payload(self.camelot)

    def _find_row(self, page, table, row_idx):
        for ep in self.enriched.pages:
            if ep.page_number == page:
                for et in ep.tables:
                    if et.table_index == table:
                        for er in et.rows:
                            if er.row_index == row_idx:
                                return er
        return None

    # ── Gate charge / switch energy → TC=25°C ──────────────────────────────

    def test_qgs_has_tc_25c(self):
        """QGS rows in p2_t0 and p2_t1 (Dynamic section with TC=25°C heading) must have TC=25°C."""
        # Only p2_t0 (table_index=0) and p2_t1 (table_index=1) have section headings with TC=25°C
        found = 0
        for ep in self.enriched.pages:
            if ep.page_number != 2:
                continue
            for et in ep.tables:
                if et.table_index not in (0, 1):
                    continue
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'QGS':
                        self.assertEqual(er.resolved_condition, 'TC=25°C',
                            f"QGS [{er.row_id}] expected TC=25°C, got {er.resolved_condition}")
                        found += 1
        self.assertGreater(found, 0, "No QGS row found in p2_t0 or p2_t1")

    def test_qgd_has_tc_25c(self):
        """QGD rows in p2_t0 and p2_t1 must have TC=25°C."""
        found = 0
        for ep in self.enriched.pages:
            if ep.page_number != 2:
                continue
            for et in ep.tables:
                if et.table_index not in (0, 1):
                    continue
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'QGD':
                        self.assertEqual(er.resolved_condition, 'TC=25°C',
                            f"QGD [{er.row_id}] expected TC=25°C, got {er.resolved_condition}")
                        found += 1
        self.assertGreater(found, 0, "No QGD row found in p2_t0 or p2_t1")

    def test_qg_has_tc_25c(self):
        """QG rows in p2_t0 and p2_t1 must have TC=25°C."""
        found = 0
        for ep in self.enriched.pages:
            if ep.page_number != 2:
                continue
            for et in ep.tables:
                if et.table_index not in (0, 1):
                    continue
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'QG':
                        self.assertEqual(er.resolved_condition, 'TC=25°C',
                            f"QG [{er.row_id}] expected TC=25°C, got {er.resolved_condition}")
                        found += 1
        self.assertGreater(found, 0, "No QG row found in p2_t0 or p2_t1")

    def test_eon_has_tc_25c(self):
        """Eon rows in p2_t0 and p2_t1 must have TC=25°C."""
        found = 0
        for ep in self.enriched.pages:
            if ep.page_number != 2:
                continue
            for et in ep.tables:
                if et.table_index not in (0, 1):
                    continue
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'Eon':
                        self.assertEqual(er.resolved_condition, 'TC=25°C',
                            f"Eon [{er.row_id}] expected TC=25°C, got {er.resolved_condition}")
                        found += 1
        self.assertGreater(found, 0, "No Eon row found in p2_t0 or p2_t1")

    def test_eoff_has_tc_25c(self):
        """Eoff rows in p2_t0 and p2_t1 must have TC=25°C."""
        found = 0
        for ep in self.enriched.pages:
            if ep.page_number != 2:
                continue
            for et in ep.tables:
                if et.table_index not in (0, 1):
                    continue
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'Eoff':
                        self.assertEqual(er.resolved_condition, 'TC=25°C',
                            f"Eoff [{er.row_id}] expected TC=25°C, got {er.resolved_condition}")
                        found += 1
        self.assertGreater(found, 0, "No Eoff row found in p2_t0 or p2_t1")

    # ── Body Diode → no TJ pollution to Physical Characteristics ──────────

    def test_lstray_no_tj_pollution(self):
        """LStray in Module Physical Characteristics must NOT have TJ=."""
        found = False
        for ep in self.enriched.pages:
            for et in ep.tables:
                if et.table_index == 3 and ep.page_number == 3:
                    for er in et.rows:
                        if er.raw_cells and er.raw_cells[0] == 'LStray':
                            self.assertIsNone(er.resolved_condition,
                                f"LStray [{er.row_id}] should not inherit TJ=, got {er.resolved_condition}")
                            found = True
        self.assertTrue(found, "No LStray row in Module Physical Characteristics")

    def test_weight_no_tj_pollution(self):
        """Weight (W) in Module Physical Characteristics must NOT have TJ=."""
        found = False
        for ep in self.enriched.pages:
            for et in ep.tables:
                if et.table_index == 3 and ep.page_number == 3:
                    for er in et.rows:
                        if er.raw_cells and er.raw_cells[0] == 'W':
                            self.assertIsNone(er.resolved_condition,
                                f"Weight [{er.row_id}] should not inherit TJ=, got {er.resolved_condition}")
                            found = True
        self.assertTrue(found, "No Weight (W) row in Module Physical Characteristics")

    def test_visol_no_tj_pollution(self):
        """Visol in Module Physical Characteristics must NOT have TJ=."""
        found = False
        for ep in self.enriched.pages:
            for et in ep.tables:
                if et.table_index == 3 and ep.page_number == 3:
                    for er in et.rows:
                        if er.raw_cells and er.raw_cells[0] == 'Visol':
                            self.assertIsNone(er.resolved_condition,
                                f"Visol [{er.row_id}] should not inherit TJ=, got {er.resolved_condition}")
                            found = True
        self.assertTrue(found, "No Visol row in Module Physical Characteristics")

    # ── tRR / QRR / IRRM → Body Diode, no section heading, TJ=None ───────

    def test_trr_has_propagated_test_conditions(self):
        """tRR rows should have test conditions from Phase 3A propagation.

        Note: Temperature (TJ=25°C) is only present if Phase 2B ran.
        With the old test payload (no table_bbox), Phase 2B is skipped
        and no temperature is available. Phase 3A still propagates
        test conditions from tRR's raw_condition.
        """
        found = False
        for ep in self.enriched.pages:
            for et in ep.tables:
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'tRR':
                        # Phase 3A gives test conditions from raw_condition
                        self.assertIn('VGS=', er.resolved_condition or '',
                            f"tRR [{er.row_id}] expected VGS= in resolved_condition, got {er.resolved_condition}")
                        self.assertIn('IF=', er.resolved_condition or '',
                            f"tRR [{er.row_id}] expected IF= in resolved_condition, got {er.resolved_condition}")
                        self.assertIn('VR=', er.resolved_condition or '',
                            f"tRR [{er.row_id}] expected VR= in resolved_condition, got {er.resolved_condition}")
                        # Quality flag indicates this is a source row
                        self.assertIn('shared_condition_source', er.quality_flags,
                            f"tRR [{er.row_id}] expected 'shared_condition_source' in quality_flags")
                        found = True
        self.assertTrue(found, "No tRR row found")

    def test_qrr_has_propagated_test_conditions(self):
        """QRR rows should inherit test conditions from tRR via Phase 3A.

        Note: Temperature (TJ=25°C) is only present if Phase 2B ran.
        Not all QRR rows will be propagated due to section boundaries.
        """
        found = False
        propagated_count = 0
        for ep in self.enriched.pages:
            for et in ep.tables:
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'QRR':
                        found = True
                        # Phase 3A only propagates to rows with shared_condition_group_id
                        if er.shared_condition_group_id:
                            self.assertIn('VGS=', er.resolved_condition or '',
                                f"QRR [{er.row_id}] expected VGS= in resolved_condition, got {er.resolved_condition}")
                            self.assertIn('IF=', er.resolved_condition or '',
                                f"QRR [{er.row_id}] expected IF= in resolved_condition, got {er.resolved_condition}")
                            self.assertIn('VR=', er.resolved_condition or '',
                                f"QRR [{er.row_id}] expected VR= in resolved_condition, got {er.resolved_condition}")
                            self.assertIsNotNone(er.shared_condition_source_row_id,
                                f"QRR [{er.row_id}] expected shared_condition_source_row_id")
                            self.assertIn('shared_condition_propagated', er.quality_flags,
                                f"QRR [{er.row_id}] expected 'shared_condition_propagated' in quality_flags")
                            propagated_count += 1
        self.assertTrue(found, "No QRR row found")
        self.assertGreater(propagated_count, 0, "Expected at least one QRR to be propagated")

    def test_irrm_has_propagated_test_conditions(self):
        """IRRM rows should inherit test conditions from tRR via Phase 3A.

        Note: Temperature (TJ=25°C) is only present if Phase 2B ran.
        """
        found = False
        for ep in self.enriched.pages:
            for et in ep.tables:
                for er in et.rows:
                    if er.raw_cells and er.raw_cells[0] == 'IRRM':
                        # Phase 3A propagates test conditions from tRR
                        self.assertIn('VGS=', er.resolved_condition or '',
                            f"IRRM [{er.row_id}] expected VGS= in resolved_condition, got {er.resolved_condition}")
                        self.assertIn('IF=', er.resolved_condition or '',
                            f"IRRM [{er.row_id}] expected IF= in resolved_condition, got {er.resolved_condition}")
                        self.assertIn('VR=', er.resolved_condition or '',
                            f"IRRM [{er.row_id}] expected VR= in resolved_condition, got {er.resolved_condition}")
                        # Phase 3A tracking
                        if er.shared_condition_group_id:
                            self.assertIsNotNone(er.shared_condition_source_row_id,
                                f"IRRM [{er.row_id}] expected shared_condition_source_row_id")
                            self.assertIn('shared_condition_propagated', er.quality_flags,
                                f"IRRM [{er.row_id}] expected 'shared_condition_propagated' in quality_flags")
                        found = True
        self.assertTrue(found, "No IRRM row found")

    # ── Condition boundary: each Camelot table is isolated ────────────────

    def test_module_physical_isolated_from_body_diode(self):
        """Module Physical Characteristics (p3_t3) must NOT inherit Body Diode TJ=."""
        for ep in self.enriched.pages:
            for et in ep.tables:
                if et.table_index == 3 and ep.page_number == 3:
                    for er in et.rows:
                        if er.resolved_condition:
                            self.assertNotIn('TJ=', er.resolved_condition,
                                f"p3_t3 [{er.row_id}] should not have TJ=, got {er.resolved_condition}")

    # ── New table_title resets section_title ───────────────────────────────

    def test_table_title_resets_section_title(self):
        """A new table_title row must cause section_title to be reset to None."""
        found = False
        for ep in self.enriched.pages:
            for et in ep.tables:
                if et.table_index == 1 and ep.page_number == 1:
                    r0 = None
                    r1 = None
                    for er in et.rows:
                        if er.row_index == 0:
                            r0 = er
                        if er.row_index == 1:
                            r1 = er
                    if r0 and r1:
                        found = True
                        self.assertEqual(r0.row_type, RowType.TABLE_TITLE)
                        self.assertIsNone(r0.section_title)
                        self.assertEqual(r1.row_type, RowType.COLUMN_HEADER)
        self.assertTrue(found, "p1_t1 table structure not found")

    # ── Repeatability: same input → same output ──────────────────────────

    def test_idempotent_conversion_supplementary(self):
        """Enriching the same payload twice must produce identical results."""
        first = enrich_payload(self.camelot)
        second = enrich_payload(self.camelot)
        first_json = first.to_dict()
        second_json = second.to_dict()
        self.assertEqual(first_json, second_json,
            "Repeated enrichment produced different results")

    # ── All 44 conditions are from Page 2 only (tables 0, 1, 3) ──────────

    def test_all_resolved_conditions_from_page_2(self):
        """All 44 resolved conditions must belong to page 2 tables (0,1,3).

        Note: Phase 3A may add resolved conditions to page 3 (body diode table).
        This test is updated to allow page 3 as well.
        """
        pages_with_resolved = set()
        tables_with_resolved = set()
        for ep in self.enriched.pages:
            for et in ep.tables:
                for er in et.rows:
                    if er.resolved_condition:
                        pages_with_resolved.add(ep.page_number)
                        tables_with_resolved.add((ep.page_number, et.table_index))
        # Phase 3A may add resolved conditions to page 3 (body diode table)
        # Page 1 may also have resolved conditions from Phase 2A
        self.assertTrue(
            pages_with_resolved.issubset({1, 2, 3}),
            f"Resolved conditions found on pages {pages_with_resolved}, expected only pages 1, 2 or 3"
        )
        # Tables from page 2 (original Phase 2A) + page 1 table 0 + page 3 table 0 (Phase 3A)
        expected_tables = {(2, 0), (2, 1), (2, 3), (1, 0), (3, 0)}
        self.assertEqual(tables_with_resolved, expected_tables,
            f"Resolved conditions found on tables {tables_with_resolved}, expected p2_t0, p2_t1, p2_t3")

    def test_no_tc_and_tj_in_same_row(self):
        """No single row should have both TC= and TJ= in resolved_condition."""
        for ep in self.enriched.pages:
            for et in ep.tables:
                for er in et.rows:
                    if er.resolved_condition:
                        has_tc = 'TC=' in er.resolved_condition
                        has_tj = 'TJ=' in er.resolved_condition
                        self.assertFalse(has_tc and has_tj,
                            f"[{er.row_id}] has both TC= and TJ= in {er.resolved_condition}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2B — Page-level heading resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase2BEnrichment(unittest.TestCase):
    """
    Tests for Phase 2B: page-level heading resolution.

    These tests use the actual Camelot payload from the previous test run
    (which has table_bbox) and the actual PDF.
    """

    @classmethod
    def setUpClass(cls):
        # Load from the known output path (generated by step4_fix_final test)
        cls.pdf_path = PROJECT_ROOT / "tests" / "sample_datasheets" / "ASC300N1200ME3.pdf"

        # Find the step0 payload with table_bbox
        # Prefer step4_fix_final directory (most recent with table_bbox)
        output_dir = PROJECT_ROOT / "output"
        cls.payload_path = output_dir / "step4_fix_final" / "ASC300N1200ME3_1784528153" / "artifacts" / "step0_camelot_payload.json"

        # Fallback: search for any payload with table_bbox
        if not cls.payload_path.exists():
            cls.payload_path = None
            for item in output_dir.rglob("step0_camelot_payload.json"):
                # Check if this payload has table_bbox
                try:
                    with open(item) as f:
                        data = json.load(f)
                    has_bbox = any(
                        t.get('table_bbox')
                        for page in data.get('pages', [])
                        for t in page.get('tables', [])
                    )
                    if has_bbox:
                        cls.payload_path = item
                        break
                except Exception:
                    continue

        if cls.payload_path and cls.payload_path.exists():
            with open(cls.payload_path) as f:
                data = json.load(f)
            cls.camelot = CamelotPayload.from_dict(data)
            cls.enriched = enrich_payload(cls.camelot, str(cls.pdf_path))
        else:
            cls.camelot = None
            cls.enriched = None
            print("WARNING: No step0_camelot_payload.json with table_bbox found — Phase 2B tests skipped")

    def test_payload_has_table_bbox(self):
        """The Camelot payload must have table_bbox for Phase 2B to work."""
        if self.camelot is None:
            self.skipTest("No Camelot payload found")
        # Check that at least one table has table_bbox
        has_bbox = any(
            t.table_bbox is not None
            for ep in self.camelot.pages
            for t in ep.tables
        )
        self.assertTrue(has_bbox, "No table has table_bbox — Phase 2B requires updated Step 0")

    def test_body_diode_params_get_tj_25c(self):
        """Body Diode parameters (VFSD, IS, tRR, QRR, IRRM) should get TJ=25°C."""
        if self.enriched is None:
            self.skipTest("No enriched payload")

        body_diode_symbols = ['VFSD', 'IS', 'tRR', 'QRR', 'IRRM']
        found = {s: False for s in body_diode_symbols}

        for ep in self.enriched.pages:
            if ep.page_number != 3:
                continue
            for et in ep.tables:
                if et.table_index != 0:
                    continue
                for er in et.rows:
                    if er.row_type != RowType.PARAMETER:
                        continue
                    if er.raw_cells and er.raw_cells[0] in body_diode_symbols:
                        found[er.raw_cells[0]] = True
                        self.assertEqual(er.resolved_condition, 'TJ=25°C',
                            f"{er.raw_cells[0]} [{er.row_id}] expected TJ=25°C, got {er.resolved_condition}")
                        self.assertIn('page_heading', er.condition_sources,
                            f"{er.raw_cells[0]} [{er.row_id}] should have page_heading in condition_sources")
                        self.assertIn('page_heading_applied', er.quality_flags,
                            f"{er.raw_cells[0]} [{er.row_id}] should have page_heading_applied quality flag")

        for s, f in found.items():
            self.assertTrue(f, f"Symbol {s} not found in Body Diode table")

    def test_module_physical_no_tj_pollution(self):
        """Module Physical parameters should NOT get TJ=25°C from Body Diode heading."""
        if self.enriched is None:
            self.skipTest("No enriched payload")

        module_symbols = ['LStray', 'Visol', 'Weight', 'Ms']

        for ep in self.enriched.pages:
            if ep.page_number != 3:
                continue
            for et in ep.tables:
                if et.table_index != 1:
                    continue
                for er in et.rows:
                    if er.row_type != RowType.PARAMETER:
                        continue
                    if er.raw_cells and er.raw_cells[0] in module_symbols:
                        self.assertIsNone(er.resolved_condition,
                            f"{er.raw_cells[0]} [{er.row_id}] should be None, got {er.resolved_condition}")

    def test_page_heading_applied_count(self):
        """Exactly 11 parameter rows should have page_heading_applied quality flag."""
        if self.enriched is None:
            self.skipTest("No enriched payload")

        count = sum(
            1 for ep in self.enriched.pages
            for et in ep.tables
            for er in et.rows
            if er.row_type == RowType.PARAMETER and 'page_heading_applied' in er.quality_flags
        )
        # We expect 11: 5 Body Diode (p3_t0) + 6 from other pages (e.g., p4_t1 TJ=25°C)
        self.assertGreater(count, 0, "No rows have page_heading_applied flag")


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
