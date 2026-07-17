"""
step3_agent_cross_check.py — Step 3: Agent 3 — Cross-Parameter Consistency Check

Validates cross-parameter consistency relationships.
This step uses rule-based logic (no LLM call) for deterministic checking.

Input:  Agent2Result (from Step 2)
Output: Agent3Result (consistency report)
"""

import json
import logging
from pathlib import Path

from ..contracts import (
    Agent2Result,
    Agent3Result,
    ConsistencyCheck,
    FieldStatus,
)
from ..artifacts import ArtifactPaths, save_agent3, load_agent2

logger = logging.getLogger(__name__)


def _get_field(params: list, field_id: str):
    return next((p for p in params if p.field_id == field_id), None)


def _typ(p) -> float | None:
    if p is None:
        return None
    return float(p.typ) if p.typ is not None else (float(p.value) if p.value is not None else None)


def _max_v(p) -> float | None:
    if p is None:
        return None
    return float(p.max) if p.max is not None else None


def _min_v(p) -> float | None:
    if p is None:
        return None
    return float(p.min) if p.min is not None else None


def nF_to_pF(nF: float) -> float:
    return nF * 1000.0


def get_capacitance_in_pF(p) -> float | None:
    """Get capacitance value normalized to pF."""
    v = _typ(p)
    if v is None:
        return None
    unit = (p.unit or "").strip().lower()
    if unit == "pf":
        return v
    elif unit == "nf":
        return nF_to_pF(v)
    return None


def check_rds_temperature_coefficient(params: list) -> ConsistencyCheck:
    """RDS(on)@150°C should be > RDS(on)@25°C (positive temperature coefficient)."""
    rds25 = _get_field(params, "rds_on_25c")
    rds150 = _get_field(params, "rds_on_150c")

    details = {}
    if rds25 is None or rds150 is None:
        return ConsistencyCheck(
            rule_id="RDS_TEMP_COEFFICIENT",
            rule_name="RDS(on) 温度特性",
            severity="critical",
            status="skipped",
            fields_involved=["rds_on_25c", "rds_on_150c"],
            details=details,
            verdict="SKIPPED: missing rds_on_25c or rds_on_150c data",
            suggested_action="none",
        )

    v25 = _typ(rds25)
    v150 = _typ(rds150)
    details["rds_on_25c_typ"] = v25
    details["rds_on_150c_typ"] = v150

    if v25 is None:
        return ConsistencyCheck(
            rule_id="RDS_TEMP_COEFFICIENT", rule_name="RDS(on) 温度特性",
            severity="critical", status="skipped",
            fields_involved=["rds_on_25c", "rds_on_150c"],
            details=details,
            verdict="SKIPPED: rds_on_25c has no typ value",
            suggested_action="none",
        )

    if v150 is None:
        return ConsistencyCheck(
            rule_id="RDS_TEMP_COEFFICIENT", rule_name="RDS(on) 温度特性",
            severity="critical", status="skipped",
            fields_involved=["rds_on_25c", "rds_on_150c"],
            details=details,
            verdict="SKIPPED: rds_on_150c is blocked (no TC=150°C candidate)",
            suggested_action="none",
        )

    ratio = v150 / v25
    details["ratio"] = round(ratio, 3)
    details["expected_range"] = "1.3x ~ 2.5x"

    if ratio < 1.0:
        return ConsistencyCheck(
            rule_id="RDS_TEMP_COEFFICIENT", rule_name="RDS(on) 温度特性",
            severity="critical", status="fail",
            fields_involved=["rds_on_25c", "rds_on_150c"],
            details=details,
            verdict=f"FAIL: rds_on_150c ({v150}mΩ) < rds_on_25c ({v25}mΩ)",
            suggested_action="review",
        )

    if ratio < 1.3 or ratio > 2.5:
        return ConsistencyCheck(
            rule_id="RDS_TEMP_COEFFICIENT", rule_name="RDS(on) 温度特性",
            severity="high", status="warning",
            fields_involved=["rds_on_25c", "rds_on_150c"],
            details=details,
            verdict=f"WARNING: ratio={ratio:.2f}x outside 1.3x~2.5x range",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="RDS_TEMP_COEFFICIENT", rule_name="RDS(on) 温度特性",
        severity="critical", status="pass",
        fields_involved=["rds_on_25c", "rds_on_150c"],
        details=details,
        verdict=f"PASS: ratio={ratio:.2f}x within range",
        suggested_action="none",
    )


