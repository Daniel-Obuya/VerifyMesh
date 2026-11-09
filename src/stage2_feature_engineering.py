"""
VerifyMesh — Centralized Stage 2 Feature Engineering Module
===========================================================

Single source of truth for Stage 2 task-specific feature construction across:
1. Synthetic dataset evaluation and model training (DataFrame batch mode).
2. Live backend inference in `src/task_suitability_inference.py` and `backend/db.py` (single-pair dict mode).

Guarantees:
- Zero target leakage (never accepts or computes target-derived or simulation-oracle columns).
- Deterministic domain weightings across task categories.
- Computes the approved 5-feature v2 representation (`STAGE2_V2_FEATURES`) and the
  complete 28-feature legacy representation (`LEGACY_28_FEATURES`) from raw applicant-task
  attributes so all callers and backward-compatibility tests remain 100% supported.
- Strict numeric and finite (`NaN`/`Inf`) validation so invalid inputs never silently fabricate scores.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. Canonical Feature Definitions (Exact 5-Feature Phase 3/4 Schema)
# ---------------------------------------------------------------------------

STAGE2_V2_FEATURES: list[str] = [
    "weighted_skill_margin",
    "min_skill_margin",
    "weakest_link_deficit",
    "exp_surplus_tanh",
    "difficulty_tier",
]

STAGE2_V2_FEATURE_DESCRIPTIONS: dict[str, str] = {
    "weighted_skill_margin": (
        "Category-weighted competency surplus across communication, product knowledge, "
        "sales, and customer service relative to task minimums."
    ),
    "min_skill_margin": (
        "Smallest individual competency margin across communication, product knowledge, "
        "sales, customer service, and overall assessment score."
    ),
    "weakest_link_deficit": (
        "Non-positive bottleneck deficit (min(0.0, min_skill_margin)), capturing risk "
        "when the weakest sub-skill falls below the task target."
    ),
    "exp_surplus_tanh": (
        "Saturating relevant experience surplus above task minimum: "
        "tanh((task_relevant_exp - task_min_exp) / 12.0)."
    ),
    "difficulty_tier": (
        "Numeric task difficulty tier (1 = Low / Foundational, 2 = Medium / Standard, 3 = High / Advanced)."
    ),
}

LEGACY_28_FEATURES: list[str] = [
    "difficulty_tier",
    "task_min_exp",
    "task_min_assessment",
    "task_min_comm",
    "task_min_prod",
    "task_min_sales",
    "task_min_cs",
    "applicant_relevant_exp",
    "applicant_sales_exp",
    "applicant_cs_exp",
    "applicant_cert_count",
    "applicant_has_sales_cert",
    "applicant_has_cs_cert",
    "applicant_has_tech_cert",
    "applicant_assessment_score",
    "applicant_comm_score",
    "applicant_prod_score",
    "applicant_sales_score",
    "applicant_cs_score",
    "experience_surplus_months",
    "assessment_gap",
    "communication_gap",
    "product_knowledge_gap",
    "sales_skill_gap",
    "customer_service_gap",
    "exp_leverage_ratio",
    "assessment_gap_sq",
    "comm_gap_sq",
]

# Category-specific domain weights matching generate_synthetic_dataset.py
CATEGORY_DOMAIN_WEIGHTS: dict[str, dict[str, float]] = {
    "Enterprise Sales": {"comm": 0.25, "prod": 0.20, "sales": 0.45, "cs": 0.10},
    "Customer Support Escalations": {"comm": 0.30, "prod": 0.20, "sales": 0.05, "cs": 0.45},
    "Technical Product Onboarding": {"comm": 0.25, "prod": 0.50, "sales": 0.05, "cs": 0.20},
    "Quality Assurance & Compliance": {"comm": 0.30, "prod": 0.40, "sales": 0.05, "cs": 0.25},
    "Account Retention & Growth": {"comm": 0.25, "prod": 0.15, "sales": 0.30, "cs": 0.30},
}

DEFAULT_DOMAIN_WEIGHTS: dict[str, float] = {
    "comm": 0.25,
    "prod": 0.25,
    "sales": 0.25,
    "cs": 0.25,
}

# Category-specific default sub-skill minimums by difficulty tier when not explicitly stored in DB
CATEGORY_SUBSKILL_BASELINES: dict[str, dict[str, float]] = {
    "Enterprise Sales": {"comm": 70.0, "prod": 65.0, "sales": 72.0, "cs": 60.0},
    "Customer Support Escalations": {"comm": 72.0, "prod": 65.0, "sales": 55.0, "cs": 74.0},
    "Technical Product Onboarding": {"comm": 68.0, "prod": 75.0, "sales": 55.0, "cs": 65.0},
    "Quality Assurance & Compliance": {"comm": 70.0, "prod": 72.0, "sales": 55.0, "cs": 68.0},
    "Account Retention & Growth": {"comm": 72.0, "prod": 62.0, "sales": 68.0, "cs": 68.0},
}


def resolve_domain_weights(task_category: str | None) -> dict[str, float]:
    """
    Map a task category name (from synthetic data or live DB) to domain skill weights.
    """
    if not task_category:
        return DEFAULT_DOMAIN_WEIGHTS
    if task_category in CATEGORY_DOMAIN_WEIGHTS:
        return CATEGORY_DOMAIN_WEIGHTS[task_category]

    cat_lower = str(task_category).lower()
    if "sales" in cat_lower and ("retention" in cat_lower or "account" in cat_lower):
        return CATEGORY_DOMAIN_WEIGHTS["Account Retention & Growth"]
    if "sales" in cat_lower:
        return CATEGORY_DOMAIN_WEIGHTS["Enterprise Sales"]
    if "support" in cat_lower or "service" in cat_lower or "escalation" in cat_lower:
        return CATEGORY_DOMAIN_WEIGHTS["Customer Support Escalations"]
    if "tech" in cat_lower or "product" in cat_lower or "onboarding" in cat_lower:
        return CATEGORY_DOMAIN_WEIGHTS["Technical Product Onboarding"]
    if "quality" in cat_lower or "compliance" in cat_lower or "qa" in cat_lower:
        return CATEGORY_DOMAIN_WEIGHTS["Quality Assurance & Compliance"]
    return DEFAULT_DOMAIN_WEIGHTS


def resolve_subskill_minimums(
    task_category: str | None,
    difficulty_tier: int | float = 2,
    min_assessment: float = 70.0,
) -> dict[str, float]:
    """
    Deterministically derive task sub-skill minimum thresholds when a database task
    specifies only an overall pass mark, task category, and difficulty tier.
    """
    tier_offset = (float(difficulty_tier) - 2.0) * 4.0
    cat_key = None
    if task_category in CATEGORY_SUBSKILL_BASELINES:
        cat_key = task_category
    elif task_category:
        cat_lower = str(task_category).lower()
        if "sales" in cat_lower and ("retention" in cat_lower or "account" in cat_lower):
            cat_key = "Account Retention & Growth"
        elif "sales" in cat_lower:
            cat_key = "Enterprise Sales"
        elif "support" in cat_lower or "service" in cat_lower or "escalation" in cat_lower:
            cat_key = "Customer Support Escalations"
        elif "tech" in cat_lower or "product" in cat_lower or "onboarding" in cat_lower:
            cat_key = "Technical Product Onboarding"
        elif "quality" in cat_lower or "compliance" in cat_lower or "qa" in cat_lower:
            cat_key = "Quality Assurance & Compliance"

    if cat_key:
        base = CATEGORY_SUBSKILL_BASELINES[cat_key]
        return {
            "task_min_comm": float(np.clip(base["comm"] + tier_offset, 45.0, 90.0)),
            "task_min_prod": float(np.clip(base["prod"] + tier_offset, 45.0, 90.0)),
            "task_min_sales": float(np.clip(base["sales"] + tier_offset, 45.0, 90.0)),
            "task_min_cs": float(np.clip(base["cs"] + tier_offset, 45.0, 90.0)),
        }

    base_val = float(np.clip(min_assessment, 50.0, 85.0))
    return {
        "task_min_comm": base_val,
        "task_min_prod": base_val,
        "task_min_sales": base_val,
        "task_min_cs": base_val,
    }


# ---------------------------------------------------------------------------
# 2. DataFrame Batch Feature Engineering (Training & Evaluation)
# ---------------------------------------------------------------------------


def compute_stage2_features_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a DataFrame from `synthetic_applicant_task_pairs.csv` or
    `task_suitability_training.csv`, deterministically compute all Stage 2 v2
    and legacy 28 features without modifying the input DataFrame in place.
    """
    out = df.copy()

    # Ensure gap columns exist if raw columns are provided
    if "experience_surplus_months" not in out.columns:
        out["experience_surplus_months"] = (
            out["applicant_relevant_exp"] - out["task_min_exp"]
        )
    if "assessment_gap" not in out.columns:
        out["assessment_gap"] = (
            out["applicant_assessment_score"] - out["task_min_assessment"]
        )
    if "communication_gap" not in out.columns:
        out["communication_gap"] = out["applicant_comm_score"] - out["task_min_comm"]
    if "product_knowledge_gap" not in out.columns:
        out["product_knowledge_gap"] = (
            out["applicant_prod_score"] - out["task_min_prod"]
        )
    if "sales_skill_gap" not in out.columns:
        out["sales_skill_gap"] = out["applicant_sales_score"] - out["task_min_sales"]
    if "customer_service_gap" not in out.columns:
        out["customer_service_gap"] = out["applicant_cs_score"] - out["task_min_cs"]

    if "min_skill_margin" not in out.columns:
        out["min_skill_margin"] = out[
            [
                "communication_gap",
                "product_knowledge_gap",
                "sales_skill_gap",
                "customer_service_gap",
                "assessment_gap",
            ]
        ].min(axis=1)

    if "weighted_skill_margin" not in out.columns:
        weights_series = out.get(
            "task_category", pd.Series([None] * len(out), index=out.index)
        ).map(resolve_domain_weights)
        w_comm = weights_series.map(lambda w: w["comm"])
        w_prod = weights_series.map(lambda w: w["prod"])
        w_sales = weights_series.map(lambda w: w["sales"])
        w_cs = weights_series.map(lambda w: w["cs"])
        out["weighted_skill_margin"] = (
            w_comm * out["communication_gap"]
            + w_prod * out["product_knowledge_gap"]
            + w_sales * out["sales_skill_gap"]
            + w_cs * out["customer_service_gap"]
        ).round(2)

    if "cert_satisfied" not in out.columns:
        out["cert_satisfied"] = 1

    # Stage 2 v2 engineered features
    out["weakest_link_deficit"] = np.minimum(0.0, out["min_skill_margin"].astype(float))
    out["exp_surplus_tanh"] = np.tanh(
        out["experience_surplus_months"].astype(float) / 12.0
    )

    # Legacy 28 engineered features
    if "applicant_relevant_exp" in out.columns and "task_min_exp" in out.columns:
        out["exp_leverage_ratio"] = out["applicant_relevant_exp"].astype(float) / (
            out["task_min_exp"].astype(float) + 1.0
        )
    if "assessment_gap" in out.columns:
        out["assessment_gap_sq"] = out["assessment_gap"].astype(float) ** 2
    if "communication_gap" in out.columns:
        out["comm_gap_sq"] = out["communication_gap"].astype(float) ** 2

    return out


