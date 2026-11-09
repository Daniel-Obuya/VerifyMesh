"""
VerifyMesh - Task-Specific Synthetic Dataset Generator
======================================================
Research Prototype Data Generation Pipeline for Task-Specific Performance Modeling.

This script generates synthetic applicants, task definitions, applicant-task pairs,
and eligibility/suitability outcomes for experiment evaluation.

IMPORTANT RESEARCH INTEGRITY NOTICE:
All generated outcomes are purely synthetic and generated via parametric simulation.
They do NOT represent empirical real-world task completions.
"""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def get_default_output_dir() -> Path:
    """Return default output directory for task-specific synthetic dataset."""
    return Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Task Templates & Domain Definitions
# ---------------------------------------------------------------------------

TASK_CATEGORIES = [
    "Enterprise Sales",
    "Customer Support Escalations",
    "Technical Product Onboarding",
    "Quality Assurance & Compliance",
    "Account Retention & Growth"
]

CATEGORY_DOMAINS = {
    "Enterprise Sales": {
        "primary_skill": "sales_skill_score",
        "primary_exp": "sales_experience_months",
        "preferred_cert": "Sales_Specialist",
        "weights": {"comm": 0.25, "prod": 0.20, "sales": 0.50, "cs": 0.05}
    },
    "Customer Support Escalations": {
        "primary_skill": "customer_service_score",
        "primary_exp": "customer_service_experience_months",
        "preferred_cert": "Customer_Success_Pro",
        "weights": {"comm": 0.35, "prod": 0.15, "sales": 0.05, "cs": 0.45}
    },
    "Technical Product Onboarding": {
        "primary_skill": "product_knowledge_score",
        "primary_exp": "relevant_experience_months",
        "preferred_cert": "Technical_Support_Architect",
        "weights": {"comm": 0.25, "prod": 0.50, "sales": 0.10, "cs": 0.15}
    },
    "Quality Assurance & Compliance": {
        "primary_skill": "assessment_score",
        "primary_exp": "relevant_experience_months",
        "preferred_cert": "None",
        "weights": {"comm": 0.20, "prod": 0.35, "sales": 0.10, "cs": 0.35}
    },
    "Account Retention & Growth": {
        "primary_skill": "communication_score",
        "primary_exp": "sales_experience_months",
        "preferred_cert": "Customer_Success_Pro",
        "weights": {"comm": 0.35, "prod": 0.20, "sales": 0.25, "cs": 0.20}
    }
}


# ---------------------------------------------------------------------------
# 1. Applicant Generation
# ---------------------------------------------------------------------------