def check_gate_charge_hierarchy(params: list) -> ConsistencyCheck:
    """QG > QGS and QG > QGD; QGS+QGD <= QG*1.3."""
    qg = _get_field(params, "qg")
    qgs = _get_field(params, "qgs")
    qgd = _get_field(params, "qgd")

    qg_v = _typ(qg)
    qgs_v = _typ(qgs)
    qgd_v = _typ(qgd)

    details = {"qg_typ": qg_v, "qgs_typ": qgs_v, "qgd_typ": qgd_v}

    if None in [qg_v, qgs_v, qgd_v]:
        return ConsistencyCheck(
            rule_id="GATE_CHARGE_HIERARCHY", rule_name="栅极电荷层级",
            severity="critical", status="skipped",
            fields_involved=["qg", "qgs", "qgd"],
            details=details,
            verdict="SKIPPED: missing QG/QGS/QGD values",
            suggested_action="none",
        )

    failures = []
    if qg_v <= qgs_v:
        failures.append(f"QG({qg_v}nC) <= QGS({qgs_v}nC)")
    if qg_v <= qgd_v:
        failures.append(f"QG({qg_v}nC) <= QGD({qgd_v}nC)")

    sum_ratio = (qgs_v + qgd_v) / qg_v
    details["sum_ratio"] = round(sum_ratio, 3)

    warnings = []
    if sum_ratio > 1.3:
        warnings.append(f"QGS+QGD={qgs_v+qgd_v:.1f}nC > QG*1.3")

    if failures:
        return ConsistencyCheck(
            rule_id="GATE_CHARGE_HIERARCHY", rule_name="栅极电荷层级",
            severity="critical", status="fail",
            fields_involved=["qg", "qgs", "qgd"],
            details=details,
            verdict=f"FAIL: {'; '.join(failures)}",
            suggested_action="review",
        )

    if warnings:
        return ConsistencyCheck(
            rule_id="GATE_CHARGE_HIERARCHY", rule_name="栅极电荷层级",
            severity="high", status="warning",
            fields_involved=["qg", "qgs", "qgd"],
            details=details,
            verdict=f"WARNING: {'; '.join(warnings)}",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="GATE_CHARGE_HIERARCHY", rule_name="栅极电荷层级",
        severity="critical", status="pass",
        fields_involved=["qg", "qgs", "qgd"],
        details=details,
        verdict=f"PASS: QG({qg_v}nC) > QGS({qgs_v}nC) + QGD({qgd_v}nC), sum_ratio={sum_ratio:.2f}x",
        suggested_action="none",
    )


def check_capacitance_hierarchy(params: list) -> ConsistencyCheck:
    """Ciss >> Coss > Crss (in pF)."""
    ciss_pf = get_capacitance_in_pF(_get_field(params, "ciss"))
    coss_pf = get_capacitance_in_pF(_get_field(params, "coss"))
    crss_pf = get_capacitance_in_pF(_get_field(params, "crss"))

    details = {"ciss_pF": ciss_pf, "coss_pF": coss_pf, "crss_pF": crss_pf}

    if None in [ciss_pf, coss_pf, crss_pf]:
        return ConsistencyCheck(
            rule_id="CAPACITANCE_HIERARCHY", rule_name="电容层级",
            severity="critical", status="skipped",
            fields_involved=["ciss", "coss", "crss"],
            details=details,
            verdict="SKIPPED: missing capacitance values",
            suggested_action="none",
        )

    failures = []
    if ciss_pf <= coss_pf:
        failures.append(f"Ciss({ciss_pf:.1f}pF) <= Coss({coss_pf:.1f}pF)")
    if coss_pf <= crss_pf:
        failures.append(f"Coss({coss_pf:.1f}pF) <= Crss({crss_pf:.1f}pF)")

    ratio = ciss_pf / crss_pf
    details["ciss_crss_ratio"] = round(ratio, 1)

    if failures:
        return ConsistencyCheck(
            rule_id="CAPACITANCE_HIERARCHY", rule_name="电容层级",
            severity="critical", status="fail",
            fields_involved=["ciss", "coss", "crss"],
            details=details,
            verdict=f"FAIL: {'; '.join(failures)}",
            suggested_action="review",
        )

    return ConsistencyCheck(
        rule_id="CAPACITANCE_HIERARCHY", rule_name="电容层级",
        severity="critical", status="pass",
        fields_involved=["ciss", "coss", "crss"],
        details=details,
        verdict=f"PASS: Ciss({ciss_pf:.0f}pF) >> Coss({coss_pf:.0f}pF) > Crss({crss_pf:.0f}pF)",
        suggested_action="none",
    )