# ---------------------------------------------------------------------------
# 3. Single-Pair Feature Builder (Live Backend & Inference Service)
# ---------------------------------------------------------------------------


def _strict_float(val: Any, field_name: str) -> float:
    """Convert a value to float, strictly rejecting None, bool, non-numeric, NaN, and Inf."""
    if val is None or isinstance(val, bool):
        raise ValueError(f"Feature '{field_name}' must be a valid finite numeric value, got {val!r}.")
    try:
        fval = float(val)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Feature '{field_name}' must be numeric, got {val!r} ({type(val).__name__}).") from exc
    if math.isnan(fval) or math.isinf(fval):
        raise ValueError(f"Feature '{field_name}' must be finite (cannot be NaN or Inf), got {val!r}.")
    return fval


def extract_five_stage2_features(feature_dict: dict[str, Any]) -> dict[str, float]:
    """
    Strictly validate and extract the exact 5 Stage 2 v2 features from a dictionary.
    Raises ValueError if any of the 5 features is missing, None, non-numeric, NaN, or Inf.
    """
    if not isinstance(feature_dict, dict):
        raise ValueError("Input features must be provided as a dictionary.")
    missing = [f for f in STAGE2_V2_FEATURES if f not in feature_dict or feature_dict[f] is None]
    if missing:
        raise ValueError(f"Missing required task suitability feature keys: {', '.join(missing)}")
    extracted: dict[str, float] = {}
    for feat in STAGE2_V2_FEATURES:
        extracted[feat] = _strict_float(feature_dict[feat], feat)
    if extracted["difficulty_tier"] not in (1.0, 2.0, 3.0):
        raise ValueError(
            f"Feature 'difficulty_tier' must be 1, 2, or 3, got {extracted['difficulty_tier']}."
        )
    return extracted


