#!/usr/bin/env python3
"""Generate a visual French Cloud Security report from Checkov JSON results.

The report is a summary of the selected Checkov controls only; it does not
constitute an ISO certification or a complete compliance audit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "checkov-results.json"
DEFAULT_MAPPING = PROJECT_ROOT / "policies" / "control-mapping.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "compliance-report.pdf"

# Palette: restrained, high-contrast report design.
NAVY = colors.HexColor("#14213D")
BLUE = colors.HexColor("#2457A7")
TEAL = colors.HexColor("#087E8B")
GREEN = colors.HexColor("#218739")
RED = colors.HexColor("#B42318")
AMBER = colors.HexColor("#9A6700")
INK = colors.HexColor("#202939")
MUTED = colors.HexColor("#5E6A7D")
PALE = colors.HexColor("#F3F6FA")
PALE_BLUE = colors.HexColor("#EAF1FB")
PALE_GREEN = colors.HexColor("#EAF6ED")
PALE_RED = colors.HexColor("#FCEDEC")
PALE_AMBER = colors.HexColor("#FFF5D7")
BORDER = colors.HexColor("#D9E0EA")
WHITE = colors.white

PRIORITY_LABELS = {
    "high": "Élevée (priorité définie par le projet)",
    "medium": "Moyenne (priorité définie par le projet)",
    "low": "Faible (priorité définie par le projet)",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Fichier introuvable : {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON invalide dans {path}, ligne {exc.lineno}, "
            f"colonne {exc.colno} : {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"Le JSON doit contenir un objet : {path}")
    return data


def as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def as_text(value: Any, default: str = "Non renseigné") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() or default
    if isinstance(value, (int, float)):
        return str(value)
    return default


def safe_path(value: Any) -> str:
    raw = as_text(value, "Fichier non renseigné")
    normalized = raw.replace("\\", "/").lstrip("/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized != "Fichier non renseigné" and not normalized.startswith("terraform/"):
        normalized = f"terraform/{normalized}"
    return normalized


def format_lines(value: Any) -> str:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    ):
        start, end = value[0], value[1]
        return f"ligne {start}" if start == end else f"lignes {start} à {end}"
    return "Lignes non renseignées"


def ptext(value: Any, default: str = "Non renseigné") -> str:
    """Escape dynamic text for ReportLab Paragraph's XML-like markup."""
    return escape(as_text(value, default)).replace("\n", "<br/>")


def get_control(check: dict[str, Any], controls: dict[str, Any]) -> dict[str, Any]:
    entry = controls.get(as_text(check.get("check_id"), ""), {})
    return entry if isinstance(entry, dict) else {}


def title_for(check: dict[str, Any], control: dict[str, Any]) -> str:
    return as_text(
        control.get("title"),
        as_text(check.get("short_description"), as_text(check.get("check_name"), "Contrôle inconnu")),
    )


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=19, leading=23, textColor=WHITE, alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=13, textColor=colors.HexColor("#E4ECF8"),
        ),
        "h1": ParagraphStyle(
            "SectionHeading", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=14, leading=18, textColor=NAVY, spaceBefore=9, spaceAfter=7,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "FindingHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=NAVY, spaceBefore=4, spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.2,
            leading=10.8, textColor=INK, spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.3,
            leading=10, textColor=MUTED, spaceAfter=2,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.3, leading=9, textColor=MUTED, spaceAfter=2, keepWithNext=True,
        ),
        "card_label": ParagraphStyle(
            "CardLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.1, leading=9, textColor=MUTED, alignment=TA_CENTER,
        ),
        "card_value": ParagraphStyle(
            "CardValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=20, leading=23, textColor=NAVY, alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "Callout", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=9, leading=13, textColor=NAVY,
        ),
        "white_small": ParagraphStyle(
            "WhiteSmall", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=11, textColor=WHITE,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8, leading=11, leftIndent=9, firstLineIndent=-7,
            textColor=INK, spaceAfter=3,
        ),
    }


