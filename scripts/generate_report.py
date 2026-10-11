
#!/usr/bin/env python3
"""Generate a French, human-readable report from Checkov JSON results."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = PROJECT_ROOT / "checkov-results.json"
DEFAULT_MAPPING = PROJECT_ROOT / "policies" / "control-mapping.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "compliance-report.md"

PRIORITY_LABELS = {
    "high": "Élevée — priorité définie par le projet",
    "medium": "Moyenne — priorité définie par le projet",
    "low": "Faible — priorité définie par le projet",
}


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file and ensure its top-level value is an object."""
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"Fichier introuvable : {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON invalide dans {path}, ligne {exc.lineno}, "
            f"colonne {exc.colno} : {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"Le fichier doit contenir un objet JSON : {path}")

    return data


def as_list(value: Any) -> list[dict[str, Any]]:
    """Return a list containing only dictionary entries."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def as_text(value: Any, default: str = "Non renseigné") -> str:
    """Convert an optional value to readable text."""
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    if isinstance(value, (str, int, float)):
        return str(value)
    return default


def format_path(value: Any) -> str:
    """Format a Checkov file path relative to the repository."""
    raw = as_text(value, "Fichier non renseigné")
    normalized = raw.replace("\\", "/").lstrip("/")

    if normalized.startswith("./"):
        normalized = normalized[2:]

    # Checkov reports paths relative to the scanned Terraform directory.
    if normalized != "Fichier non renseigné":
        if not normalized.startswith("terraform/"):
            normalized = f"terraform/{normalized}"

    return normalized


def format_lines(value: Any) -> str:
    """Format Checkov's [start, end] line range."""
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    ):
        start, end = value[0], value[1]
        if start == end:
            return f"ligne {start}"
        return f"lignes {start}–{end}"

    return "lignes non renseignées"


def markdown_safe(value: Any) -> str:
    """Avoid accidental Markdown table or line formatting."""
    return as_text(value).replace("|", "\\|").replace("\n", " ")


def get_check_title(
    check: dict[str, Any], mapping: dict[str, Any]
) -> str:
    check_id = as_text(check.get("check_id"), "Identifiant inconnu")
    control = mapping.get(check_id, {})
    if isinstance(control, dict) and control.get("title"):
        return str(control["title"])

    return as_text(
        check.get("short_description"),
        as_text(check.get("check_name"), f"Contrôle {check_id}"),
    )


def render_failed_check(
    check: dict[str, Any], mapping: dict[str, Any], number: int
) -> list[str]:
    check_id = as_text(check.get("check_id"), "Identifiant inconnu")
    control = mapping.get(check_id, {})

    if not isinstance(control, dict):
        control = {}

    title = get_check_title(check, mapping)
    priority = str(control.get("project_priority", "")).lower()
    priority_label = PRIORITY_LABELS.get(
        priority, "À classifier — priorité non définie"
    )

    technical_name = as_text(check.get("check_name"))
    resource = as_text(check.get("resource"))
    file_path = format_path(check.get("file_path"))
    lines = format_lines(check.get("file_line_range"))
    guideline = check.get("guideline")

    explanation = as_text(
        control.get("plain_language"),
        as_text(
            check.get("description"),
            technical_name,
        ),
    )
    risk = as_text(
        control.get("risk"),
        "Le risque doit être évalué par l'équipe responsable.",
    )
    recommendation = as_text(
        control.get("recommendation"),
        "Examiner la documentation du contrôle et corriger la "
        "configuration si nécessaire.",
    )

    iso_status = str(control.get("iso_mapping_status", "not_documented"))
    iso_note = as_text(
        control.get("iso_mapping_note"),
        "Aucune correspondance ISO n'est documentée pour ce contrôle.",
    )

    section = [
        f"### {number}. {title}",
        "",
        f"- **Résultat Checkov :** ÉCHEC (`{check_id}`)",
        f"- **Priorité du projet :** {priority_label}",
        f"- **Ressource :** `{markdown_safe(resource)}`",
        f"- **Fichier :** `{markdown_safe(file_path)}` — {lines}",
        f"- **Contrôle technique :** {markdown_safe(technical_name)}",
        "",
        "**Explication en langage simple**",
        "",
        explanation,
        "",
        "**Risque potentiel**",
        "",
        risk,
        "",
        "**Action recommandée**",
        "",
        recommendation,
        "",
        f"**Correspondance ISO :** {iso_status} — {iso_note}",
    ]

    severity = check.get("severity")
    if severity is not None:
        section.insert(
            3,
            f"- **Sévérité fournie par Checkov :** "
            f"{markdown_safe(severity)}",
        )

    if isinstance(guideline, str) and guideline.startswith("https://"):
        section.extend(["", f"**Documentation technique :** {guideline}"])

    section.append("")
    section.append("---")
    section.append("")
    return section


