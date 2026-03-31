from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
import os
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

from app.db.database import get_db
from app.core.security import get_current_user
from app.services.report_service import get_simple_report, get_detailed_report

from app.repositories.energy_repository import (
    get_hourly_consumption_today,
    get_daily_consumption_month_comparison,
    get_energy_summary_by_room,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


router = APIRouter(prefix="/reports", tags=["Reports"])


# =====================================================
# 🎨 THEME
# =====================================================

# ReportLab colors (PDF)
THEME_BLUE = colors.HexColor("#113d9e")
THEME_ACCENT = colors.HexColor("#eeaa55")
TEXT_DARK = colors.HexColor("#1f2937")
TEXT_MUTED = colors.HexColor("#6b7280")
BORDER_SOFT = colors.HexColor("#d6dbe6")
BG_SOFT = colors.HexColor("#f5f7fb")
BG_CARD = colors.white

# Matplotlib colors (CHARTS) — MUST be str/tuple, not ReportLab Color
MPL_THEME_BLUE = "#113d9e"
MPL_THEME_ACCENT = "#eeaa55"
MPL_TEXT_DARK = "#1f2937"
MPL_TEXT_MUTED = "#6b7280"
MPL_BORDER_SOFT = "#d6dbe6"

# caminho do logo
LOGO_PATH = r"C:\Users\tomas\countlight-project\backend\app\static\images\logo_neon.png"
LOGO_FALLBACKS = [
    r"C:\Users\tomas\countlight-project\backend\app\static\images\logo_neon.jpg",
    r"C:\Users\tomas\countlight-project\backend\app\static\images\logo_neon.jpeg",
]


def _find_logo_path() -> str | None:
    if os.path.exists(LOGO_PATH):
        return LOGO_PATH
    for p in LOGO_FALLBACKS:
        if os.path.exists(p):
            return p
    return None


def build_styles():
    base = getSampleStyleSheet()

    base["Normal"].fontName = "Helvetica"
    base["Normal"].fontSize = 10
    base["Normal"].leading = 14
    base["Normal"].textColor = TEXT_DARK

    base.add(
        ParagraphStyle(
            name="TitleEco",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=THEME_BLUE,
            alignment=TA_LEFT,
            spaceAfter=8,
        )
    )

    base.add(
        ParagraphStyle(
            name="H2Eco",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=THEME_BLUE,
            spaceBefore=8,
            spaceAfter=6,
        )
    )

    base.add(
        ParagraphStyle(
            name="Muted",
            parent=base["Normal"],
            textColor=TEXT_MUTED,
            fontSize=9.5,
            leading=13,
        )
    )

    return base


# =====================================================
# 🧱 PDF LAYOUT HELPERS
# =====================================================

def header_footer(canvas, doc):
    canvas.saveState()

    # header bar
    canvas.setFillColor(THEME_BLUE)
    canvas.rect(0, A4[1] - 22 * mm, A4[0], 22 * mm, fill=1, stroke=0)

    # logo
    logo_path = _find_logo_path()
    if logo_path:
        try:
            canvas.drawImage(
                logo_path,
                x=12 * mm,
                y=A4[1] - 20 * mm,
                width=28 * mm,
                height=16 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # title in header
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(45 * mm, A4[1] - 14.5 * mm, "CountLight • Relatório de Energia")

    # accent line
    canvas.setFillColor(THEME_ACCENT)
    canvas.rect(0, A4[1] - 22.7 * mm, A4[0], 1.7 * mm, fill=1, stroke=0)

    # footer
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(12 * mm, 10 * mm, f"Gerado em {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.drawRightString(A4[0] - 12 * mm, 10 * mm, f"Página {doc.page}")

    canvas.restoreState()


def section_box(title: str, styles):
    t = Table([[Paragraph(title, styles["H2Eco"])]], colWidths=[170 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BG_SOFT),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t


def create_kpi_card(label: str, value: str, chip_color=THEME_BLUE, trend: str | None = None):
    chip = Table([[""]], colWidths=[6], rowHeights=[34])
    chip.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), chip_color)]))

    label_p = Paragraph(
        label,
        ParagraphStyle("tmpLabel", fontName="Helvetica", fontSize=9, textColor=TEXT_MUTED),
    )
    value_p = Paragraph(
        value,
        ParagraphStyle("tmpValue", fontName="Helvetica-Bold", fontSize=16, textColor=TEXT_DARK),
    )
    trend_p = Paragraph(
        trend or "",
        ParagraphStyle("tmpTrend", fontName="Helvetica-Bold", fontSize=9, textColor=chip_color, alignment=TA_RIGHT),
    )

    inner = Table([[label_p, trend_p], [value_p, ""]], colWidths=[120, 40])
    inner.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("SPAN", (1, 1), (1, 1)),
            ]
        )
    )

    card = Table([[chip, inner]], colWidths=[10, 160], rowHeights=[40])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return card