class ResultBar(Flowable):
    """Compact stacked bar comparing passed, failed, and skipped checks."""

    def __init__(self, passed: int, failed: int, skipped: int, width: float = 170 * mm, height: float = 18 * mm):
        super().__init__()
        self.passed = max(0, passed)
        self.failed = max(0, failed)
        self.skipped = max(0, skipped)
        self.width = width
        self.height = height

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:
        self.width = min(self.width, availWidth)
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        total = self.passed + self.failed + self.skipped
        bar_y = self.height - 8 * mm
        bar_h = 5 * mm
        available_w = self.width
        c.setFillColor(PALE)
        c.roundRect(0, bar_y, available_w, bar_h, 2 * mm, fill=1, stroke=0)
        if total > 0:
            x = 0
            items = [
                (self.passed, GREEN),
                (self.failed, RED),
                (self.skipped, AMBER),
            ]
            for count, color in items:
                w = available_w * count / total
                if count and w > 0:
                    c.setFillColor(color)
                    c.rect(x, bar_y, w, bar_h, fill=1, stroke=0)
                    x += w
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawString(0, 3 * mm, f"Total : {total} contrôle(s)")
        legend = [
            (GREEN, f"Réussis : {self.passed}"),
            (RED, f"Échoués : {self.failed}"),
            (AMBER, f"Ignorés : {self.skipped}"),
        ]
        x = self.width
        for color, label in reversed(legend):
            sw = stringWidth(label, "Helvetica", 7.5) + 13 * mm
            x -= sw
            c.setFillColor(color)
            c.circle(x + 2 * mm, 4 * mm, 1.2 * mm, fill=1, stroke=0)
            c.setFillColor(MUTED)
            c.drawString(x + 5 * mm, 3 * mm, label)
            x -= 2 * mm