def check_reverse_recovery_consistency(params: list) -> ConsistencyCheck:
    """Qrr ≈ 0.5 * trr(ns) * IRRM(A) * 1e-3 (in μC)."""
    trr_v = _typ(_get_field(params, "trr"))
    qrr_v = _typ(_get_field(params, "qrr"))
    irrm_v = _typ(_get_field(params, "irrm"))

    details = {"trr": trr_v, "qrr": qrr_v, "irrm": irrm_v}

    if None in [trr_v, qrr_v, irrm_v]:
        return ConsistencyCheck(
            rule_id="REVERSE_RECOVERY_CONSISTENCY", rule_name="反向恢复一致性",
            severity="high", status="skipped",
            fields_involved=["trr", "qrr", "irrm"],
            details=details,
            verdict="SKIPPED: missing trr/qrr/irrm values",
            suggested_action="none",
        )

    # Expected Qrr in μC = 0.5 * trr(ns) * IRRM(A) * 1e-3
    expected_uc = 0.5 * trr_v * irrm_v * 1e-3
    expected_nc = expected_uc * 1000

    details["expected_qrr_uc"] = round(expected_uc, 4)
    details["expected_qrr_nc"] = round(expected_nc, 4)

    ratio_if_nc = qrr_v / expected_nc if expected_nc > 0 else float("inf")
    ratio_if_uc = qrr_v / expected_uc if expected_uc > 0 else float("inf")

    details["ratio_if_qrr_is_nC"] = round(ratio_if_nc, 2)
    details["ratio_if_qrr_is_uC"] = round(ratio_if_uc, 2)

    nc_ok = 0.2 <= ratio_if_nc <= 3.0
    uc_ok = 0.2 <= ratio_if_uc <= 3.0

    if nc_ok and not uc_ok:
        return ConsistencyCheck(
            rule_id="REVERSE_RECOVERY_CONSISTENCY", rule_name="反向恢复一致性",
            severity="high", status="pass",
            fields_involved=["trr", "qrr", "irrm"],
            details=details,
            verdict=f"PASS: Qrr({qrr_v}nC) ratio={ratio_if_nc:.1f}x consistent as nC",
            suggested_action="none",
        )

    if uc_ok and not nc_ok:
        return ConsistencyCheck(
            rule_id="REVERSE_RECOVERY_CONSISTENCY", rule_name="反向恢复一致性",
            severity="high", status="warning",
            fields_involved=["trr", "qrr", "irrm"],
            details=details,
            verdict=f"WARNING: Qrr({qrr_v}) labeled as nC but ratio consistent with μC. Unit may be wrong.",
            suggested_action="warning",
        )

    if not nc_ok and not uc_ok:
        return ConsistencyCheck(
            rule_id="REVERSE_RECOVERY_CONSISTENCY", rule_name="反向恢复一致性",
            severity="high", status="warning",
            fields_involved=["trr", "qrr", "irrm"],
            details=details,
            verdict=f"WARNING: Qrr({qrr_v}) inconsistent with trr({trr_v}ns)*IRRM({irrm_v}A)",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="REVERSE_RECOVERY_CONSISTENCY", rule_name="反向恢复一致性",
        severity="high", status="pass",
        fields_involved=["trr", "qrr", "irrm"],
        details=details,
        verdict=f"PASS: Qrr consistent",
        suggested_action="none",
    )


def check_switching_energy(params: list) -> ConsistencyCheck:
    """Eon and Eoff should be comparable (within 3.3x)."""
    eon_v = _typ(_get_field(params, "eon"))
    eoff_v = _typ(_get_field(params, "eoff"))

    details = {"eon": eon_v, "eoff": eoff_v}

    if None in [eon_v, eoff_v]:
        return ConsistencyCheck(
            rule_id="SWITCHING_ENERGY_CONSISTENCY", rule_name="开关能量可比性",
            severity="high", status="skipped",
            fields_involved=["eon", "eoff"],
            details=details,
            verdict="SKIPPED: missing Eon/Eoff",
            suggested_action="none",
        )

    if eon_v == 0 or eoff_v == 0:
        return ConsistencyCheck(
            rule_id="SWITCHING_ENERGY_CONSISTENCY", rule_name="开关能量可比性",
            severity="high", status="fail",
            fields_involved=["eon", "eoff"],
            details=details,
            verdict="FAIL: Eon or Eoff is zero",
            suggested_action="review",
        )

    ratio = max(eon_v, eoff_v) / min(eon_v, eoff_v)
    details["ratio"] = round(ratio, 2)

    if ratio > 3.3:
        return ConsistencyCheck(
            rule_id="SWITCHING_ENERGY_CONSISTENCY", rule_name="开关能量可比性",
            severity="high", status="warning",
            fields_involved=["eon", "eoff"],
            details=details,
            verdict=f"WARNING: Eon/Eoff ratio={ratio:.1f}x > 3.3x",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="SWITCHING_ENERGY_CONSISTENCY", rule_name="开关能量可比性",
        severity="high", status="pass",
        fields_involved=["eon", "eoff"],
        details=details,
        verdict=f"PASS: Eon/Eoff ratio={ratio:.2f}x within range",
        suggested_action="none",
    )


