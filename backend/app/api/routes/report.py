"""Report generation routes -- PDF and Word export."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.report_service import generate_trade_report_docx, generate_trade_report_pdf
from app.models.database import get_db
from app.models.schemas_db import Country, TradeRecord

router = APIRouter()


@router.get("/export/pdf")
def export_pdf(db: Session = Depends(get_db)):
    """Export trade analysis report as PDF."""
    # Get summary data
    latest_year = db.query(func.max(TradeRecord.year)).scalar() or 2025
    total = db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0)).filter(TradeRecord.year == latest_year).scalar()
    prev_total = db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0)).filter(TradeRecord.year == latest_year - 1).scalar()
    yoy = ((total - prev_total) / prev_total * 100) if prev_total else 0
    partners = db.query(func.count(func.distinct(TradeRecord.partner))).filter(TradeRecord.year == latest_year).scalar()
    categories = db.query(func.count(func.distinct(TradeRecord.hs_section))).filter(TradeRecord.year == latest_year).scalar()

    summary_data = {
        'total_trade_value': total,
        'yoy_growth': yoy,
        'partner_count': partners,
        'product_categories': categories,
    }

    # Get trade trend data
    trend_rows = (
        db.query(TradeRecord.year, func.sum(TradeRecord.trade_value_usd))
        .filter(TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.year)
        .order_by(TradeRecord.year)
        .all()
    )
    trade_data = [{'date': str(r[0]), 'value': r[1], 'growth': 0} for r in trend_rows[-12:]]

    # Get country data
    country_rows = (
        db.query(TradeRecord.partner, func.sum(TradeRecord.trade_value_usd).label('total'))
        .filter(TradeRecord.year == latest_year, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .limit(5)
        .all()
    )
    country_names = {c.code: c.name_cn for c in db.query(Country).all()}
    country_data = [
        {'name': country_names.get(r[0], r[0]), 'value': r[1], 'share': r[1] / total * 100 if total else 0}
        for r in country_rows
    ]

    # Generate PDF
    pdf_bytes = generate_trade_report_pdf(
        title=f"中国-东盟贸易分析报告 ({latest_year}年)",
        summary_data=summary_data,
        trade_data=trade_data,
        country_data=country_data,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=trade_report_{latest_year}.pdf"},
    )


@router.get("/export/docx")
def export_docx(db: Session = Depends(get_db)):
    """Export trade analysis report as Word document."""
    # Get summary data
    latest_year = db.query(func.max(TradeRecord.year)).scalar() or 2025
    total = db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0)).filter(TradeRecord.year == latest_year).scalar()
    prev_total = db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0)).filter(TradeRecord.year == latest_year - 1).scalar()
    yoy = ((total - prev_total) / prev_total * 100) if prev_total else 0
    partners = db.query(func.count(func.distinct(TradeRecord.partner))).filter(TradeRecord.year == latest_year).scalar()
    categories = db.query(func.count(func.distinct(TradeRecord.hs_section))).filter(TradeRecord.year == latest_year).scalar()

    summary_data = {
        'total_trade_value': total,
        'yoy_growth': yoy,
        'partner_count': partners,
        'product_categories': categories,
    }

    # Get trade trend data
    trend_rows = (
        db.query(TradeRecord.year, func.sum(TradeRecord.trade_value_usd))
        .filter(TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.year)
        .order_by(TradeRecord.year)
        .all()
    )
    trade_data = [{'date': str(r[0]), 'value': r[1], 'growth': 0} for r in trend_rows[-12:]]

    # Get country data
    country_rows = (
        db.query(TradeRecord.partner, func.sum(TradeRecord.trade_value_usd).label('total'))
        .filter(TradeRecord.year == latest_year, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .limit(5)
        .all()
    )
    country_names = {c.code: c.name_cn for c in db.query(Country).all()}
    country_data = [
        {'name': country_names.get(r[0], r[0]), 'value': r[1], 'share': r[1] / total * 100 if total else 0}
        for r in country_rows
    ]

    # Generate Word document
    docx_bytes = generate_trade_report_docx(
        title=f"中国-东盟贸易分析报告 ({latest_year}年)",
        summary_data=summary_data,
        trade_data=trade_data,
        country_data=country_data,
    )

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=trade_report_{latest_year}.docx"},
    )


import io