def cards_row(cards):
    row = Table([cards], colWidths=[180] * len(cards))
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return row


# =====================================================
# 📄 PAGES
# =====================================================

def build_page_summary(elements, report, styles, report_type, start, end):
    elements.append(Spacer(1, 18 * mm))
    elements.append(Paragraph("Resumo", styles["TitleEco"]))
    elements.append(Paragraph(f"Período: <b>{start}</b> a <b>{end}</b>", styles["Muted"]))
    elements.append(Spacer(1, 8))

    elements.append(HRFlowable(width="100%", thickness=0.6, color=BORDER_SOFT))
    elements.append(Spacer(1, 10))

    if "total_kwh" in report:
        consumo = report.get("total_kwh", 0)
        custo = report.get("cost", 0)
        variacao = report.get("variation", 0)

        improved = variacao < 0
        var_color = colors.HexColor("#16a34a") if improved else colors.HexColor("#dc2626")
        var_sign = "↓" if improved else "↑"

        kpi_cards = [
            create_kpi_card("Consumo", f"{consumo} kWh", chip_color=THEME_BLUE),
            create_kpi_card("Custo", f"{custo} €", chip_color=THEME_ACCENT),
            create_kpi_card("Variação", f"{variacao}%", chip_color=var_color, trend=var_sign),
        ]
        elements.append(cards_row(kpi_cards))
        elements.append(Spacer(1, 12))

        insight = (
            f"O consumo <b>{'diminuiu' if improved else 'aumentou'}</b> "
            f"<b>{abs(variacao)}%</b> face ao período anterior."
        )
        elements.append(section_box("Insight", styles))
        insight_tbl = Table([[Paragraph(insight, styles["Normal"])]], colWidths=[170 * mm])
        insight_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(insight_tbl)

    else:
        kpis = report.get("kpis", {})
        comp = report.get("comparisons", {})

        kpi_cards = [
            create_kpi_card("Consumo hoje", f"{kpis.get('today', 0)} kWh", chip_color=THEME_BLUE),
            create_kpi_card("Consumo mês", f"{kpis.get('month', 0)} kWh", chip_color=THEME_ACCENT),
            create_kpi_card("Custo mensal", f"{kpis.get('cost', 0)} €", chip_color=THEME_BLUE),
        ]
        elements.append(cards_row(kpi_cards))
        elements.append(Spacer(1, 12))

        elements.append(section_box("Comparações", styles))
        comp_table = Table(
            [
                ["Vs ontem", f"{comp.get('vs_yesterday', 0)}%"],
                ["Vs mês", f"{comp.get('vs_month', 0)}%"],
            ],
            colWidths=[80 * mm, 90 * mm],
        )
        comp_table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                    ("BACKGROUND", (0, 0), (-1, 0), BG_SOFT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), THEME_BLUE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, BORDER_SOFT),
                ]
            )
        )
        elements.append(comp_table)
        elements.append(Spacer(1, 12))

        elements.append(section_box("Insight", styles))
        insight_txt = report.get("insight", "Sem dados")
        insight_table = Table([[Paragraph(insight_txt, styles["Normal"])]], colWidths=[170 * mm])
        insight_table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(insight_table)