def check_junction_temperature(params: list) -> ConsistencyCheck:
    """Tj_max should be in reasonable range (150-200°C for SiC)."""
    tj = _get_field(params, "junction_temperature")
    tj_max = _max_v(tj)

    details = {"tj_max": tj_max}

    if tj_max is None:
        return ConsistencyCheck(
            rule_id="JUNCTION_TEMPERATURE_RANGE", rule_name="Tj_max 范围",
            severity="high", status="skipped",
            fields_involved=["junction_temperature"],
            details=details,
            verdict="SKIPPED: no junction_temperature max",
            suggested_action="none",
        )

    if tj_max < 120 or tj_max > 225:
        return ConsistencyCheck(
            rule_id="JUNCTION_TEMPERATURE_RANGE", rule_name="Tj_max 范围",
            severity="high", status="fail",
            fields_involved=["junction_temperature"],
            details=details,
            verdict=f"FAIL: Tj_max={tj_max}°C outside 120-225°C",
            suggested_action="review",
        )

    if tj_max < 150 or tj_max > 200:
        return ConsistencyCheck(
            rule_id="JUNCTION_TEMPERATURE_RANGE", rule_name="Tj_max 范围",
            severity="medium", status="warning",
            fields_involved=["junction_temperature"],
            details=details,
            verdict=f"WARNING: Tj_max={tj_max}°C outside typical 150-200°C",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="JUNCTION_TEMPERATURE_RANGE", rule_name="Tj_max 范围",
        severity="high", status="pass",
        fields_involved=["junction_temperature"],
        details=details,
        verdict=f"PASS: Tj_max={tj_max}°C within range",
        suggested_action="none",
    )


def check_vgsth_range(params: list) -> ConsistencyCheck:
    """VGS(th) should be in reasonable range (1.5V-5.5V for SiC)."""
    vgs = _get_field(params, "vgs_th")
    vgs_min = _min_v(vgs)
    vgs_max = _max_v(vgs)

    details = {"vgs_min": vgs_min, "vgs_max": vgs_max}

    if None in [vgs_min, vgs_max]:
        return ConsistencyCheck(
            rule_id="VGSTH_RANGE", rule_name="VGS(th) 范围",
            severity="medium", status="skipped",
            fields_involved=["vgs_th"],
            details=details,
            verdict="SKIPPED: missing VGS(th) min/max",
            suggested_action="none",
        )

    if vgs_min >= vgs_max:
        return ConsistencyCheck(
            rule_id="VGSTH_RANGE", rule_name="VGS(th) 范围",
            severity="high", status="fail",
            fields_involved=["vgs_th"],
            details=details,
            verdict=f"FAIL: VGS(th) min({vgs_min}V) >= max({vgs_max}V)",
            suggested_action="review",
        )

    if vgs_min < 1.0 or vgs_max > 7.0:
        return ConsistencyCheck(
            rule_id="VGSTH_RANGE", rule_name="VGS(th) 范围",
            severity="high", status="fail",
            fields_involved=["vgs_th"],
            details=details,
            verdict=f"FAIL: VGS(th)={vgs_min}-{vgs_max}V outside 1-7V range",
            suggested_action="review",
        )

    if vgs_max - vgs_min > 4.0:
        return ConsistencyCheck(
            rule_id="VGSTH_RANGE", rule_name="VGS(th) 范围",
            severity="medium", status="warning",
            fields_involved=["vgs_th"],
            details=details,
            verdict=f"WARNING: VGS(th) range={vgs_max-vgs_min:.1f}V unusually wide",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="VGSTH_RANGE", rule_name="VGS(th) 范围",
        severity="medium", status="pass",
        fields_involved=["vgs_th"],
        details=details,
        verdict=f"PASS: VGS(th)={vgs_min}-{vgs_max}V",
        suggested_action="none",
    )


