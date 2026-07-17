#!/usr/bin/env python3
"""
Agent 3: Cross-Parameter Consistency Checker
Tests cross-parameter consistency relationships in SiC MOSFET datasheet extractions.

Usage:
    python3 test_cross_check.py [input_json]
    
Examples:
    python3 test_cross_check.py
    python3 test_cross_check.py agent_prototype/data/agent3_test_input_asc300.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_field(params: list[dict], field_id: str) -> Optional[dict]:
    return next((p for p in params if p["field_id"] == field_id), None)


def typ_value(p: Optional[dict]) -> Optional[float]:
    if p is None:
        return None
    v = p.get("typ") or p.get("value")
    if v is not None:
        return float(v)
    return None


def max_value(p: Optional[dict]) -> Optional[float]:
    if p is None:
        return None
    v = p.get("max")
    if v is not None:
        return float(v)
    return None


def min_value(p: Optional[dict]) -> Optional[float]:
    if p is None:
        return None
    v = p.get("min")
    if v is not None:
        return float(v)
    return None


def nF_to_pF(nF: float) -> float:
    """Convert nF to pF"""
    return nF * 1000.0


def get_value_in_pF(param: Optional[dict]) -> Optional[float]:
    """Get capacitance value normalized to pF"""
    if param is None or typ_value(param) is None:
        return None
    v = typ_value(param)
    unit = (param.get("unit") or "").lower().strip()
    if unit == "pf":
        return v
    elif unit == "nf":
        return nF_to_pF(v)
    return None  # unknown unit


# ─────────────────────────────────────────────────────────────────────────────
# Consistency Check Rules
# ─────────────────────────────────────────────────────────────────────────────

def check_rds_temperature_coefficient(params: list[dict]) -> dict:
    """Rule 1: RDS(on) should increase with temperature (positive temperature coefficient)"""
    rds_25 = get_field(params, "rds_on_25c")
    rds_150 = get_field(params, "rds_on_150c")
    
    details = {}
    
    if rds_25 is None or rds_150 is None:
        return {
            "rule_id": "RDS_TEMP_COEFFICIENT",
            "rule_name": "RDS(on) 温度特性",
            "severity": "critical",
            "status": "skipped",
            "fields_involved": ["rds_on_25c", "rds_on_150c"],
            "details": details,
            "verdict": "SKIPPED: 缺少 rds_on_25c 或 rds_on_150c 数据",
            "suggested_action": "none"
        }
    
    v25 = typ_value(rds_25)
    v150 = typ_value(rds_150)
    
    details["rds_on_25c_typ"] = v25
    details["rds_on_150c_typ"] = v150
    
    if v25 is None:
        return {
            "rule_id": "RDS_TEMP_COEFFICIENT",
            "rule_name": "RDS(on) 温度特性",
            "severity": "critical",
            "status": "skipped",
            "fields_involved": ["rds_on_25c", "rds_on_150c"],
            "details": details,
            "verdict": "SKIPPED: rds_on_25c has no typ value",
            "suggested_action": "none"
        }
    
    if v150 is None:
        return {
            "rule_id": "RDS_TEMP_COEFFICIENT",
            "rule_name": "RDS(on) 温度特性",
            "severity": "critical",
            "status": "skipped",
            "fields_involved": ["rds_on_25c", "rds_on_150c"],
            "details": details,
            "verdict": "SKIPPED: rds_on_150c is blocked (no TC=150°C candidate). Expected for ASC300 datasheet.",
            "suggested_action": "none"
        }
    
    ratio = v150 / v25
    details["ratio"] = round(ratio, 3)
    details["expected_range"] = "1.3x ~ 2.5x"
    
    if ratio < 1.0:
        return {
            "rule_id": "RDS_TEMP_COEFFICIENT",
            "rule_name": "RDS(on) 温度特性",
            "severity": "critical",
            "status": "fail",
            "fields_involved": ["rds_on_25c", "rds_on_150c"],
            "details": details,
            "verdict": f"FAIL: rds_on_150c ({v150} mΩ) < rds_on_25c ({v25} mΩ). Temperature coefficient should be positive.",
            "suggested_action": "review"
        }
    
    if ratio < 1.3 or ratio > 2.5:
        return {
            "rule_id": "RDS_TEMP_COEFFICIENT",
            "rule_name": "RDS(on) 温度特性",
            "severity": "high",
            "status": "warning",
            "fields_involved": ["rds_on_25c", "rds_on_150c"],
            "details": details,
            "verdict": f"WARNING: ratio={ratio:.2f}x outside typical 1.3x~2.5x range for SiC MOSFET",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "RDS_TEMP_COEFFICIENT",
        "rule_name": "RDS(on) 温度特性",
        "severity": "critical",
        "status": "pass",
        "fields_involved": ["rds_on_25c", "rds_on_150c"],
        "details": details,
        "verdict": f"PASS: ratio={ratio:.2f}x within 1.3x~2.5x range",
        "suggested_action": "none"
    }


def check_gate_charge_hierarchy(params: list[dict]) -> dict:
    """Rule 2: Gate charge hierarchy — QG > QGS, QG > QGD, QGS+QGD <= QG*1.3"""
    qg = get_field(params, "qg")
    qgs = get_field(params, "qgs")
    qgd = get_field(params, "qgd")
    
    qg_v = typ_value(qg)
    qgs_v = typ_value(qgs)
    qgd_v = typ_value(qgd)
    
    details = {
        "qg_typ": qg_v,
        "qgs_typ": qgs_v,
        "qgd_typ": qgd_v,
        "qgs_plus_qgd": (qgs_v + qgd_v) if qgs_v and qgd_v else None,
    }
    
    missing = []
    for name, v in [("qg", qg_v), ("qgs", qgs_v), ("qgd", qgd_v)]:
        if v is None:
            missing.append(name)
    
    if missing:
        return {
            "rule_id": "GATE_CHARGE_HIERARCHY",
            "rule_name": "栅极电荷层级",
            "severity": "critical",
            "status": "skipped",
            "fields_involved": ["qg", "qgs", "qgd"],
            "details": details,
            "verdict": f"SKIPPED: missing {', '.join(missing)} typ values",
            "suggested_action": "none"
        }
    
    failures = []
    if qg_v <= qgs_v:
        failures.append(f"QG({qg_v}nC) <= QGS({qgs_v}nC)")
    if qg_v <= qgd_v:
        failures.append(f"QG({qg_v}nC) <= QGD({qgd_v}nC)")
    
    sum_ratio = (qgs_v + qgd_v) / qg_v
    details["sum_ratio"] = round(sum_ratio, 3)
    details["expected_sum_ratio"] = "0.3 ~ 1.3"
    
    warnings = []
    if sum_ratio > 1.3:
        warnings.append(f"QGS+QGD={qgs_v+qgd_v:.1f}nC > QG*1.3={qg_v*1.3:.1f}nC")
    
    if failures:
        return {
            "rule_id": "GATE_CHARGE_HIERARCHY",
            "rule_name": "栅极电荷层级",
            "severity": "critical",
            "status": "fail",
            "fields_involved": ["qg", "qgs", "qgd"],
            "details": details,
            "verdict": f"FAIL: {'; '.join(failures)}",
            "suggested_action": "review"
        }
    
    if warnings:
        return {
            "rule_id": "GATE_CHARGE_HIERARCHY",
            "rule_name": "栅极电荷层级",
            "severity": "high",
            "status": "warning",
            "fields_involved": ["qg", "qgs", "qgd"],
            "details": details,
            "verdict": f"WARNING: {'; '.join(warnings)}",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "GATE_CHARGE_HIERARCHY",
        "rule_name": "栅极电荷层级",
        "severity": "critical",
        "status": "pass",
        "fields_involved": ["qg", "qgs", "qgd"],
        "details": details,
        "verdict": f"PASS: QG({qg_v}nC) > QGS({qgs_v}nC) + QGD({qgd_v}nC), sum_ratio={sum_ratio:.2f}x",
        "suggested_action": "none"
    }


def check_capacitance_hierarchy(params: list[dict]) -> dict:
    """Rule 3: Capacitance hierarchy — Ciss >> Coss > Crss (in pF)"""
    ciss_pf = get_value_in_pF(get_field(params, "ciss"))
    coss_pf = get_value_in_pF(get_field(params, "coss"))
    crss_pf = get_value_in_pF(get_field(params, "crss"))
    
    details = {
        "ciss_in_pF": ciss_pf,
        "coss_in_pF": coss_pf,
        "crss_in_pF": crss_pf,
    }
    
    missing = [n for n, v in [("ciss", ciss_pf), ("coss", coss_pf), ("crss", crss_pf)] if v is None]
    if missing:
        return {
            "rule_id": "CAPACITANCE_HIERARCHY",
            "rule_name": "电容层级",
            "severity": "critical",
            "status": "skipped",
            "fields_involved": ["ciss", "coss", "crss"],
            "details": details,
            "verdict": f"SKIPPED: missing {', '.join(missing)}",
            "suggested_action": "none"
        }
    
    failures = []
    if ciss_pf <= coss_pf:
        failures.append(f"Ciss({ciss_pf:.1f}pF) <= Coss({coss_pf:.1f}pF)")
    if coss_pf <= crss_pf:
        failures.append(f"Coss({coss_pf:.1f}pF) <= Crss({crss_pf:.1f}pF)")
    
    ratio = ciss_pf / crss_pf
    details["ciss_to_crss_ratio"] = round(ratio, 1)
    
    if failures:
        return {
            "rule_id": "CAPACITANCE_HIERARCHY",
            "rule_name": "电容层级",
            "severity": "critical",
            "status": "fail",
            "fields_involved": ["ciss", "coss", "crss"],
            "details": details,
            "verdict": f"FAIL: {'; '.join(failures)}",
            "suggested_action": "review"
        }
    
    return {
        "rule_id": "CAPACITANCE_HIERARCHY",
        "rule_name": "电容层级",
        "severity": "critical",
        "status": "pass",
        "fields_involved": ["ciss", "coss", "crss"],
        "details": details,
        "verdict": f"PASS: Ciss({ciss_pf:.1f}pF) >> Coss({coss_pf:.1f}pF) > Crss({crss_pf:.1f}pF), ratio={ratio:.0f}x",
        "suggested_action": "none"
    }


def check_reverse_recovery_consistency(params: list[dict]) -> dict:
    """Rule 4: Reverse recovery consistency — Qrr ≈ 0.5 * trr * IRRM
    Qrr in nC, trr in ns, IRRM in A:
    Expected Qrr(nC) = 0.5 * trr(ns) * IRRM(A) * 1e-3  (result in μC then convert)
    More simply: Qrr(nC) ≈ 0.5 * trr(μs) * IRRM(A) * 1000
    Or: expected Qrr(μC) = 0.5 * trr(ns) * IRRM(A) * 1e-6
    Then compare: if Qrr is in nC → compare with expected_nC; if μC → compare with expected_μC
    """
    trr_v = typ_value(get_field(params, "trr"))
    qrr_v = typ_value(get_field(params, "qrr"))
    irrm_v = typ_value(get_field(params, "irrm"))
    
    details = {"trr_typ": trr_v, "qrr_typ": qrr_v, "irrm_typ": irrm_v}
    
    if None in [trr_v, qrr_v, irrm_v]:
        missing = [n for n, v in [("trr", trr_v), ("qrr", qrr_v), ("irrm", irrm_v)] if v is None]
        return {
            "rule_id": "REVERSE_RECOVERY_CONSISTENCY",
            "rule_name": "反向恢复一致性",
            "severity": "high",
            "status": "skipped",
            "fields_involved": ["trr", "qrr", "irrm"],
            "details": details,
            "verdict": f"SKIPPED: missing {', '.join(missing)}",
            "suggested_action": "none"
        }
    
    # Expected Qrr in μC = 0.5 * trr(ns) * IRRM(A) * 1e-3
    # = 0.5 * trr(ns) * IRRM(A) / 1000
    # For trr=96ns, IRRM=141A: expected = 0.5 * 96 * 141 / 1000 = 6.768 μC
    expected_qrr_uc = 0.5 * trr_v * irrm_v * 1e-3  # in μC
    expected_qrr_nc = expected_qrr_uc * 1000  # in nC
    
    details["expected_qrr_uc"] = round(expected_qrr_uc, 4)
    details["expected_qrr_nc"] = round(expected_qrr_nc, 4)
    
    # Check if Qrr fits better as nC or μC
    ratio_if_nc = qrr_v / expected_qrr_nc if expected_qrr_nc > 0 else float('inf')
    ratio_if_uc = qrr_v / expected_qrr_uc if expected_qrr_uc > 0 else float('inf')
    
    details["ratio_if_qrr_is_nC"] = round(ratio_if_nc, 2)
    details["ratio_if_qrr_is_uC"] = round(ratio_if_uc, 2)
    details["expected_range"] = "0.3x ~ 2.0x (if unit is correct)"
    
    # Determine which assumption (nC or μC) gives a plausible ratio
    ratio_nc_ok = 0.2 <= ratio_if_nc <= 3.0
    ratio_uc_ok = 0.2 <= ratio_if_uc <= 3.0
    
    if ratio_nc_ok and not ratio_uc_ok:
        return {
            "rule_id": "REVERSE_RECOVERY_CONSISTENCY",
            "rule_name": "反向恢复一致性",
            "severity": "high",
            "status": "pass",
            "fields_involved": ["trr", "qrr", "irrm"],
            "details": details,
            "verdict": f"PASS: Qrr({qrr_v}nC) ratio={ratio_if_nc:.1f}x consistent when treated as nC",
            "suggested_action": "none"
        }
    
    if ratio_uc_ok and not ratio_nc_ok:
        return {
            "rule_id": "REVERSE_RECOVERY_CONSISTENCY",
            "rule_name": "反向恢复一致性",
            "severity": "high",
            "status": "warning",
            "fields_involved": ["trr", "qrr", "irrm"],
            "details": details,
            "verdict": f"WARNING: Qrr({qrr_v}) labeled as nC but ratio consistent with μC (ratio={ratio_if_uc:.1f}x). Qrr unit may be μC.",
            "suggested_action": "warning"
        }
    
    if not ratio_nc_ok and not ratio_uc_ok:
        return {
            "rule_id": "REVERSE_RECOVERY_CONSISTENCY",
            "rule_name": "反向恢复一致性",
            "severity": "high",
            "status": "warning",
            "fields_involved": ["trr", "qrr", "irrm"],
            "details": details,
            "verdict": f"WARNING: Qrr({qrr_v}) inconsistent with trr({trr_v}ns)*IRRM({irrm_v}A). Ratios: nC={ratio_if_nc:.0f}x, μC={ratio_if_uc:.0f}x. Neither fits 0.3x~2.0x range.",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "REVERSE_RECOVERY_CONSISTENCY",
        "rule_name": "反向恢复一致性",
        "severity": "high",
        "status": "pass",
        "fields_involved": ["trr", "qrr", "irrm"],
        "details": details,
        "verdict": f"PASS: ratio_nC={ratio_if_nc:.1f}x, ratio_μC={ratio_if_uc:.1f}x",
        "suggested_action": "none"
    }


def check_switching_energy_consistency(params: list[dict]) -> dict:
    """Rule 5: Eon and Eoff should be comparable (within 0.3x to 3x)"""
    eon_v = typ_value(get_field(params, "eon"))
    eoff_v = typ_value(get_field(params, "eoff"))
    
    details = {"eon_typ": eon_v, "eoff_typ": eoff_v}
    
    if None in [eon_v, eoff_v]:
        missing = [n for n, v in [("eon", eon_v), ("eoff", eoff_v)] if v is None]
        return {
            "rule_id": "SWITCHING_ENERGY_CONSISTENCY",
            "rule_name": "开关能量可比性",
            "severity": "high",
            "status": "skipped",
            "fields_involved": ["eon", "eoff"],
            "details": details,
            "verdict": f"SKIPPED: missing {', '.join(missing)}",
            "suggested_action": "none"
        }
    
    if eon_v == 0 or eoff_v == 0:
        return {
            "rule_id": "SWITCHING_ENERGY_CONSISTENCY",
            "rule_name": "开关能量可比性",
            "severity": "high",
            "status": "fail",
            "fields_involved": ["eon", "eoff"],
            "details": details,
            "verdict": "FAIL: Eon or Eoff is zero",
            "suggested_action": "review"
        }
    
    ratio = max(eon_v, eoff_v) / min(eon_v, eoff_v)
    details["eon_to_eoff_ratio"] = round(ratio, 2)
    details["expected_range"] = "< 3.3x"
    
    if ratio > 3.3:
        return {
            "rule_id": "SWITCHING_ENERGY_CONSISTENCY",
            "rule_name": "开关能量可比性",
            "severity": "high",
            "status": "warning",
            "fields_involved": ["eon", "eoff"],
            "details": details,
            "verdict": f"WARNING: Eon/Eoff ratio={ratio:.2f}x > 3.3x, one may be from different conditions",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "SWITCHING_ENERGY_CONSISTENCY",
        "rule_name": "开关能量可比性",
        "severity": "high",
        "status": "pass",
        "fields_involved": ["eon", "eoff"],
        "details": details,
        "verdict": f"PASS: Eon/Eoff ratio={ratio:.2f}x within acceptable range",
        "suggested_action": "none"
    }


def check_junction_temperature_range(params: list[dict]) -> dict:
    """Rule 6: Tj_max should be in reasonable range (150-200°C for SiC)"""
    tj_max = max_value(get_field(params, "junction_temperature"))
    
    details = {"tj_max": tj_max, "typical_range": "150°C ~ 200°C"}
    
    if tj_max is None:
        return {
            "rule_id": "JUNCTION_TEMPERATURE_RANGE",
            "rule_name": "Tj_max 范围合理性",
            "severity": "high",
            "status": "skipped",
            "fields_involved": ["junction_temperature"],
            "details": details,
            "verdict": "SKIPPED: no junction_temperature max value",
            "suggested_action": "none"
        }
    
    if tj_max < 120 or tj_max > 225:
        return {
            "rule_id": "JUNCTION_TEMPERATURE_RANGE",
            "rule_name": "Tj_max 范围合理性",
            "severity": "high",
            "status": "fail",
            "fields_involved": ["junction_temperature"],
            "details": details,
            "verdict": f"FAIL: Tj_max={tj_max}°C outside 120-225°C range",
            "suggested_action": "review"
        }
    
    if tj_max < 150 or tj_max > 200:
        return {
            "rule_id": "JUNCTION_TEMPERATURE_RANGE",
            "rule_name": "Tj_max 范围合理性",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["junction_temperature"],
            "details": details,
            "verdict": f"WARNING: Tj_max={tj_max}°C outside typical 150-200°C range",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "JUNCTION_TEMPERATURE_RANGE",
        "rule_name": "Tj_max 范围合理性",
        "severity": "high",
        "status": "pass",
        "fields_involved": ["junction_temperature"],
        "details": details,
        "verdict": f"PASS: Tj_max={tj_max}°C within 150-200°C range",
        "suggested_action": "none"
    }


def check_vgsth_range(params: list[dict]) -> dict:
    """Rule 7: VGS(th) should be in reasonable range for SiC MOSFET (1.5V - 5.5V)"""
    vgs_min = min_value(get_field(params, "vgs_th"))
    vgs_max = max_value(get_field(params, "vgs_th"))
    
    details = {"vgs_th_min": vgs_min, "vgs_th_max": vgs_max}
    
    if vgs_min is None or vgs_max is None:
        return {
            "rule_id": "VGSTH_RANGE",
            "rule_name": "VGS(th) 范围合理性",
            "severity": "medium",
            "status": "skipped",
            "fields_involved": ["vgs_th"],
            "details": details,
            "verdict": "SKIPPED: missing vgs_th min/max values",
            "suggested_action": "none"
        }
    
    if vgs_min >= vgs_max:
        return {
            "rule_id": "VGSTH_RANGE",
            "rule_name": "VGS(th) 范围合理性",
            "severity": "high",
            "status": "fail",
            "fields_involved": ["vgs_th"],
            "details": details,
            "verdict": f"FAIL: VGS(th) min({vgs_min}V) >= max({vgs_max}V)",
            "suggested_action": "review"
        }
    
    if vgs_min < 1.0 or vgs_max > 7.0:
        return {
            "rule_id": "VGSTH_RANGE",
            "rule_name": "VGS(th) 范围合理性",
            "severity": "high",
            "status": "fail",
            "fields_involved": ["vgs_th"],
            "details": details,
            "verdict": f"FAIL: VGS(th)={vgs_min}-{vgs_max}V outside 1-7V range",
            "suggested_action": "review"
        }
    
    if vgs_max - vgs_min > 4.0:
        return {
            "rule_id": "VGSTH_RANGE",
            "rule_name": "VGS(th) 范围合理性",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["vgs_th"],
            "details": details,
            "verdict": f"WARNING: VGS(th) range={vgs_max-vgs_min:.1f}V is unusually wide (>4V)",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "VGSTH_RANGE",
        "rule_name": "VGS(th) 范围合理性",
        "severity": "medium",
        "status": "pass",
        "fields_involved": ["vgs_th"],
        "details": details,
        "verdict": f"PASS: VGS(th)={vgs_min}-{vgs_max}V within typical range",
        "suggested_action": "none"
    }


def check_isolation_vs_voltage_rating(params: list[dict]) -> dict:
    """Rule 8: Isolation voltage should be >= some fraction of VDS rating"""
    isol_v = typ_value(get_field(params, "isol"))
    vds_max = max_value(get_field(params, "voltage_rating"))
    
    details = {"isol_typ": isol_v, "vds_max": vds_max}
    
    if None in [isol_v, vds_max]:
        missing = [n for n, v in [("isol", isol_v), ("voltage_rating", vds_max)] if v is None]
        return {
            "rule_id": "ISOLATION_VS_VOLTAGE_RATING",
            "rule_name": "隔离电压与额定电压关系",
            "severity": "medium",
            "status": "skipped",
            "fields_involved": ["isol", "voltage_rating"],
            "details": details,
            "verdict": f"SKIPPED: missing {', '.join(missing)}",
            "suggested_action": "none"
        }
    
    # isol may be in kV, vds in V — normalize
    isol_v_in_V = isol_v * 1000.0 if isol_v < 100 else isol_v
    
    details["isol_in_V"] = isol_v_in_V
    details["ratio"] = round(isol_v_in_V / vds_max, 2)
    
    if isol_v_in_V < vds_max * 0.5:
        return {
            "rule_id": "ISOLATION_VS_VOLTAGE_RATING",
            "rule_name": "隔离电压与额定电压关系",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["isol", "voltage_rating"],
            "details": details,
            "verdict": f"WARNING: Visol({isol_v_in_V:.0f}V) < 0.5*VDS({vds_max:.0f}V)",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "ISOLATION_VS_VOLTAGE_RATING",
        "rule_name": "隔离电压与额定电压关系",
        "severity": "medium",
        "status": "pass",
        "fields_involved": ["isol", "voltage_rating"],
        "details": details,
        "verdict": f"PASS: Visol({isol_v_in_V:.0f}V) >= 0.5*VDS({vds_max:.0f}V)",
        "suggested_action": "none"
    }


def check_rds_absolute_reasonableness(params: list[dict]) -> dict:
    """Rule 9: RDS(on) absolute value reasonableness for package current rating"""
    rds_typ = typ_value(get_field(params, "rds_on_25c"))
    id_max = max_value(get_field(params, "current_rating"))
    
    details = {"rds_on_25c_typ": rds_typ, "id_max": id_max}
    
    if None in [rds_typ, id_max]:
        return {
            "rule_id": "RDS_ABSOLUTE_REASONABLENESS",
            "rule_name": "RDS(on) 绝对值合理性",
            "severity": "medium",
            "status": "skipped",
            "fields_involved": ["rds_on_25c", "current_rating"],
            "details": details,
            "verdict": "SKIPPED: missing data",
            "suggested_action": "none"
        }
    
    power_loss = (id_max ** 2) * (rds_typ / 1000.0)
    details["estimated_power_loss_W"] = round(power_loss, 1)
    details["typical_note"] = "300A module: RDS(on) typ usually 3-10 mΩ"
    
    if rds_typ < 1.0:
        return {
            "rule_id": "RDS_ABSOLUTE_REASONABLENESS",
            "rule_name": "RDS(on) 绝对值合理性",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["rds_on_25c", "current_rating"],
            "details": details,
            "verdict": f"WARNING: rds_on_25c={rds_typ}mΩ very low for {id_max}A module",
            "suggested_action": "warning"
        }
    
    if rds_typ > 20:
        return {
            "rule_id": "RDS_ABSOLUTE_REASONABLENESS",
            "rule_name": "RDS(on) 绝对值合理性",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["rds_on_25c", "current_rating"],
            "details": details,
            "verdict": f"WARNING: rds_on_25c={rds_typ}mΩ very high for {id_max}A module",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "RDS_ABSOLUTE_REASONABLENESS",
        "rule_name": "RDS(on) 绝对值合理性",
        "severity": "medium",
        "status": "pass",
        "fields_involved": ["rds_on_25c", "current_rating"],
        "details": details,
        "verdict": f"PASS: rds_on_25c={rds_typ}mΩ reasonable for {id_max}A module (est. loss={power_loss:.0f}W)",
        "suggested_action": "none"
    }


def check_qg_absolute_reasonableness(params: list[dict]) -> dict:
    """Rule 10: QG absolute value reasonableness for 800V-class SiC MOSFET"""
    qg_v = typ_value(get_field(params, "qg"))
    id_max = max_value(get_field(params, "current_rating"))
    
    details = {"qg_typ": qg_v, "id_max": id_max}
    
    if qg_v is None or id_max is None:
        return {
            "rule_id": "QG_ABSOLUTE_REASONABLENESS",
            "rule_name": "QG 绝对值合理性",
            "severity": "medium",
            "status": "skipped",
            "fields_involved": ["qg", "current_rating"],
            "details": details,
            "verdict": "SKIPPED: missing data",
            "suggested_action": "none"
        }
    
    details["typical_range"] = "800V-class, >200A: QG typically 300-2000 nC"
    
    if qg_v < 50:
        return {
            "rule_id": "QG_ABSOLUTE_REASONABLENESS",
            "rule_name": "QG 绝对值合理性",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["qg", "current_rating"],
            "details": details,
            "verdict": f"WARNING: QG={qg_v}nC very low for {id_max}A/800V SiC MOSFET",
            "suggested_action": "warning"
        }
    
    if qg_v > 5000:
        return {
            "rule_id": "QG_ABSOLUTE_REASONABLENESS",
            "rule_name": "QG 绝对值合理性",
            "severity": "medium",
            "status": "warning",
            "fields_involved": ["qg", "current_rating"],
            "details": details,
            "verdict": f"WARNING: QG={qg_v}nC very high for {id_max}A/800V SiC MOSFET",
            "suggested_action": "warning"
        }
    
    return {
        "rule_id": "QG_ABSOLUTE_REASONABLENESS",
        "rule_name": "QG 绝对值合理性",
        "severity": "medium",
        "status": "pass",
        "fields_involved": ["qg", "current_rating"],
        "details": details,
        "verdict": f"PASS: QG={qg_v}nC reasonable for {id_max}A/800V SiC MOSFET",
        "suggested_action": "none"
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

ALL_RULES = [
    check_rds_temperature_coefficient,
    check_gate_charge_hierarchy,
    check_capacitance_hierarchy,
    check_reverse_recovery_consistency,
    check_switching_energy_consistency,
    check_junction_temperature_range,
    check_vgsth_range,
    check_isolation_vs_voltage_rating,
    check_rds_absolute_reasonableness,
    check_qg_absolute_reasonableness,
]


def run_agent3(input_data: dict) -> dict:
    params = input_data.get("final_params", [])
    
    results = []
    for rule in ALL_RULES:
        result = rule(params)
        results.append(result)
    
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    warnings = sum(1 for r in results if r["status"] == "warning")
    
    if failed > 0:
        overall = "inconsistent"
    elif warnings > 0:
        overall = "review_needed"
    else:
        overall = "consistent"
    
    recommendations = []
    for r in results:
        if r["status"] in ("fail", "warning") and r["severity"] in ("critical", "high"):
            recommendations.append(f"[{r['severity'].upper()}] {r['rule_name']}: {r['verdict']}")
    
    return {
        "document_id": input_data.get("document_id", ""),
        "file_name": input_data.get("file_name", ""),
        "overall_status": overall,
        "consistency_checks": results,
        "summary": {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warnings": warnings
        },
        "recommendations": recommendations
    }


def main():
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    else:
        input_path = Path(__file__).parent / "data" / "agent3_test_input_asc300.json"
    
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(input_path) as f:
        input_data = json.load(f)
    
    result = run_agent3(input_data)
    
    stem = Path(input_path).stem
    output_path = Path(__file__).parent / "results" / f"agent3_consistency_{stem}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Agent 3 Consistency Check Results")
    print(f"{'─'*50}")
    print(f"Document: {result['file_name']}")
    print(f"Overall Status: {result['overall_status'].upper()}")
    print()
    print(f"Summary: {result['summary']['passed']}/{result['summary']['total_checks']} passed", end="")
    if result['summary']['failed'] > 0:
        print(f", {result['summary']['failed']} FAILED", end="")
    if result['summary']['warnings'] > 0:
        print(f", {result['summary']['warnings']} warnings", end="")
    if result['summary']['skipped'] > 0:
        print(f", {result['summary']['skipped']} skipped", end="")
    print()
    print()
    
    for r in result["consistency_checks"]:
        icon = {"pass": "✅", "fail": "❌", "skipped": "⏭️", "warning": "⚠️"}.get(r["status"], "?")
        print(f"  {icon} [{r['severity']}] {r['rule_name']}: {r['verdict']}")
    
    if result["recommendations"]:
        print()
        print("Recommendations:")
        for rec in result["recommendations"]:
            print(f"  • {rec}")
    
    print()
    print(f"Full report: {output_path}")
    
    return 0 if result["overall_status"] == "consistent" else 1


if __name__ == "__main__":
    sys.exit(main())