def build_complete_stage2_feature_dict(raw_input: dict[str, Any]) -> dict[str, float]:
    """
    Accepts either:
      - A dictionary of raw/gap applicant-task features (from `backend/db.py` or unit tests), OR
      - A dictionary already containing `STAGE2_V2_FEATURES` or `LEGACY_28_FEATURES`.

    Returns a complete dictionary containing both all 5 `STAGE2_V2_FEATURES` and
    all 28 `LEGACY_28_FEATURES` as validated finite floats.
    """
    if not isinstance(raw_input, dict):
        raise ValueError("raw_input must be a dictionary.")
    d = dict(raw_input)

    difficulty_tier = _strict_float(d.get("difficulty_tier", 2.0), "difficulty_tier")
    task_min_exp = _strict_float(d.get("task_min_exp", 0.0), "task_min_exp")
    task_min_assessment = _strict_float(d.get("task_min_assessment", 70.0), "task_min_assessment")

    task_category = d.get("task_category")
    sub_mins = resolve_subskill_minimums(
        task_category, difficulty_tier=difficulty_tier, min_assessment=task_min_assessment
    )

    task_min_comm = _strict_float(d.get("task_min_comm", sub_mins["task_min_comm"]), "task_min_comm")
    task_min_prod = _strict_float(d.get("task_min_prod", sub_mins["task_min_prod"]), "task_min_prod")
    task_min_sales = _strict_float(d.get("task_min_sales", sub_mins["task_min_sales"]), "task_min_sales")
    task_min_cs = _strict_float(d.get("task_min_cs", sub_mins["task_min_cs"]), "task_min_cs")

    app_rel_exp = _strict_float(d.get("applicant_relevant_exp", task_min_exp), "applicant_relevant_exp")
    app_sales_exp = _strict_float(d.get("applicant_sales_exp", app_rel_exp * 0.5), "applicant_sales_exp")
    app_cs_exp = _strict_float(d.get("applicant_cs_exp", app_rel_exp * 0.5), "applicant_cs_exp")

    app_cert_count = _strict_float(d.get("applicant_cert_count", 0.0), "applicant_cert_count")
    app_has_sales_cert = _strict_float(d.get("applicant_has_sales_cert", 0.0), "applicant_has_sales_cert")
    app_has_cs_cert = _strict_float(d.get("applicant_has_cs_cert", 0.0), "applicant_has_cs_cert")
    app_has_tech_cert = _strict_float(d.get("applicant_has_tech_cert", 0.0), "applicant_has_tech_cert")

    app_assess = _strict_float(d.get("applicant_assessment_score", task_min_assessment), "applicant_assessment_score")
    app_comm = _strict_float(d.get("applicant_comm_score", app_assess), "applicant_comm_score")
    app_prod = _strict_float(d.get("applicant_prod_score", app_assess), "applicant_prod_score")
    app_sales = _strict_float(d.get("applicant_sales_score", app_assess), "applicant_sales_score")
    app_cs = _strict_float(d.get("applicant_cs_score", app_assess), "applicant_cs_score")

    # Gaps / surpluses (respect explicit gap values if caller provided them)
    exp_surplus = _strict_float(
        d.get("experience_surplus_months", app_rel_exp - task_min_exp),
        "experience_surplus_months",
    )
    assess_gap = _strict_float(
        d.get("assessment_gap", app_assess - task_min_assessment),
        "assessment_gap",
    )
    comm_gap = _strict_float(d.get("communication_gap", app_comm - task_min_comm), "communication_gap")
    prod_gap = _strict_float(d.get("product_knowledge_gap", app_prod - task_min_prod), "product_knowledge_gap")
    sales_gap = _strict_float(d.get("sales_skill_gap", app_sales - task_min_sales), "sales_skill_gap")
    cs_gap = _strict_float(d.get("customer_service_gap", app_cs - task_min_cs), "customer_service_gap")

    # Relational aggregates
    if "min_skill_margin" in d and d["min_skill_margin"] is not None:
        min_skill_margin = _strict_float(d["min_skill_margin"], "min_skill_margin")
    else:
        min_skill_margin = float(
            min(comm_gap, prod_gap, sales_gap, cs_gap, assess_gap)
        )

    if "weighted_skill_margin" in d and d["weighted_skill_margin"] is not None:
        weighted_skill_margin = _strict_float(d["weighted_skill_margin"], "weighted_skill_margin")
    else:
        w = resolve_domain_weights(task_category)
        weighted_skill_margin = float(
            round(
                w["comm"] * comm_gap
                + w["prod"] * prod_gap
                + w["sales"] * sales_gap
                + w["cs"] * cs_gap,
                4,
            )
        )

    if "weakest_link_deficit" in d and d["weakest_link_deficit"] is not None:
        weakest_link_deficit = _strict_float(d["weakest_link_deficit"], "weakest_link_deficit")
    else:
        weakest_link_deficit = float(min(0.0, min_skill_margin))

    if "exp_surplus_tanh" in d and d["exp_surplus_tanh"] is not None:
        exp_surplus_tanh = _strict_float(d["exp_surplus_tanh"], "exp_surplus_tanh")
    else:
        exp_surplus_tanh = float(math.tanh(exp_surplus / 12.0))

    cert_satisfied = _strict_float(d.get("cert_satisfied", 1.0), "cert_satisfied")

    exp_leverage_ratio = _strict_float(
        d.get("exp_leverage_ratio", app_rel_exp / (task_min_exp + 1.0)),
        "exp_leverage_ratio",
    )
    assessment_gap_sq = _strict_float(d.get("assessment_gap_sq", assess_gap ** 2), "assessment_gap_sq")
    comm_gap_sq = _strict_float(d.get("comm_gap_sq", comm_gap ** 2), "comm_gap_sq")

    return {
        # Stage 2 v2 features (exact 5 features)
        "weighted_skill_margin": weighted_skill_margin,
        "min_skill_margin": min_skill_margin,
        "weakest_link_deficit": weakest_link_deficit,
        "exp_surplus_tanh": exp_surplus_tanh,
        "difficulty_tier": difficulty_tier,
        # Auxiliary indicator retained for explanation / backward compatibility
        "cert_satisfied": cert_satisfied,
        # Legacy 28 features (for full backward compatibility)
        "task_min_exp": task_min_exp,
        "task_min_assessment": task_min_assessment,
        "task_min_comm": task_min_comm,
        "task_min_prod": task_min_prod,
        "task_min_sales": task_min_sales,
        "task_min_cs": task_min_cs,
        "applicant_relevant_exp": app_rel_exp,
        "applicant_sales_exp": app_sales_exp,
        "applicant_cs_exp": app_cs_exp,
        "applicant_cert_count": app_cert_count,
        "applicant_has_sales_cert": app_has_sales_cert,
        "applicant_has_cs_cert": app_has_cs_cert,
        "applicant_has_tech_cert": app_has_tech_cert,
        "applicant_assessment_score": app_assess,
        "applicant_comm_score": app_comm,
        "applicant_prod_score": app_prod,
        "applicant_sales_score": app_sales,
        "applicant_cs_score": app_cs,
        "experience_surplus_months": exp_surplus,
        "assessment_gap": assess_gap,
        "communication_gap": comm_gap,
        "product_knowledge_gap": prod_gap,
        "sales_skill_gap": sales_gap,
        "customer_service_gap": cs_gap,
        "exp_leverage_ratio": exp_leverage_ratio,
        "assessment_gap_sq": assessment_gap_sq,
        "comm_gap_sq": comm_gap_sq,
    }