def check_isolation_voltage(params: list) -> ConsistencyCheck:
    """Isolation voltage should be >= 0.5 * VDS rating."""
    isol = _get_field(params, "isol")
    vds = _get_field(params, "voltage_rating")

    isol_v = _typ(isol)
    vds_max = _max_v(vds)

    details = {"isol": isol_v, "vds_max": vds_max}

    if None in [isol_v, vds_max]:
        return ConsistencyCheck(
            rule_id="ISOLATION_VS_VOLTAGE_RATING", rule_name="隔离电压关系",
            severity="medium", status="skipped",
            fields_involved=["isol", "voltage_rating"],
            details=details,
            verdict="SKIPPED: missing isol or voltage_rating",
            suggested_action="none",
        )

    # Normalize to V (isol may be in kV)
    isol_v_in_V = isol_v * 1000.0 if isol_v < 100 else isol_v
    details["isol_in_V"] = isol_v_in_V
    details["ratio"] = round(isol_v_in_V / vds_max, 2)

    if isol_v_in_V < vds_max * 0.5:
        return ConsistencyCheck(
            rule_id="ISOLATION_VS_VOLTAGE_RATING", rule_name="隔离电压关系",
            severity="medium", status="warning",
            fields_involved=["isol", "voltage_rating"],
            details=details,
            verdict=f"WARNING: Visol({isol_v_in_V:.0f}V) < 0.5*VDS({vds_max:.0f}V)",
            suggested_action="warning",
        )

    return ConsistencyCheck(
        rule_id="ISOLATION_VS_VOLTAGE_RATING", rule_name="隔离电压关系",
        severity="medium", status="pass",
        fields_involved=["isol", "voltage_rating"],
        details=details,
        verdict=f"PASS: Visol({isol_v_in_V:.0f}V) >= 0.5*VDS({vds_max:.0f}V)",
        suggested_action="none",
    )


ALL_RULES = [
    check_rds_temperature_coefficient,
    check_gate_charge_hierarchy,
    check_capacitance_hierarchy,
    check_reverse_recovery_consistency,
    check_switching_energy,
    check_junction_temperature,
    check_vgsth_range,
    check_isolation_voltage,
]


def run(agent2_result: Agent2Result, artifact_paths: ArtifactPaths) -> Agent3Result:
    """
    Run Step 3: Agent 3 Cross-Parameter Consistency Check.

    Args:
        agent2_result: Agent2Result from Step 2
        artifact_paths: Artifact paths manager

    Returns:
        Agent3Result
    """
    logger.info(f"Step 3: Running Agent 3 consistency checks for {agent2_result.file_name}")

    params = agent2_result.final_params

    checks = []
    for rule_fn in ALL_RULES:
        check = rule_fn(params)
        checks.append(check)

    total = len(checks)
    passed = sum(1 for c in checks if c.status == "pass")
    failed = sum(1 for c in checks if c.status == "fail")
    skipped = sum(1 for c in checks if c.status == "skipped")
    warnings = sum(1 for c in checks if c.status == "warning")

    if failed > 0:
        overall = "inconsistent"
    elif warnings > 0:
        overall = "review_needed"
    else:
        overall = "consistent"

    recommendations = [
        f"[{c.severity.upper()}] {c.rule_name}: {c.verdict}"
        for c in checks
        if c.status in ("fail", "warning") and c.severity in ("critical", "high")
    ]

    result = Agent3Result(
        document_id=agent2_result.document_id,
        file_name=agent2_result.file_name,
        overall_status=overall,
        consistency_checks=checks,
        summary={
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warnings": warnings,
        },
        recommendations=recommendations,
    )

    save_agent3(result, artifact_paths.step3_consistency())
    logger.info(f"Step 3: {passed}/{total} passed, {warnings} warnings, {failed} failed")

    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python3 step3_agent_cross_check.py <agent2_json> <output_dir>")
        sys.exit(1)

    agent2_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    from artifacts import ArtifactPaths
    agent2 = load_agent2(agent2_path)
    pdf_stem = Path(agent2.file_name).stem
    ap = ArtifactPaths(output_dir, pdf_stem).ensure_dirs()

    result = run(agent2, ap)
    s = result.summary
    print(f"\nStep 3: {s['passed']}/{s['total_checks']} passed, "
          f"{s['warnings']} warnings, {s['failed']} failed, {s['skipped']} skipped")
    print(f"Result saved to: {ap.step3_consistency()}")