def build_page_breakdown(elements, report, styles):
    elements.append(Spacer(1, 18 * mm))
    elements.append(Paragraph("Distribuição de Consumo", styles["TitleEco"]))
    elements.append(Paragraph("Detalhe por divisões e equipamentos.", styles["Muted"]))
    elements.append(Spacer(1, 10))

    def _list_box(title, items):
        elements.append(section_box(title, styles))
        rows = []
        for it in items:
            rows.append(
                [
                    Paragraph(str(it.get("label", "N/A")), styles["Normal"]),
                    Paragraph(
                        f"{it.get('value', 0)} kWh",
                        ParagraphStyle("v", parent=styles["Normal"], alignment=TA_RIGHT),
                    ),
                ]
            )

        if not rows:
            rows = [[Paragraph("Sem dados", styles["Muted"]), Paragraph("-", styles["Muted"])]]

        t = Table(rows, colWidths=[120 * mm, 50 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_SOFT),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 10))

    _list_box("Divisões", report.get("rooms", []))
    _list_box("Equipamentos", report.get("devices", []))

    medals = ["🥇", "🥈", "🥉"]

    def _top_box(title, items):
        elements.append(section_box(title, styles))
        rows = []
        for i, it in enumerate(items or []):
            medal = medals[i] if i < 3 else "•"
            rows.append(
                [
                    Paragraph(f"{medal} {it.get('label', 'N/A')}", styles["Normal"]),
                    Paragraph(
                        f"{it.get('percentage', 0)}%",
                        ParagraphStyle("p", parent=styles["Normal"], alignment=TA_RIGHT),
                    ),
                ]
            )

        if not rows:
            rows = [[Paragraph("Sem dados", styles["Muted"]), Paragraph("-", styles["Muted"])]]

        t = Table(rows, colWidths=[120 * mm, 50 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_SOFT),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 10))

    _top_box("Top Divisões", report.get("top_rooms", []))
    _top_box("Top Equipamentos", report.get("top_devices", []))


def build_page_analysis(elements, report, styles):
    elements.append(Spacer(1, 18 * mm))
    elements.append(Paragraph("Análise Inteligente", styles["TitleEco"]))
    elements.append(Paragraph("Picos e custos estimados.", styles["Muted"]))
    elements.append(Spacer(1, 10))

    peaks = report.get("peaks", {})
    costs = report.get("costs", {})

    left = Table(
        [
            [Paragraph("Picos de Consumo", styles["H2Eco"])],
            [Paragraph(f"Pico: <b>{peaks.get('value', 0)} kW</b>", styles["Normal"])],
            [Paragraph(f"Hora: <b>{peaks.get('hour', '--')}</b>", styles["Normal"])],
        ],
        colWidths=[83 * mm],
    )
    left.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                ("BACKGROUND", (0, 0), (-1, 0), BG_SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    right = Table(
        [
            [Paragraph("Custos", styles["H2Eco"])],
            [Paragraph(f"Atual: <b>{costs.get('current', 0)} €</b>", styles["Normal"])],
            [Paragraph(f"Estimado: <b>{costs.get('projected', 0)} €</b>", styles["Normal"])],
            [Paragraph(f"Diferença: <b>{costs.get('diff', 0)} €</b>", styles["Normal"])],
        ],
        colWidths=[83 * mm],
    )
    right.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, BORDER_SOFT),
                ("BACKGROUND", (0, 0), (-1, 0), BG_SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    row = Table([[left, right]], colWidths=[85 * mm, 85 * mm])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(row)


def build_page_charts(elements, styles, db, user_id):
    elements.append(Spacer(1, 18 * mm))
    elements.append(Paragraph("Gráficos", styles["TitleEco"]))
    elements.append(Paragraph("Evolução e comparações do consumo.", styles["Muted"]))
    elements.append(Spacer(1, 10))

    hourly = get_hourly_consumption_today(db, user_id)
    hourly_data = hourly.get("data", [])

    if hourly_data and any(d.get("value", 0) > 0 for d in hourly_data):
        chart1 = create_line_chart(hourly_data, "Consumo ao longo do dia")
        elements.append(section_box("Consumo ao longo do dia", styles))
        elements.append(Spacer(1, 6))
        elements.append(Image(chart1, width=170 * mm, height=70 * mm))
        elements.append(Spacer(1, 10))

    comp = get_daily_consumption_month_comparison(db, user_id)
    if comp.get("has_data"):
        chart2 = create_bar_chart(
            comp["labels"],
            comp["current_month"],
            comp["previous_month"],
            "Mês Atual vs Anterior",
        )
        elements.append(section_box("Comparação Mensal", styles))
        elements.append(Spacer(1, 6))
        elements.append(Image(chart2, width=170 * mm, height=70 * mm))
        elements.append(Spacer(1, 10))

    rooms = get_energy_summary_by_room(db, user_id)
    rooms_data = rooms.get("data", [])

    if rooms_data and any(d.get("value", 0) > 0 for d in rooms_data):
        chart3 = create_pie_chart(rooms_data, "Consumo por Divisão")
        elements.append(section_box("Consumo por Divisão", styles))
        elements.append(Spacer(1, 6))
        elements.append(Image(chart3, width=170 * mm, height=70 * mm))


# =====================================================
# 📄 GET — Relatório PDF
# =====================================================

@router.get("/pdf")
def get_report_pdf(
    type: str = Query("house", pattern="^(house|room)$"),
    detail: str = Query("simple", pattern="^(simple|detailed)$"),
    start: str = Query(...),
    end: str = Query(...),
    room_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if type == "room" and not room_id:
        raise HTTPException(status_code=400, detail="room_id é obrigatório")

    user_id = current_user.id_user if hasattr(current_user, "id_user") else current_user

    if detail == "simple":
        report = get_simple_report(
            db=db,
            user_id=user_id,
            start_date=start,
            end_date=end,
            report_type=type,
            room_id=room_id,
        )
    else:
        report = get_detailed_report(
            db=db,
            user_id=user_id,
            start_date=start,
            end_date=end,
            report_type=type,
            room_id=room_id,
        )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=28 * mm,
        bottomMargin=16 * mm,
        title="CountLight - Relatório",
        author="CountLight",
    )

    styles = build_styles()
    elements = []

    build_page_summary(elements, report, styles, type, start, end)

    if detail == "detailed":
        elements.append(PageBreak())
        build_page_breakdown(elements, report, styles)

        elements.append(PageBreak())
        build_page_analysis(elements, report, styles)

        elements.append(PageBreak())
        build_page_charts(elements, styles, db, user_id)

    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio.pdf"},
    )