def generate_applicants(num_applicants: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate synthetic applicant population with realistic cross-skill correlation
    and internally consistent tenure values.
    """
    applicant_ids = [f"APP-{i+1:04d}" for i in range(num_applicants)]

    # Correlated skill latents using covariance matrix
    # Dimensions: [assessment, communication, product_knowledge, sales_skill, customer_service]
    mean_skills = np.array([68.0, 70.0, 65.0, 62.0, 66.0])
    cov_skills = np.array([
        [140.0,  45.0,  55.0,  30.0,  35.0],
        [ 45.0, 130.0,  30.0,  40.0,  50.0],
        [ 55.0,  30.0, 150.0,  20.0,  25.0],
        [ 30.0,  40.0,  20.0, 160.0,  15.0],
        [ 35.0,  50.0,  25.0,  15.0, 140.0]
    ])

    raw_scores = rng.multivariate_normal(mean_skills, cov_skills, size=num_applicants)
    scores = np.clip(np.round(raw_scores, 1), 15.0, 99.0)

    # Experience generation (months) using log-normal distributions
    sales_exp = np.round(rng.lognormal(mean=2.6, sigma=0.85, size=num_applicants)).astype(int)
    sales_zero_mask = rng.random(num_applicants) < 0.22
    sales_exp[sales_zero_mask] = 0
    sales_exp = np.clip(sales_exp, 0, 120)

    cs_exp = np.round(rng.lognormal(mean=2.7, sigma=0.80, size=num_applicants)).astype(int)
    cs_zero_mask = rng.random(num_applicants) < 0.20
    cs_exp[cs_zero_mask] = 0
    cs_exp = np.clip(cs_exp, 0, 120)

    base_exp = np.round(rng.lognormal(mean=2.8, sigma=0.75, size=num_applicants)).astype(int)
    base_exp = np.clip(base_exp, 0, 140)

    # Ensure internally consistent total experience:
    # Total experience represents overall career tenure, which must be >= any specialized sub-tenure
    overlap_factor = rng.uniform(0.3, 0.7, size=num_applicants)
    total_exp = np.maximum(
        np.maximum(sales_exp, cs_exp),
        np.round(base_exp + (1.0 - overlap_factor) * (sales_exp + cs_exp)).astype(int)
    )
    total_exp = np.clip(total_exp, 1, 180)

    # Relevant experience for general technical/domain evaluation
    relevant_exp = np.clip(np.round(total_exp * rng.uniform(0.70, 1.0, size=num_applicants)).astype(int), 0, 180)

    # Certifications
    cert_propensity = (
        0.20
        + 0.003 * total_exp
        + 0.004 * (scores[:, 0] - 50.0)
    )
    cert_propensity = np.clip(cert_propensity, 0.05, 0.85)

    has_sales_cert = (rng.random(num_applicants) < (cert_propensity * (sales_exp > 6) * (scores[:, 3] > 60))).astype(int)
    has_cs_cert = (rng.random(num_applicants) < (cert_propensity * (cs_exp > 6) * (scores[:, 4] > 60))).astype(int)
    has_tech_cert = (rng.random(num_applicants) < (cert_propensity * (scores[:, 2] > 65))).astype(int)

    cert_count = has_sales_cert + has_cs_cert + has_tech_cert
    extra_certs = (rng.random(num_applicants) < 0.25).astype(int) + (rng.random(num_applicants) < 0.10).astype(int)
    cert_count = np.clip(cert_count + extra_certs, 0, 5)

    primary_certs = []
    for i in range(num_applicants):
        certs = []
        if has_tech_cert[i]:
            certs.append("Technical_Support_Architect")
        if has_sales_cert[i]:
            certs.append("Sales_Specialist")
        if has_cs_cert[i]:
            certs.append("Customer_Success_Pro")
        if certs:
            primary_certs.append(certs[0])
        else:
            primary_certs.append("None")

    df_applicants = pd.DataFrame({
        "applicant_id": applicant_ids,
        "relevant_experience_months": relevant_exp,
        "sales_experience_months": sales_exp,
        "customer_service_experience_months": cs_exp,
        "total_experience_months": total_exp,
        "certification_count": cert_count,
        "has_sales_cert": has_sales_cert,
        "has_cs_cert": has_cs_cert,
        "has_technical_cert": has_tech_cert,
        "primary_certification": primary_certs,
        "assessment_score": scores[:, 0],
        "communication_score": scores[:, 1],
        "product_knowledge_score": scores[:, 2],
        "sales_skill_score": scores[:, 3],
        "customer_service_score": scores[:, 4]
    })

    return df_applicants


# ---------------------------------------------------------------------------
# 2. Task Generation
# ---------------------------------------------------------------------------

def generate_tasks(num_tasks: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate synthetic task catalog across multiple categories and difficulty tiers.
    Task requirements vary systematically so optimal applicant match is task-dependent.
    """
    archetypes = [
        # Enterprise Sales
        ("Enterprise Sales", "B2B SaaS Mid-Market Pipeline Prospecting", "Medium", 2, 12, "Sales_Specialist", 65, 70, 60, 70, 50),
        ("Enterprise Sales", "Strategic Enterprise Key Account Closing", "High", 3, 30, "Sales_Specialist", 75, 80, 70, 80, 55),
        ("Enterprise Sales", "Inbound Sales Lead Qualification", "Low", 1, 6, "None", 55, 65, 50, 60, 45),
        ("Enterprise Sales", "Public Sector RFP Proposal Pitching", "High", 3, 24, "Sales_Specialist", 75, 78, 72, 78, 50),
        ("Enterprise Sales", "Channel Partner Reseller Enablement", "Medium", 2, 18, "Sales_Specialist", 68, 72, 65, 68, 50),
        ("Enterprise Sales", "High-Velocity Inside Sales Campaigns", "Low", 1, 3, "None", 50, 60, 45, 60, 45),

        # Customer Support Escalations
        ("Customer Support Escalations", "Tier-1 Multi-Channel Helpdesk Support", "Low", 1, 3, "None", 50, 65, 45, 40, 65),
        ("Customer Support Escalations", "Enterprise SLA Incident Escalation Lead", "High", 3, 24, "Customer_Success_Pro", 75, 78, 68, 45, 80),
        ("Customer Support Escalations", "Billing Dispute & Executive Complaint Resolution", "Medium", 2, 15, "Customer_Success_Pro", 65, 72, 55, 45, 72),
        ("Customer Support Escalations", "24/7 Global NOC Service Desk Agent", "Medium", 2, 12, "None", 60, 68, 60, 40, 68),
        ("Customer Support Escalations", "High-Touch VIP Client Concierge", "High", 3, 20, "Customer_Success_Pro", 70, 82, 65, 50, 80),
        ("Customer Support Escalations", "Social Media Reputation & Ticket Triage", "Low", 1, 6, "None", 55, 68, 48, 40, 65),

        # Technical Product Onboarding
        ("Technical Product Onboarding", "Developer API & Webhook Integration Guidance", "High", 3, 30, "Technical_Support_Architect", 78, 70, 82, 40, 50),
        ("Technical Product Onboarding", "Self-Serve Platform Setup & Walkthrough", "Low", 1, 6, "None", 55, 65, 60, 40, 50),
        ("Technical Product Onboarding", "Data Migration & Custom ETL Validation", "High", 3, 24, "Technical_Support_Architect", 75, 68, 80, 35, 50),
        ("Technical Product Onboarding", "SSO & Identity Provider Configuration Assistance", "Medium", 2, 15, "Technical_Support_Architect", 68, 68, 72, 35, 50),
        ("Technical Product Onboarding", "Mobile SDK Debugging & Sandbox Deployment", "Medium", 2, 12, "None", 65, 65, 68, 30, 50),
        ("Technical Product Onboarding", "Technical Architecture Scope & Kickoff", "High", 3, 36, "Technical_Support_Architect", 80, 75, 85, 45, 50),

        # Quality Assurance & Compliance
        ("Quality Assurance & Compliance", "Call Recording QA & Scorecard Auditing", "Low", 1, 6, "None", 60, 65, 55, 40, 60),
        ("Quality Assurance & Compliance", "GDPR & HIPAA Compliance Verification Audit", "High", 3, 30, "None", 78, 70, 75, 40, 60),
        ("Quality Assurance & Compliance", "Financial Transaction AML & KYC Verification", "Medium", 2, 18, "None", 68, 65, 65, 40, 60),
        ("Quality Assurance & Compliance", "Contract Fulfillment & SLA Audit Reporting", "Medium", 2, 20, "None", 70, 68, 68, 45, 55),
        ("Quality Assurance & Compliance", "Agent Scripting & Standard Operating Procedure Review", "Low", 1, 10, "None", 60, 65, 55, 40, 60),
        ("Quality Assurance & Compliance", "Regulatory Anti-Fraud Investigation Sprint", "High", 3, 24, "None", 78, 68, 78, 40, 62),

        # Account Retention & Growth
        ("Account Retention & Growth", "At-Risk Client Churn Intervention & Save", "High", 3, 24, "Customer_Success_Pro", 72, 80, 65, 70, 75),
        ("Account Retention & Growth", "Quarterly Business Review (QBR) Facilitation", "Medium", 2, 15, "None", 65, 75, 62, 60, 68),
        ("Account Retention & Growth", "Subscription Tier Contract Renewal Processing", "Low", 1, 6, "None", 55, 65, 52, 58, 60),
        ("Account Retention & Growth", "Enterprise Client Health Monitoring & NPS Advisory", "Medium", 2, 18, "Customer_Success_Pro", 68, 78, 65, 65, 72),
        ("Account Retention & Growth", "Cross-Sell Expansion Campaign for Existing Accounts", "Medium", 2, 15, "Sales_Specialist", 65, 72, 62, 70, 65),
        ("Account Retention & Growth", "Strategic Executive Partnership Advisory", "High", 3, 36, "Customer_Success_Pro", 78, 82, 72, 75, 78),
    ]

    selected_archetypes = archetypes[:num_tasks]
    if len(selected_archetypes) < num_tasks:
        extra_count = num_tasks - len(selected_archetypes)
        for i in range(extra_count):
            base = archetypes[i % len(archetypes)]
            selected_archetypes.append((
                base[0],
                f"{base[1]} (Cohort {i+2})",
                base[2],
                base[3],
                max(0, base[4] + int(rng.choice([-6, 0, 6]))),
                base[5],
                max(40, min(90, base[6] + int(rng.choice([-5, 0, 5])))),
                max(40, min(90, base[7] + int(rng.choice([-5, 0, 5])))),
                max(40, min(90, base[8] + int(rng.choice([-5, 0, 5])))),
                max(40, min(90, base[9] + int(rng.choice([-5, 0, 5])))),
                max(40, min(90, base[10] + int(rng.choice([-5, 0, 5]))))
            ))

    tasks_data = []
    for idx, item in enumerate(selected_archetypes):
        tasks_data.append({
            "task_id": f"TSK-{idx+1:03d}",
            "task_title": item[1],
            "task_category": item[0],
            "difficulty_level": item[2],
            "difficulty_tier": item[3],
            "min_relevant_experience_months": item[4],
            "required_certification": item[5],
            "min_assessment_score": float(item[6]),
            "min_communication_score": float(item[7]),
            "min_product_knowledge_score": float(item[8]),
            "min_sales_skill_score": float(item[9]),
            "min_customer_service_score": float(item[10])
        })

    return pd.DataFrame(tasks_data)


# ---------------------------------------------------------------------------
# 3. Applicant-Task Pairing & Feature Engineering
# ---------------------------------------------------------------------------

def calculate_pair_features(applicant: pd.Series, task: pd.Series) -> dict:
    """
    Derive relational match features and evaluate rule-based mandatory eligibility.
    """
    category = task["task_category"]

    # 1. Relevant experience mapping for the task
    if category == "Enterprise Sales":
        task_rel_exp = float(applicant["sales_experience_months"])
    elif category == "Customer Support Escalations":
        task_rel_exp = float(applicant["customer_service_experience_months"])
    elif category == "Technical Product Onboarding":
        task_rel_exp = float(applicant["relevant_experience_months"])
    elif category == "Quality Assurance & Compliance":
        task_rel_exp = float(applicant["relevant_experience_months"])
    elif category == "Account Retention & Growth":
        task_rel_exp = float(0.5 * applicant["sales_experience_months"] + 0.5 * applicant["customer_service_experience_months"])
    else:
        task_rel_exp = float(applicant["relevant_experience_months"])

    min_exp_req = float(task["min_relevant_experience_months"])
    experience_surplus = task_rel_exp - min_exp_req

    # 2. Skill gaps (Applicant Score - Task Minimum Requirement)
    assessment_gap = float(applicant["assessment_score"] - task["min_assessment_score"])
    comm_skill_gap = float(applicant["communication_score"] - task["min_communication_score"])
    product_know_gap = float(applicant["product_knowledge_score"] - task["min_product_knowledge_score"])
    sales_skill_gap = float(applicant["sales_skill_score"] - task["min_sales_skill_score"])
    cs_skill_gap = float(applicant["customer_service_score"] - task["min_customer_service_score"])

    # 3. Weighted domain skill margin
    domain_weights = CATEGORY_DOMAINS[category]["weights"]
    weighted_skill_margin = (
        domain_weights["comm"] * comm_skill_gap +
        domain_weights["prod"] * product_know_gap +
        domain_weights["sales"] * sales_skill_gap +
        domain_weights["cs"] * cs_skill_gap
    )
    min_skill_margin = min(comm_skill_gap, product_know_gap, sales_skill_gap, cs_skill_gap, assessment_gap)

    # 4. Certification requirement satisfaction
    req_cert = task["required_certification"]
    if req_cert == "None":
        cert_satisfied = 1
    elif req_cert == "Sales_Specialist":
        cert_satisfied = int(applicant["has_sales_cert"] == 1 or applicant["primary_certification"] == "Sales_Specialist")
    elif req_cert == "Customer_Success_Pro":
        cert_satisfied = int(applicant["has_cs_cert"] == 1 or applicant["primary_certification"] == "Customer_Success_Pro")
    elif req_cert == "Technical_Support_Architect":
        cert_satisfied = int(applicant["has_technical_cert"] == 1 or applicant["primary_certification"] == "Technical_Support_Architect")
    else:
        cert_satisfied = 1

    # 5. Assessment satisfaction
    assessment_satisfied = int(
        assessment_gap >= 0 and
        comm_skill_gap >= -5.0 and
        product_know_gap >= -5.0 and
        sales_skill_gap >= -8.0 and
        cs_skill_gap >= -8.0
    )

    # 6. Rule-based mandatory eligibility determination
    ineligibility_reasons = []
    if cert_satisfied == 0:
        ineligibility_reasons.append(f"Lacks required certification: {req_cert}")

    if experience_surplus < 0:
        ineligibility_reasons.append(
            f"Insufficient experience (has {task_rel_exp:.0f}m, requires {min_exp_req:.0f}m)"
        )

    if assessment_gap < 0:
        ineligibility_reasons.append(
            f"Overall assessment below cutoff ({applicant['assessment_score']:.1f} < {task['min_assessment_score']:.1f})"
        )
    if comm_skill_gap < -5.0:
        ineligibility_reasons.append(f"Communication deficit below minimum ({applicant['communication_score']:.1f} < {task['min_communication_score']:.1f})")
    if product_know_gap < -5.0:
        ineligibility_reasons.append(f"Product knowledge deficit below minimum ({applicant['product_knowledge_score']:.1f} < {task['min_product_knowledge_score']:.1f})")

    if category == "Enterprise Sales" and sales_skill_gap < -3.0:
        ineligibility_reasons.append(f"Sales skill below threshold ({applicant['sales_skill_score']:.1f} < {task['min_sales_skill_score']:.1f})")
    if category == "Customer Support Escalations" and cs_skill_gap < -3.0:
        ineligibility_reasons.append(f"Customer service skill below threshold ({applicant['customer_service_score']:.1f} < {task['min_customer_service_score']:.1f})")

    is_eligible = 1 if len(ineligibility_reasons) == 0 else 0
    reasons_str = "Eligible" if is_eligible == 1 else "; ".join(ineligibility_reasons)

    return {
        "task_relevant_experience_months": round(task_rel_exp, 1),
        "experience_surplus_months": round(experience_surplus, 1),
        "assessment_gap": round(assessment_gap, 1),
        "communication_gap": round(comm_skill_gap, 1),
        "product_knowledge_gap": round(product_know_gap, 1),
        "sales_skill_gap": round(sales_skill_gap, 1),
        "customer_service_gap": round(cs_skill_gap, 1),
        "min_skill_margin": round(min_skill_margin, 1),
        "weighted_skill_margin": round(weighted_skill_margin, 2),
        "cert_satisfied": cert_satisfied,
        "assessment_satisfied": assessment_satisfied,
        "is_eligible": is_eligible,
        "ineligibility_reasons": reasons_str
    }


# ---------------------------------------------------------------------------
# 4. Stochastic Outcome Simulation Scenarios
# ---------------------------------------------------------------------------

def simulate_outcome(
    features: dict,
    applicant: pd.Series,
    task: pd.Series,
    scenario: str,
    rng: np.random.Generator
) -> tuple[float, float, int]:
    """
    Parametric stochastic outcome simulation.
    Returns: (latent_score, latent_success_prob, task_success)
    """
    diff_tier = float(task["difficulty_tier"])
    weighted_margin = features["weighted_skill_margin"]
    exp_surplus = features["experience_surplus_months"]
    min_margin = features["min_skill_margin"]
    cert_bonus = 0.30 if features["cert_satisfied"] == 1 else -0.50

    if scenario == "scenario_a":
        # Scenario A: Balanced Compensatory
        # Log-odds index:
        # z = beta_0 + beta_skill * weighted_margin + beta_exp * tanh(exp_surplus / 12)
        #     + cert_bonus - beta_diff * (diff_tier - 1) + noise
        beta_0 = -0.22  # Calibrated for realistic ~60% pass rate among eligible applicants
        beta_skill = 0.040
        beta_exp = 0.55
        beta_diff = 0.55

        # Diminishing marginal returns on excess tenure
        exp_component = np.tanh(exp_surplus / 12.0)

        # Environmental Gaussian perturbation
        noise = rng.normal(loc=0.0, scale=0.45)

        latent_score = (
            beta_0
            + beta_skill * weighted_margin
            + beta_exp * exp_component
            + cert_bonus
            - beta_diff * (diff_tier - 1.0)
            + noise
        )

        prob = 1.0 / (1.0 + np.exp(-latent_score))
        prob = np.clip(prob, 0.03, 0.97)

    elif scenario == "scenario_b":
        # Scenario B: Strict Bottleneck / High-Stakes
        # High penalty for weakest skill; non-linear difficulty penalty
        beta_0 = -0.15
        beta_skill = 0.028
        beta_min = 0.035
        beta_diff = 0.40

        weakest_penalty = 0.0
        if min_margin < 0:
            weakest_penalty = 0.045 * (abs(min_margin) ** 1.15)

        exp_component = 0.28 * np.log1p(max(0.0, exp_surplus))
        diff_component = beta_diff * (diff_tier ** 1.35)

        # Logistic distribution disturbance for heavier tails
        noise = rng.logistic(loc=0.0, scale=0.40)

        latent_score = (
            beta_0
            + beta_skill * weighted_margin
            + beta_min * min_margin
            + exp_component
            + cert_bonus
            - weakest_penalty
            - diff_component
            + noise
        )

        prob = 1.0 / (1.0 + np.exp(-latent_score))
        prob = np.clip(prob, 0.02, 0.98)

    else:
        raise ValueError(f"Unknown simulation scenario: {scenario}")

    # Bernoulli trial with simulated probability
    task_success = int(rng.random() < prob)

    return float(round(latent_score, 4)), float(round(prob, 4)), task_success


# ---------------------------------------------------------------------------
# 5. Core Pipeline Assembly
# ---------------------------------------------------------------------------

def generate_task_specific_dataset(
    num_applicants: int = 800,
    num_tasks: int = 30,
    num_pairs: int = 6000,
    scenario: str = "scenario_a",
    seed: int = 42,
    output_dir: Path = None
) -> dict:
    """
    Execute full dataset generation pipeline, produce all CSV files, and perform validation checks.
    """
    if output_dir is None:
        output_dir = get_default_output_dir()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    print(f"[Pipeline] Initializing synthetic dataset generation (Seed: {seed}, Scenario: {scenario})...")

    # 1. Generate Applicants
    df_applicants = generate_applicants(num_applicants, rng)
    applicants_path = output_dir / "synthetic_applicants.csv"
    df_applicants.to_csv(applicants_path, index=False)
    print(f"[Pipeline] Saved {len(df_applicants)} applicants to: {applicants_path.name}")

    # 2. Generate Tasks
    df_tasks = generate_tasks(num_tasks, rng)
    tasks_path = output_dir / "synthetic_tasks.csv"
    df_tasks.to_csv(tasks_path, index=False)
    print(f"[Pipeline] Saved {len(df_tasks)} tasks to: {tasks_path.name}")

    # 3. Generate Applicant-Task Pairs
    # Structured realistic application sampling:
    # On a workforce platform, ~55% of task applications come from candidates with relevant domain background
    # and ~45% come from exploratory or cross-domain candidates.
    pairs_list = []
    pairs_per_task = int(np.ceil(num_pairs / num_tasks))
    all_applicant_indices = np.arange(num_applicants)

    pair_keys = set()
    for _, task in df_tasks.iterrows():
        cat = task["task_category"]

        # Identify affinity applicants
        if cat == "Enterprise Sales":
            affinity_mask = (df_applicants["sales_experience_months"] > 6) | (df_applicants["has_sales_cert"] == 1) | (df_applicants["sales_skill_score"] > 65)
        elif cat == "Customer Support Escalations":
            affinity_mask = (df_applicants["customer_service_experience_months"] > 6) | (df_applicants["has_cs_cert"] == 1) | (df_applicants["customer_service_score"] > 65)
        elif cat == "Technical Product Onboarding":
            affinity_mask = (df_applicants["relevant_experience_months"] > 12) | (df_applicants["has_technical_cert"] == 1) | (df_applicants["product_knowledge_score"] > 68)
        elif cat == "Quality Assurance & Compliance":
            affinity_mask = (df_applicants["relevant_experience_months"] > 12) | (df_applicants["assessment_score"] > 70)
        elif cat == "Account Retention & Growth":
            affinity_mask = ((df_applicants["sales_experience_months"] > 6) & (df_applicants["customer_service_experience_months"] > 6)) | (df_applicants["communication_score"] > 72)
        else:
            affinity_mask = df_applicants["relevant_experience_months"] > 12

        affinity_indices = df_applicants[affinity_mask].index.to_numpy()
        general_indices = df_applicants[~affinity_mask].index.to_numpy()

        num_affinity = int(round(pairs_per_task * 0.55))
        num_general = pairs_per_task - num_affinity

        selected_affinity = rng.choice(affinity_indices, size=min(num_affinity, len(affinity_indices)), replace=False)
        selected_general = rng.choice(all_applicant_indices, size=num_general, replace=False)
        combined_sampled = np.unique(np.concatenate([selected_affinity, selected_general]))

        # Ensure exact pairs_per_task count
        if len(combined_sampled) < pairs_per_task:
            remaining = np.setdiff1d(all_applicant_indices, combined_sampled)
            fill = rng.choice(remaining, size=pairs_per_task - len(combined_sampled), replace=False)
            combined_sampled = np.concatenate([combined_sampled, fill])
        elif len(combined_sampled) > pairs_per_task:
            combined_sampled = combined_sampled[:pairs_per_task]

        for app_idx in combined_sampled:
            app_id = df_applicants.loc[app_idx, "applicant_id"]
            tsk_id = task["task_id"]
            key = (app_id, tsk_id)
            if key in pair_keys:
                continue
            pair_keys.add(key)

            applicant = df_applicants.loc[app_idx]
            match_feats = calculate_pair_features(applicant, task)
            latent_score, latent_prob, outcome = simulate_outcome(match_feats, applicant, task, scenario, rng)

            row = {
                "applicant_id": applicant["applicant_id"],
                "task_id": task["task_id"],
                "task_category": task["task_category"],
                "difficulty_tier": task["difficulty_tier"],
                "difficulty_level": task["difficulty_level"],
                # Applicant raw features
                "applicant_relevant_exp": applicant["relevant_experience_months"],
                "applicant_sales_exp": applicant["sales_experience_months"],
                "applicant_cs_exp": applicant["customer_service_experience_months"],
                "applicant_cert_count": applicant["certification_count"],
                "applicant_has_sales_cert": applicant["has_sales_cert"],
                "applicant_has_cs_cert": applicant["has_cs_cert"],
                "applicant_has_tech_cert": applicant["has_technical_cert"],
                "applicant_primary_cert": applicant["primary_certification"],
                "applicant_assessment_score": applicant["assessment_score"],
                "applicant_comm_score": applicant["communication_score"],
                "applicant_prod_score": applicant["product_knowledge_score"],
                "applicant_sales_score": applicant["sales_skill_score"],
                "applicant_cs_score": applicant["customer_service_score"],
                # Task raw features
                "task_min_exp": task["min_relevant_experience_months"],
                "task_required_cert": task["required_certification"],
                "task_min_assessment": task["min_assessment_score"],
                "task_min_comm": task["min_communication_score"],
                "task_min_prod": task["min_product_knowledge_score"],
                "task_min_sales": task["min_sales_skill_score"],
                "task_min_cs": task["min_customer_service_score"],
                # Relational features
                "task_relevant_experience_months": match_feats["task_relevant_experience_months"],
                "experience_surplus_months": match_feats["experience_surplus_months"],
                "assessment_gap": match_feats["assessment_gap"],
                "communication_gap": match_feats["communication_gap"],
                "product_knowledge_gap": match_feats["product_knowledge_gap"],
                "sales_skill_gap": match_feats["sales_skill_gap"],
                "customer_service_gap": match_feats["customer_service_gap"],
                "min_skill_margin": match_feats["min_skill_margin"],
                "weighted_skill_margin": match_feats["weighted_skill_margin"],
                "cert_satisfied": match_feats["cert_satisfied"],
                "assessment_satisfied": match_feats["assessment_satisfied"],
                # Eligibility gate
                "is_eligible": match_feats["is_eligible"],
                "ineligibility_reasons": match_feats["ineligibility_reasons"],
                # Diagnostic simulation outputs (NOT model inputs)
                "simulation_scenario": scenario,
                "latent_score": latent_score,
                "latent_success_prob": latent_prob,
                # Target variable
                "task_success": outcome
            }
            pairs_list.append(row)

    df_all_pairs = pd.DataFrame(pairs_list)
    all_pairs_path = output_dir / "synthetic_applicant_task_pairs.csv"
    df_all_pairs.to_csv(all_pairs_path, index=False)
    print(f"[Pipeline] Saved {len(df_all_pairs)} applicant-task pairs to: {all_pairs_path.name}")

    # 4. Generate Task Suitability Training Dataset (Eligible pairs only)
    df_training = df_all_pairs[df_all_pairs["is_eligible"] == 1].copy()

    # Permitted predictive features: strictly exclude IDs, latent probabilities, and eligibility labels
    permitted_features = [
        # Categorical task features
        "task_category",
        "difficulty_level",
        "difficulty_tier",
        # Task requirements
        "task_min_exp",
        "task_required_cert",
        "task_min_assessment",
        "task_min_comm",
        "task_min_prod",
        "task_min_sales",
        "task_min_cs",
        # Applicant characteristics
        "applicant_relevant_exp",
        "applicant_sales_exp",
        "applicant_cs_exp",
        "applicant_cert_count",
        "applicant_has_sales_cert",
        "applicant_has_cs_cert",
        "applicant_has_tech_cert",
        "applicant_primary_cert",
        "applicant_assessment_score",
        "applicant_comm_score",
        "applicant_prod_score",
        "applicant_sales_score",
        "applicant_cs_score",
        # Relational Match Features
        "task_relevant_experience_months",
        "experience_surplus_months",
        "assessment_gap",
        "communication_gap",
        "product_knowledge_gap",
        "sales_skill_gap",
        "customer_service_gap",
        "min_skill_margin",
        "weighted_skill_margin",
        "cert_satisfied",
        "assessment_satisfied"
    ]

    target_col = "task_success"
    training_cols = permitted_features + [target_col]
    df_training_export = df_training[training_cols]

    training_path = output_dir / "task_suitability_training.csv"
    df_training_export.to_csv(training_path, index=False)
    print(f"[Pipeline] Saved {len(df_training_export)} eligible training pairs to: {training_path.name}")

    return {
        "df_applicants": df_applicants,
        "df_tasks": df_tasks,
        "df_all_pairs": df_all_pairs,
        "df_training": df_training_export,
        "permitted_features": permitted_features,
        "target_col": target_col,
        "scenario": scenario,
        "seed": seed,
        "paths": {
            "applicants": applicants_path,
            "tasks": tasks_path,
            "all_pairs": all_pairs_path,
            "training": training_path
        }
    }


# ---------------------------------------------------------------------------
# 6. Automated Validation Engine
# ---------------------------------------------------------------------------

def validate_datasets(pipeline_results: dict) -> dict:
    """
    Run automated validation checks across all generated datasets.
    """
    checks = []

    df_app = pipeline_results["df_applicants"]
    df_tsk = pipeline_results["df_tasks"]
    df_pairs = pipeline_results["df_all_pairs"]
    df_train = pipeline_results["df_training"]

    # 1. Unique IDs
    chk1 = len(df_app["applicant_id"].unique()) == len(df_app)
    checks.append(("Applicant IDs are unique", chk1, f"Found {len(df_app['applicant_id'].unique())} unique out of {len(df_app)}"))

    chk2 = len(df_tsk["task_id"].unique()) == len(df_tsk)
    checks.append(("Task IDs are unique", chk2, f"Found {len(df_tsk['task_id'].unique())} unique out of {len(df_tsk)}"))

    # 2. No duplicate pairs
    pair_tuples = list(zip(df_pairs["applicant_id"], df_pairs["task_id"]))
    chk3 = len(set(pair_tuples)) == len(pair_tuples)
    checks.append(("Applicant-Task combinations are unique (no duplicate pairs)", chk3, f"Total pairs: {len(pair_tuples)}, unique: {len(set(pair_tuples))}"))

    # 3. Range checks
    score_cols = ["assessment_score", "communication_score", "product_knowledge_score", "sales_skill_score", "customer_service_score"]
    all_scores_valid = True
    for sc in score_cols:
        if df_app[sc].min() < 0 or df_app[sc].max() > 100:
            all_scores_valid = False
    checks.append(("Applicant scores bounded in [0, 100]", all_scores_valid, f"Min score: {min([df_app[c].min() for c in score_cols])}, Max score: {max([df_app[c].max() for c in score_cols])}"))

    # 4. Experience consistency
    exp_consistent = (
        (df_app["sales_experience_months"] >= 0).all() and
        (df_app["customer_service_experience_months"] >= 0).all() and
        (df_app["relevant_experience_months"] >= 0).all() and
        (df_app["total_experience_months"] >= df_app["sales_experience_months"]).all() and
        (df_app["total_experience_months"] >= df_app["customer_service_experience_months"]).all()
    )
    checks.append(("Experience values non-negative and internally consistent", exp_consistent, "All individual tenures <= total_experience_months and non-negative"))

    # 5. Missing values
    missing_app = df_app.isnull().sum().sum()
    missing_tsk = df_tsk.isnull().sum().sum()
    missing_pairs = df_pairs.isnull().sum().sum()
    checks.append(("No missing or null values in source tables", (missing_app == 0 and missing_tsk == 0 and missing_pairs == 0), f"App nulls: {missing_app}, Task nulls: {missing_tsk}, Pairs nulls: {missing_pairs}"))

    # 6. Correct eligibility separation
    all_train_eligible = (df_train.index.isin(df_pairs[df_pairs["is_eligible"] == 1].index)).all()
    checks.append(("Training dataset contains ONLY eligible pairs", all_train_eligible, f"Eligible pairs count: {len(df_train)} out of {len(df_pairs)}"))

    # Ineligible pairs record reasons
    ineligible_pairs = df_pairs[df_pairs["is_eligible"] == 0]
    ineligible_have_reasons = (ineligible_pairs["ineligibility_reasons"] != "Eligible").all() and (ineligible_pairs["ineligibility_reasons"].str.len() > 0).all()
    checks.append(("Ineligible pairs have documented rejection reasons", ineligible_have_reasons, f"Ineligible count: {len(ineligible_pairs)}, all have non-empty reason strings"))

    # 7. No target leakage into training features
    forbidden_leakage = ["applicant_id", "task_id", "latent_score", "latent_success_prob", "simulation_scenario", "is_eligible", "ineligibility_reasons"]
    leakage_detected = [f for f in forbidden_leakage if f in df_train.columns]
    checks.append(("No leakage of IDs, latent simulation probabilities, or gatekeeper labels in training features", len(leakage_detected) == 0, f"Detected forbidden columns: {leakage_detected}"))

    # 8. Category coverage
    cats_in_tasks = set(df_tsk["task_category"])
    cats_in_pairs = set(df_pairs["task_category"])
    checks.append(("All task categories represented in tasks and pairs", cats_in_tasks == cats_in_pairs and len(cats_in_tasks) == 5, f"Categories present: {len(cats_in_tasks)}"))

    # 9. Class balance in training set
    pos_rate = df_train["task_success"].mean()
    class_balance_ok = 0.25 <= pos_rate <= 0.85
    checks.append(("Training set has non-trivial positive and negative representations", class_balance_ok, f"Success rate: {pos_rate:.1%} (Positive: {df_train['task_success'].sum()}, Negative: {(1-df_train['task_success']).sum()})"))

    return {
        "checks": checks,
        "all_passed": all(c[1] for c in checks),
        "total_applicants": len(df_app),
        "total_tasks": len(df_tsk),
        "total_pairs": len(df_pairs),
        "eligible_pairs": len(df_train),
        "ineligible_pairs": len(ineligible_pairs),
        "positive_count": int(df_train["task_success"].sum()),
        "negative_count": int((1 - df_train["task_success"]).sum()),
        "positive_rate": float(pos_rate)
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic dataset for VerifyMesh task-specific suitability.")
    parser.add_argument("--num-applicants", type=int, default=800, help="Number of synthetic applicants (default: 800)")
    parser.add_argument("--num-tasks", type=int, default=30, help="Number of synthetic tasks (default: 30)")
    parser.add_argument("--num-pairs", type=int, default=6000, help="Target number of applicant-task pairs (default: 6000)")
    parser.add_argument("--scenario", type=str, choices=["scenario_a", "scenario_b"], default="scenario_a", help="Simulation scenario (scenario_a: compensatory, scenario_b: strict bottleneck)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save generated datasets")

    args = parser.parse_args()

    results = generate_task_specific_dataset(
        num_applicants=args.num_applicants,
        num_tasks=args.num_tasks,
        num_pairs=args.num_pairs,
        scenario=args.scenario,
        seed=args.seed,
        output_dir=Path(args.output_dir) if args.output_dir else None
    )

    validation = validate_datasets(results)

    print("\n" + "=" * 60)
    print("DATASET VALIDATION SUMMARY")
    print("=" * 60)
    for name, passed, detail in validation["checks"]:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status:6s} | {name:<65} | {detail}")
    print("=" * 60)
    print(f"Overall Validation Result: {'ALL CHECKS PASSED' if validation['all_passed'] else 'VALIDATION ISSUES DETECTED'}")
    print(f"Total Applicants:   {validation['total_applicants']}")
    print(f"Total Tasks:        {validation['total_tasks']}")
    print(f"Total Pairs:        {validation['total_pairs']}")
    print(f"Eligible Pairs:     {validation['eligible_pairs']}")
    print(f"Ineligible Pairs:   {validation['ineligible_pairs']}")
    print(f"Training Class 1:   {validation['positive_count']} ({validation['positive_rate']:.1%})")
    print(f"Training Class 0:   {validation['negative_count']} ({1.0 - validation['positive_rate']:.1%})")
    print("=" * 60)

    if not validation["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