def kpi_cards(passed: int, failed: int, skipped: int, parsing_errors: int, width: float) -> Table:
    values = [
        (str(passed), "Contrôles réussis", PALE_GREEN, GREEN),
        (str(failed), "Contrôles échoués", PALE_RED if failed else PALE_GREEN, RED if failed else GREEN),
        (str(skipped), "Contrôles ignorés", PALE_AMBER, AMBER),
        (str(parsing_errors), "Erreurs d'analyse", PALE_RED if parsing_errors else PALE, RED if parsing_errors else NAVY),
    ]
    gap = 3 * mm
    card_width = (width - gap * 3) / 4
    cells = []
    for value, label, bg, fg in values:
        card = Table(
            [[Paragraph(value, ParagraphStyle("KPIValue", fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=fg, alignment=TA_CENTER))],
             [Paragraph(escape(label), ParagraphStyle("KPILabel", fontName="Helvetica-Bold", fontSize=6.9, leading=8.5, textColor=MUTED, alignment=TA_CENTER))]],
            colWidths=[card_width], rowHeights=[10 * mm, 10 * mm],
        )
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        cells.append(card)
    row = []
    for idx, card in enumerate(cells):
        row.append(card)
        if idx < len(cells) - 1:
            row.append("")
    widths = []
    for idx in range(7):
        widths.append(card_width if idx % 2 == 0 else gap)
    table = Table([row], colWidths=widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def field_table(rows: list[tuple[str, str]], width: float, styles: dict[str, ParagraphStyle]) -> Table:
    data = []
    for label, value in rows:
        data.append([
            Paragraph(ptext(label), styles["label"]),
            Paragraph(ptext(value), styles["body"]),
        ])
    table = Table(data, colWidths=[34 * mm, width - 34 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def finding_block(check: dict[str, Any], control: dict[str, Any], index: int, width: float, styles: dict[str, ParagraphStyle]) -> list[Any]:
    check_id = as_text(check.get("check_id"), "Identifiant inconnu")
    title = title_for(check, control)
    resource = as_text(check.get("resource"))
    file_path = safe_path(check.get("file_path"))
    lines = format_lines(check.get("file_line_range"))
    technical_name = as_text(check.get("check_name"))
    priority = PRIORITY_LABELS.get(str(control.get("project_priority", "")).lower(), "Non définie")
    explanation = as_text(control.get("plain_language"), as_text(check.get("description"), technical_name))
    risk = as_text(control.get("risk"), "Le risque doit être évalué par l'équipe responsable.")
    recommendation = as_text(control.get("recommendation"), "Examiner le contrôle et corriger la configuration si nécessaire.")
    iso_status = as_text(control.get("iso_mapping_status"), "not_documented")
    iso_status_label = {
        "to_validate": "À vérifier",
        "validated": "Vérifiée",
        "not_documented": "Non documentée",
        "not_applicable": "Non applicable",
    }.get(iso_status.lower(), iso_status)
    iso_note = as_text(control.get("iso_mapping_note"), "Aucune correspondance ISO documentée pour ce contrôle.")

    story: list[Any] = []
    story.append(Paragraph(f"{index}. {ptext(title)}", styles["h2"]))
    meta_rows = [
        ("Résultat", f"ÉCHEC - {check_id}"),
        ("Priorité du projet", priority),
        ("Ressource", resource),
        ("Fichier", f"{file_path} ({lines})"),
        ("Contrôle technique", technical_name),
    ]
    story.append(field_table(meta_rows, width, styles))
    story.append(Spacer(1, 3 * mm))
    for heading, content in [
        ("Explication en langage simple", explanation),
        ("Risque potentiel", risk),
        ("Action recommandée", recommendation),
    ]:
        story.append(Paragraph(heading, styles["label"]))
        story.append(Paragraph(ptext(content), styles["body"]))
    story.append(Paragraph("Correspondance ISO", styles["label"]))
    story.append(Paragraph(f"{ptext(iso_status_label)} - {ptext(iso_note)}", styles["body"]))
    guideline = check.get("guideline")
    if isinstance(guideline, str) and guideline.startswith("https://"):
        safe_url = escape(guideline, {'"': '&quot;'})
        story.append(Paragraph(f'<link href="{safe_url}" color="#2457A7">Documentation technique du contrôle</link>', styles["small"]))
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceBefore=1, spaceAfter=4))
    story.append(Spacer(1, 1 * mm))
    return story


def on_page(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    page_w, page_h = A4
    if doc.page > 1:
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, page_h - 14 * mm, page_w - 18 * mm, page_h - 14 * mm)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, page_h - 11 * mm, "CLOUD SECURITY & COMPLIANCE")
    canvas.setStrokeColor(BORDER)
    canvas.line(18 * mm, 13 * mm, page_w - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8.5 * mm, "Rapport automatisé - contrôles sélectionnés uniquement")
    canvas.drawRightString(page_w - 18 * mm, 8.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(input_path: Path, mapping_path: Path, output_path: Path) -> tuple[int, int, Path]:
    raw = load_json(input_path)
    mapping_data = load_json(mapping_path)
    controls = mapping_data.get("controls", {})
    if not isinstance(controls, dict):
        raise ValueError("Le fichier de correspondance doit contenir un objet 'controls'.")
    results = raw.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("La clé 'results' du JSON Checkov n'a pas le format attendu.")

    passed = as_list(results.get("passed_checks"))
    failed = as_list(results.get("failed_checks"))
    skipped = as_list(results.get("skipped_checks"))
    summary = raw.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    parsing_errors = summary.get("parsing_errors", 0)
    if not isinstance(parsing_errors, int):
        parsing_errors = len(as_list(results.get("parsing_errors")))
    resource_count = as_text(summary.get("resource_count"))
    version = as_text(summary.get("checkov_version"))
    now = datetime.now().astimezone().strftime("%d/%m/%Y à %H:%M:%S")

    # During a pull_request event, GITHUB_REF_NAME is usually "<number>/merge".
    # Prefer the source and target branch variables for readable report metadata.
    branch = (
        os.environ.get("GITHUB_HEAD_REF")
        or os.environ.get("GITHUB_REF_NAME", "Local")
    )
    target_branch = os.environ.get("GITHUB_BASE_REF") or "—"

    pr_number = ""
    source_commit = ""
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if event_path:
        try:
            event_payload = json.loads(
                Path(event_path).read_text(encoding="utf-8")
            )
            pull_request = event_payload.get("pull_request", {})

            if isinstance(pull_request, dict):
                pr_number = str(
                    pull_request.get("number")
                    or event_payload.get("number")
                    or ""
                )
                head = pull_request.get("head", {})

                if isinstance(head, dict):
                    source_commit = str(head.get("sha") or "")

        except (OSError, json.JSONDecodeError):
            # Fall back to the standard GitHub Actions variables if payload
            # metadata is unavailable or malformed.
            pass

    commit_value = source_commit or os.environ.get("GITHUB_SHA", "")
    commit = commit_value[:12] or "Exécution locale"
    run_id = os.environ.get("GITHUB_RUN_ID", "Non disponible localement")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=19 * mm,
        title="Rapport de contrôle de sécurité Cloud",
        author="Policy as Code - Checkov",
        subject="Synthèse automatisée de contrôles de sécurité Cloud",
    )
    width = A4[0] - 36 * mm
    story: list[Any] = []

    title_box = Table(
        [[[
            Paragraph("RAPPORT DE CONTRÔLE<br/>DE SÉCURITÉ CLOUD", styles["title"]),
            Spacer(1, 2 * mm),
            Paragraph("Policy as Code | Terraform | Analyse de sécurité dans le contexte ISO 27017 / ISO 27018", styles["subtitle"]),
        ]]],
        colWidths=[width],
    )
    title_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.5, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 7 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7 * mm),
    ]))
    story.append(title_box)
    story.append(Spacer(1, 5 * mm))

    overall_failed = bool(failed) or bool(parsing_errors)
    verdict_text = (
        "VIOLATIONS DÉTECTÉES - correction requise"
        if overall_failed
        else "Aucun échec détecté parmi les contrôles exécutés"
    )
    verdict_bg = PALE_RED if overall_failed else PALE_GREEN
    verdict_fg = RED if overall_failed else GREEN
    verdict = Table([[Paragraph(ptext(verdict_text), ParagraphStyle(
        "Verdict", fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=verdict_fg, alignment=TA_CENTER,
    ))]], colWidths=[width])
    verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), verdict_bg),
        ("BOX", (0, 0), (-1, -1), 0.7, verdict_fg),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    story.append(verdict)
    story.append(Spacer(1, 5 * mm))

    metadata = [
        ("Date de génération", now),
        ("Version de Checkov", version),
        ("Ressources analysées", resource_count),
        ("Branche source", branch),
        ("Branche cible", target_branch),
        ("Pull Request", f"#{pr_number}" if pr_number else "Non applicable"),
        ("Commit source analysé", commit),
        ("Identifiant du run GitHub", run_id),
    ]
    story.append(field_table(metadata, width, styles))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("1. Résumé exécutif", styles["h1"]))
    story.append(kpi_cards(len(passed), len(failed), len(skipped), parsing_errors, width))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Répartition des résultats", styles["h2"]))
    story.append(ResultBar(len(passed), len(failed), len(skipped), width=width))
    story.append(Spacer(1, 2 * mm))

    if parsing_errors:
        warning = Table([[Paragraph(
            "Attention : Checkov signale des erreurs d'analyse. Le résultat peut être incomplet et doit être examiné.",
            styles["body"],
        )]], colWidths=[width])
        warning.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE_AMBER),
            ("BOX", (0, 0), (-1, -1), 0.7, AMBER),
            ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]))
        story.append(warning)
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Interprétation", styles["h2"]))
    if failed:
        intro = f"Checkov a signalé {len(failed)} contrôle(s) en échec parmi les contrôles sélectionnés. Consultez les fiches suivantes pour comprendre le problème et les mesures proposées. Un échec technique ne signifie pas automatiquement qu'une clause ISO précise est violée."
    elif parsing_errors:
        intro = "Aucun contrôle échoué n'est répertorié, mais des erreurs d'analyse ont été signalées. Il n'est pas possible de conclure que l'analyse est complète."
    else:
        intro = "Aucun échec n'est répertorié parmi les contrôles exécutés. Ce résultat ne prouve pas la conformité complète de l'infrastructure ni sa certification ISO."
    story.append(Paragraph(ptext(intro), styles["body"]))

    if failed:
        story.append(Paragraph("2. Points à examiner", styles["h1"]))
        for index, check in enumerate(failed, start=1):
            control = get_control(check, controls)
            # Keep the heading and compact metadata together where possible.
            story.extend(finding_block(check, control, index, width, styles))

    story.append(Paragraph("Contrôles réussis", styles["h1"]))
    if passed:
        for check in passed:
            check_id = as_text(check.get("check_id"), "Identifiant inconnu")
            technical_name = as_text(check.get("check_name"))
            resource = as_text(check.get("resource"))
            path = safe_path(check.get("file_path"))
            story.append(Paragraph(
                f"<font color='{GREEN.hexval()}'><b>[RÉUSSI] {ptext(check_id)}</b></font> - "
                f"{ptext(technical_name)}<br/><font color='{MUTED.hexval()}' size='7'>"
                f"Ressource : {ptext(resource)} | Fichier : {ptext(path)}</font>", styles["body"]
            ))
    else:
        story.append(Paragraph("Aucun contrôle réussi n'est répertorié.", styles["body"]))

    if skipped:
        story.append(Paragraph("Contrôles ignorés", styles["h1"]))
        story.append(Paragraph(
            "Un contrôle ignoré ne doit pas être interprété comme une réussite.", styles["body"]
        ))
        for check in skipped:
            story.append(Paragraph(
                f"- {ptext(check.get('check_id'))} - {ptext(check.get('check_name'))}", styles["bullet"]
            ))

    story.append(Paragraph("3. Périmètre, conformité et limites", styles["h1"]))
    limitations = [
        "Ce rapport couvre uniquement les contrôles sélectionnés et les résultats analysés par Checkov.",
        "Les priorités sont définies par le projet ; elles ne sont pas des niveaux de sévérité officiels de Checkov.",
        "Une correspondance ISO marquée 'to_validate' reste à vérifier. L'absence d'échec ne prouve ni la conformité complète ni une certification ISO.",
    ]
    for item in limitations:
        story.append(Paragraph(f"- {ptext(item)}", styles["bullet"]))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return len(passed), len(failed), output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère un rapport PDF visuel en français depuis les résultats JSON de Checkov.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Chemin du JSON Checkov.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING, help="Chemin du catalogue explicatif.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Chemin du PDF à générer.")
    args = parser.parse_args()
    try:
        passed, failed, output = generate_pdf(args.input, args.mapping, args.output)
    except (ValueError, OSError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2
    print(f"Rapport PDF généré : {output}")
    print(f"Contrôles réussis : {passed}")
    print(f"Contrôles échoués : {failed}")
    print("Le code de sortie indique le succès de génération du PDF, pas la conformité du scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