# =====================================================
# 📊 CHARTS (tema + barras com cores diferentes)
# =====================================================

def _apply_chart_theme(ax):
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_color(MPL_BORDER_SOFT)

    ax.tick_params(colors=MPL_TEXT_MUTED)
    ax.yaxis.label.set_color(MPL_TEXT_DARK)
    ax.xaxis.label.set_color(MPL_TEXT_DARK)
    ax.title.set_color(MPL_THEME_BLUE)

    ax.grid(True, axis="y", linestyle="--", alpha=0.25)


def create_line_chart(data, title):
    buffer = BytesIO()

    labels = [d.get("label") for d in data]
    values = [d.get("value", 0) for d in data]

    fig, ax = plt.subplots(figsize=(7.0, 3.2), dpi=140)
    _apply_chart_theme(ax)

    ax.plot(labels, values, color=MPL_THEME_BLUE, linewidth=2.2)
    ax.fill_between(range(len(values)), values, color=MPL_THEME_BLUE, alpha=0.08)

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("kWh")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")

    fig.tight_layout()
    fig.savefig(buffer, format="png", transparent=False)
    plt.close(fig)

    buffer.seek(0)
    return buffer


def create_bar_chart(labels, current, previous, title):
    buffer = BytesIO()

    current_clean = [v if v is not None else 0 for v in current]
    previous_clean = [v if v is not None else 0 for v in previous]

    x = list(range(len(labels)))
    width = 0.42

    fig, ax = plt.subplots(figsize=(7.0, 3.2), dpi=140)
    _apply_chart_theme(ax)

    ax.bar([i - width / 2 for i in x], current_clean, width=width, label="Atual", color=MPL_THEME_BLUE)
    ax.bar([i + width / 2 for i in x], previous_clean, width=width, label="Anterior", color=MPL_THEME_ACCENT)

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("kWh")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(buffer, format="png", transparent=False)
    plt.close(fig)

    buffer.seek(0)
    return buffer


def create_pie_chart(data, title):
    buffer = BytesIO()

    labels = [d.get("label") for d in data]
    values = [d.get("value", 0) for d in data]

    palette = [
        "#113d9e",
        "#1f57cc",
        "#2d74ff",
        "#5b93ff",
        "#88b0ff",
        "#eeaa55",
        "#f2c07f",
        "#f6d6aa",
    ]
    colors_list = [palette[i % len(palette)] for i in range(len(values))]

    fig, ax = plt.subplots(figsize=(7.0, 3.2), dpi=140)
    ax.set_title(title, fontweight="bold", color=MPL_THEME_BLUE)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors_list,
        textprops={"color": MPL_TEXT_DARK},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
        t.set_fontsize(9)

    ax.axis("equal")

    fig.tight_layout()
    fig.savefig(buffer, format="png", transparent=False)
    plt.close(fig)

    buffer.seek(0)
    return buffer