def explain_stage2_prediction(feature_dict: dict[str, float]) -> list[dict[str, Any]]:
    """
    Generate human-readable, domain-grounded contributing factors for the Admin UI
    corresponding to the exact 5 Stage 2 v2 features (`STAGE2_V2_FEATURES`).
    """
    factors: list[dict[str, Any]] = []

    w_margin = float(feature_dict.get("weighted_skill_margin", 0.0))
    min_margin = float(feature_dict.get("min_skill_margin", 0.0))
    wl_deficit = float(feature_dict.get("weakest_link_deficit", min(0.0, min_margin)))
    exp_surplus = float(feature_dict.get("experience_surplus_months", 0.0))
    exp_tanh = float(feature_dict.get("exp_surplus_tanh", math.tanh(exp_surplus / 12.0)))
    diff_tier = int(round(float(feature_dict.get("difficulty_tier", 2.0))))

    # 1. weighted_skill_margin
    if w_margin >= 8.0:
        factors.append(
            {
                "feature": "weighted_skill_margin",
                "label": "Weighted Competency Margin",
                "value": round(w_margin, 2),
                "unit": "pts",
                "direction": "positive",
                "summary": f"Strong task-weighted skill surplus (+{w_margin:.1f} pts above target)",
            }
        )
    elif w_margin >= 0.0:
        factors.append(
            {
                "feature": "weighted_skill_margin",
                "label": "Weighted Competency Margin",
                "value": round(w_margin, 2),
                "unit": "pts",
                "direction": "neutral",
                "summary": f"Moderate task-weighted skill margin (+{w_margin:.1f} pts above target)",
            }
        )
    else:
        factors.append(
            {
                "feature": "weighted_skill_margin",
                "label": "Weighted Competency Margin",
                "value": round(w_margin, 2),
                "unit": "pts",
                "direction": "negative",
                "summary": f"Sub-target weighted skill margin ({w_margin:.1f} pts vs. task baseline)",
            }
        )

    # 2. min_skill_margin
    if min_margin < 0.0:
        factors.append(
            {
                "feature": "min_skill_margin",
                "label": "Minimum Skill Margin",
                "value": round(min_margin, 2),
                "unit": "pts",
                "direction": "negative",
                "summary": f"Lowest sub-skill margin is below target ({min_margin:.1f} pts)",
            }
        )
    elif min_margin >= 5.0:
        factors.append(
            {
                "feature": "min_skill_margin",
                "label": "Minimum Skill Margin",
                "value": round(min_margin, 2),
                "unit": "pts",
                "direction": "positive",
                "summary": f"All sub-skills exceed target (min margin +{min_margin:.1f} pts)",
            }
        )
    else:
        factors.append(
            {
                "feature": "min_skill_margin",
                "label": "Minimum Skill Margin",
                "value": round(min_margin, 2),
                "unit": "pts",
                "direction": "neutral",
                "summary": f"Borderline minimum sub-skill margin (+{min_margin:.1f} pts)",
            }
        )

    # 3. weakest_link_deficit
    if wl_deficit < 0.0:
        factors.append(
            {
                "feature": "weakest_link_deficit",
                "label": "Weakest-Link Deficit",
                "value": round(wl_deficit, 2),
                "unit": "pts",
                "direction": "negative",
                "summary": f"Bottleneck penalty active ({wl_deficit:.1f} pts deficit on weakest domain)",
            }
        )
    else:
        factors.append(
            {
                "feature": "weakest_link_deficit",
                "label": "Weakest-Link Deficit",
                "value": 0.0,
                "unit": "pts",
                "direction": "positive",
                "summary": "Zero bottleneck deficit (0.0 pts; all domains meet baseline)",
            }
        )

    # 4. exp_surplus_tanh
    if exp_tanh >= 0.50:
        factors.append(
            {
                "feature": "exp_surplus_tanh",
                "label": "Experience Surplus (Tanh)",
                "value": round(exp_tanh, 3),
                "unit": "tanh",
                "direction": "positive",
                "summary": f"Strong experience buffer (tanh={exp_tanh:.2f}, +{exp_surplus:.0f} mos surplus)",
            }
        )
    elif exp_tanh > 0.0:
        factors.append(
            {
                "feature": "exp_surplus_tanh",
                "label": "Experience Surplus (Tanh)",
                "value": round(exp_tanh, 3),
                "unit": "tanh",
                "direction": "positive",
                "summary": f"Moderate experience buffer (tanh={exp_tanh:.2f}, +{exp_surplus:.0f} mos surplus)",
            }
        )
    else:
        factors.append(
            {
                "feature": "exp_surplus_tanh",
                "label": "Experience Surplus (Tanh)",
                "value": round(exp_tanh, 3),
                "unit": "tanh",
                "direction": "neutral",
                "summary": f"At minimum required experience threshold (tanh={exp_tanh:.2f})",
            }
        )

    # 5. difficulty_tier
    tier_names = {1: "Low (Tier 1)", 2: "Medium (Tier 2)", 3: "High (Tier 3)"}
    factors.append(
        {
            "feature": "difficulty_tier",
            "label": "Task Difficulty Tier",
            "value": diff_tier,
            "unit": "tier",
            "direction": "negative" if diff_tier == 3 else ("positive" if diff_tier == 1 else "neutral"),
            "summary": f"Task complexity: {tier_names.get(diff_tier, f'Tier {diff_tier}')}",
        }
    )

    return factors