def render_passed_checks(checks: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Contrôles réussis",
        "",
    ]

    if not checks:
        lines.extend(["Aucun contrôle réussi n'est répertorié.", ""])
        return lines

    for check in checks:
        check_id = as_text(check.get("check_id"), "Identifiant inconnu")
        title = as_text(check.get("check_name"))
        resource = as_text(check.get("resource"))
        file_path = format_path(check.get("file_path"))

        lines.append(
            f"- **{check_id}** — {title} "
            f"(ressource `{markdown_safe(resource)}`, "
            f"fichier `{markdown_safe(file_path)}`)."
        )

    lines.append("")
    return lines


def generate_report(
    input_path: Path,
    mapping_path: Path,
    output_path: Path,
) -> tuple[int, int, Path]:
    data = load_json(input_path)
    mapping_data = load_json(mapping_path)

    controls = mapping_data.get("controls", {})
    if not isinstance(controls, dict):
        raise ValueError(
            "Le fichier de correspondance doit contenir "
            "un objet 'controls'."
        )

    results = data.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("La clé 'results' n'a pas le format attendu.")

    passed = as_list(results.get("passed_checks"))
    failed = as_list(results.get("failed_checks"))
    skipped = as_list(results.get("skipped_checks"))

    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    parsing_errors = summary.get("parsing_errors", 0)
    if not isinstance(parsing_errors, int):
        parsing_errors = len(as_list(results.get("parsing_errors")))

    version = as_text(summary.get("checkov_version"))
    resource_count = as_text(summary.get("resource_count"))

    timestamp = datetime.now().astimezone().strftime("%d/%m/%Y à %H:%M:%S")

    lines = [
        "# Rapport de contrôle de sécurité Cloud",
        "",
        f"- **Date de génération :** {timestamp}",
        f"- **Fichier source :** `{input_path.name}`",
        f"- **Version de Checkov :** {version}",
        f"- **Ressources analysées :** {resource_count}",
        "",
        "> **Périmètre :** ce rapport résume les résultats fournis par "
        "Checkov et les explique en langage simple. Il ne constitue ni "
        "un audit complet ni une certification ISO 27017 ou ISO 27018.",
        "",
        "## Résumé exécutif",
        "",
        f"- **Contrôles réussis :** {len(passed)}",
        f"- **Contrôles échoués :** {len(failed)}",
        f"- **Contrôles ignorés :** {len(skipped)}",
        f"- **Erreurs d'analyse signalées :** {parsing_errors}",
        "",
    ]

    if parsing_errors:
        lines.extend(
            [
                "⚠️ **Analyse potentiellement incomplète.** "
                "Checkov signale des erreurs d'analyse. Vérifiez les "
                "logs avant de tirer une conclusion.",
                "",
            ]
        )

    if failed:
        lines.extend(
            [
                "### Conclusion",
                "",
                f"Checkov a détecté **{len(failed)} contrôle(s) en échec**. "
                "Les configurations concernées doivent être examinées. "
                "Ce résultat ne signifie pas nécessairement que chaque "
                "échec correspond à une violation d'une clause ISO.",
                "",
                "## Points à examiner",
                "",
            ]
        )

        for number, check in enumerate(failed, start=1):
            lines.extend(render_failed_check(check, controls, number))
    else:
        lines.extend(
            [
                "### Conclusion",
                "",
                "Aucun échec n'est répertorié parmi les contrôles exécutés. "
                "Cela ne prouve pas la conformité complète de "
                "l'infrastructure : seuls les contrôles effectivement "
                "exécutés sont couverts par ce résultat.",
                "",
            ]
        )

    lines.extend(render_passed_checks(passed))

    if skipped:
        lines.extend(
            [
                "## Contrôles ignorés",
                "",
                "Des contrôles ont été ignorés. Leur absence de résultat "
                "ne doit pas être interprétée comme une réussite.",
                "",
            ]
        )
        for check in skipped:
            check_id = as_text(check.get("check_id"))
            title = as_text(check.get("check_name"))
            lines.append(f"- `{check_id}` — {title}")
        lines.append("")

    lines.extend(
        [
            "## Limites et interprétation",
            "",
            "- Les résultats techniques proviennent du JSON Checkov.",
            "- Les priorités indiquées sont définies par le projet ; "
            "elles ne sont pas des niveaux de sévérité officiels "
            "de Checkov.",
            "- Les correspondances ISO sont affichées selon le catalogue "
            "fourni. Un statut `to_validate` signifie que la référence "
            "doit encore être vérifiée.",
            "- Une règle réussie ne démontre pas, à elle seule, "
            "la conformité complète d'un système.",
            "",
            "---",
            "",
            "Rapport généré automatiquement par "
            "`scripts/generate_report.py`.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return len(passed), len(failed), output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Génère un rapport Markdown en français depuis "
            "les résultats JSON de Checkov."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Chemin du JSON Checkov.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="Chemin du catalogue explicatif.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Chemin du rapport Markdown à générer.",
    )
    args = parser.parse_args()

    try:
        passed, failed, output_path = generate_report(
            args.input, args.mapping, args.output
        )
    except (ValueError, OSError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2

    print(f"Rapport généré : {output_path}")
    print(f"Contrôles réussis : {passed}")
    print(f"Contrôles échoués : {failed}")
    print(
        "Note : le code de sortie indique le succès de génération "
        "du rapport, pas la conformité du scan."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
