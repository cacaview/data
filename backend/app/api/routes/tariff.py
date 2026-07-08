"""Tariff calculation routes -- duty computation and HS code lookup."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas_db import TradeRecord, Country, Product, TariffRule
from app.models.schemas import TariffRequest, TariffResult

router = APIRouter()


@router.post("/calculate", response_model=TariffResult)
def calculate_tariff(req: TariffRequest, db: Session = Depends(get_db)):
    """Calculate import duties under MFN, RCEP, and FTA schemes.

    Looks up the best available rate and computes savings.
    """
    # Look up tariff rule for HS code + origin country
    rule = (
        db.query(TariffRule)
        .filter(
            TariffRule.hs_code == req.hs_code,
            TariffRule.partner_country == req.origin_country,
        )
        .first()
    )

    # Product name lookup
    product = db.query(Product).filter(Product.hs_code == req.hs_code).first()
    product_name = (
        product.hs_name_cn if product and product.hs_name_cn else req.hs_code
    )

    # Country names
    origin = db.query(Country).filter(Country.code == req.origin_country).first()
    target = db.query(Country).filter(Country.code == req.target_country).first()
    origin_name = origin.name_cn if origin else req.origin_country
    target_name = target.name_cn if target else req.target_country

    if rule:
        mfn_rate = rule.mfn_rate or 0.0
        rcep_rate = rule.rcep_rate if rule.rcep_rate is not None else mfn_rate
        fta_rate = rule.fta_rate
        rule_of_origin = rule.rule_of_origin or ""
    else:
        # Fallback: default rates when no rule found in DB
        mfn_rate = 10.0
        rcep_rate = 5.0
        fta_rate = None
        rule_of_origin = "无原产地规则数据，请查询海关最新规定"

    # Determine best rate
    candidates = [("RCEP", rcep_rate)]
    if fta_rate is not None:
        candidates.append(("FTA", fta_rate))
    candidates.append(("MFN", mfn_rate))

    best_scheme, best_rate = min(candidates, key=lambda x: x[1])

    # Compute duties
    duty_mfn = req.value_usd * mfn_rate / 100
    duty_best = req.value_usd * best_rate / 100
    savings = duty_mfn - duty_best
    savings_pct = (savings / duty_mfn * 100) if duty_mfn > 0 else 0.0

    # Cumulation rule description
    cumulation_rule = (
        "RCEP区域累积规则：可使用15个成员国的原材料和加工增值进行累积，"
        "满足区域价值成分40%或税则归类改变标准"
        if best_scheme == "RCEP"
        else "适用双边FTA原产地规则"
        if best_scheme == "FTA"
        else "无优惠安排，适用最惠国税率"
    )

    return TariffResult(
        hs_code=req.hs_code,
        product_name=product_name,
        origin_country=origin_name,
        target_country=target_name,
        mfn_rate=round(mfn_rate, 2),
        rcep_rate=round(rcep_rate, 2),
        fta_rate=round(fta_rate, 2) if fta_rate is not None else None,
        best_rate=round(best_rate, 2),
        best_scheme=best_scheme,
        value_usd=req.value_usd,
        duty_mfn=round(duty_mfn, 2),
        duty_best=round(duty_best, 2),
        savings=round(savings, 2),
        savings_pct=round(savings_pct, 2),
        rule_of_origin=rule_of_origin,
        cumulation_rule=cumulation_rule,
        # Frontend aliases
        declared_value_usd=req.value_usd,
        applicable_rate=round(best_rate, 2),
        applicable_basis=best_scheme.lower(),
        duty_usd=round(duty_best, 2),
        savings_vs_mfn_usd=round(savings, 2),
    )


@router.get("/common-codes")
def get_common_codes(db: Session = Depends(get_db)):
    """Return commonly used HS codes for the tariff calculator dropdown.

    Joins tariff_rules with products to provide code + name pairs.
    """
    # Get distinct HS codes from tariff rules
    code_rows = (
        db.query(distinct(TariffRule.hs_code))
        .order_by(TariffRule.hs_code)
        .limit(100)
        .all()
    )
    hs_codes = [r[0] for r in code_rows]

    if not hs_codes:
        return []

    # Look up product names
    products = db.query(Product).filter(Product.hs_code.in_(hs_codes)).all()
    name_map = {p.hs_code: (p.hs_name_cn or p.hs_name_en or p.hs_code) for p in products}

    return [
        {"hs_code": code, "code": code, "name": name_map.get(code, code)}
        for code in hs_codes
    ]
