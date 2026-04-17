"""
Merger module — handles extraction from multiple documents
about the same person and merges into one clean record.
"""
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel

console = Console()


def merge_extractions_programmatically(extractions: list[dict]) -> dict:
    """
    Fast deterministic merge — no LLM needed.
    Used as first pass before optional LLM merge review.

    Priority: real value > null
    Special handling for injuries and instructions (combine them).
    """

    def merge_value(key: str, val_a, val_b):
        """Merge two values for the same field."""

        # Both null — stay null
        if val_a is None and val_b is None:
            return None

        # One is null — take the other
        if val_a is None:
            return val_b
        if val_b is None:
            return val_a

        # Both have values — handle special fields
        if key == "injuries_symptoms":
            # Combine unique injuries
            parts_a = [p.strip() for p in str(val_a).split(",")]
            parts_b = [p.strip() for p in str(val_b).split(",")]
            combined = parts_a + [p for p in parts_b if p not in parts_a]
            return ", ".join(combined)

        if key == "other_special_instructions":
            # Combine unique instructions
            if str(val_a) == str(val_b):
                return val_a
            return f"{val_a} | {val_b}"

        # Boolean fields — true beats false
        if isinstance(val_a, bool) and isinstance(val_b, bool):
            return val_a or val_b

        # String conflict — prefer longer/more complete value
        if isinstance(val_a, str) and isinstance(val_b, str):
            return val_a if len(val_a) >= len(val_b) else val_b

        # Default — keep first value
        return val_a

    def deep_merge(dict_a: dict, dict_b: dict) -> dict:
        """Recursively merge two dicts."""
        merged = {}
        all_keys = set(dict_a.keys()) | set(dict_b.keys())

        for key in all_keys:
            val_a = dict_a.get(key)
            val_b = dict_b.get(key)

            if isinstance(val_a, dict) and isinstance(val_b, dict):
                merged[key] = deep_merge(val_a, val_b)
            else:
                merged[key] = merge_value(key, val_a, val_b)

        return merged

    if not extractions:
        return {}

    if len(extractions) == 1:
        return extractions[0]

    # Merge all extractions progressively
    result = extractions[0]
    for i in range(1, len(extractions)):
        result = deep_merge(result, extractions[i])

    return result


def validate_merged_result(merged: dict) -> dict:
    """Check mandatory fields and set human review flag."""
    mandatory = {
        "surname": merged.get("claimant_details", {}).get("surname"),
        "accident_date": merged.get("tracking_and_administration", {}).get("accident_date"),
    }

    missing = [field for field, value in mandatory.items() if not value]

    merged["requires_human_review"] = len(missing) > 0
    merged["missing_mandatory_fields"] = missing

    return merged


def inject_schedule_data(result: dict, schedule_entry: dict) -> dict:
    """
    Inject clinic schedule data into a merged extraction result.

    Only fills in null/missing fields — does NOT overwrite data
    already extracted from the client's own documents.

    Args:
        result:         Merged extraction dict for one case
        schedule_entry: Dict from clinic_schedule_parser for this client ref

    Returns:
        Updated result dict with schedule data filled in
    """
    if not schedule_entry:
        return result

    def _set_if_null(section: str, field: str, value):
        """Set a field only if currently null/missing."""
        if value is None:
            return
        if section not in result:
            result[section] = {}
        if result[section].get(field) is None:
            result[section][field] = value

    # ── Appointment time → general.appointment_time ──
    _set_if_null("general", "appointment_time", schedule_entry.get("appointment_time"))

    # ── Clinic date → general.medical_date ──
    _set_if_null("general", "medical_date", schedule_entry.get("clinic_date"))

    # ── Expert name → tracking_and_administration.expert_name ──
    _set_if_null(
        "tracking_and_administration", "expert_name",
        schedule_entry.get("expert_name")
    )

    # ── Medical agency → case_instructing_party.agency_name ──
    agency = schedule_entry.get("medical_agency")
    if agency:
        # Use full name if available (e.g. "SPEED" → "Speed Medical")
        agency_full = agency if len(agency) > 5 else agency
        _set_if_null("case_instructing_party", "agency_name", agency_full)

    # ── Medical records required → medical_records.records_required ──
    records_req = schedule_entry.get("medical_records_required")
    if records_req is not None:
        _set_if_null("medical_records", "records_required", records_req)

    # ── Client name → claimant_details (title, forenames, surname) ──
    client_name = schedule_entry.get("client_name")
    if client_name:
        parsed = _parse_client_name(client_name)
        _set_if_null("claimant_details", "title", parsed.get("title"))
        _set_if_null("claimant_details", "forenames", parsed.get("forenames"))
        _set_if_null("claimant_details", "surname", parsed.get("surname"))

        # Infer gender from title
        gender = _infer_gender(parsed.get("title"))
        if gender:
            _set_if_null("claimant_details", "gender", gender)

    console.print(
        f"  [green]✓[/green] Schedule data injected "
        f"(fill-only, no overwrites)"
    )

    return result


def _parse_client_name(full_name: str) -> dict:
    """
    Split a full client name into title, forenames, surname.

    Examples:
        "Mr Carl Hayes"         → {"title": "Mr", "forenames": "Carl", "surname": "Hayes"}
        "Miss Kiera Knight"     → {"title": "Miss", "forenames": "Kiera", "surname": "Knight"}
        "Mrs Rhoneen Schoneville" → {"title": "Mrs", "forenames": "Rhoneen", "surname": "Schoneville"}
        "Paula Rippinghamsmith" → {"title": None, "forenames": "Paula", "surname": "Rippinghamsmith"}
        "Master Joe Murrell"    → {"title": "Master", "forenames": "Joe", "surname": "Murrell"}
    """
    titles = {"mr", "mrs", "ms", "miss", "dr", "master", "prof"}

    parts = full_name.strip().split()
    if not parts:
        return {"title": None, "forenames": None, "surname": None}

    title = None
    if parts[0].lower().rstrip(".") in titles:
        title = parts[0]
        parts = parts[1:]

    if len(parts) == 0:
        return {"title": title, "forenames": None, "surname": None}
    elif len(parts) == 1:
        return {"title": title, "forenames": None, "surname": parts[0]}
    else:
        surname = parts[-1]
        forenames = " ".join(parts[:-1])
        return {"title": title, "forenames": forenames, "surname": surname}


def _infer_gender(title: str) -> str:
    """Infer gender from title. Returns 'Male', 'Female', or None."""
    if not title:
        return None

    lowered = title.lower().rstrip(".")
    if lowered in {"mr", "master"}:
        return "Male"
    elif lowered in {"mrs", "miss", "ms"}:
        return "Female"
    return None


def process_multiple_documents(
    document_paths: list[str],
    extract_fn,
    use_llm_merge: bool = False,
    merge_prompt_fn = None
) -> dict:
    """
    Main entry point for multi-document processing.

    Args:
        document_paths: List of file paths (1, 2, or 3 documents)
        extract_fn: The extract_document function from agent.py
        use_llm_merge: If True, uses Mistral for final merge review

    Returns:
        Single merged JSON dict ready for Excel export
    """
    if not document_paths:
        raise ValueError("No documents provided")

    if len(document_paths) > 5:
        raise ValueError("Maximum 5 documents per case supported")

    extractions = []

    for i, path in enumerate(document_paths, 1):
        console.print(f"\n[cyan]Processing document {i}/{len(document_paths)}:[/cyan] {path}")

        try:
            from utils import read_document
            text = read_document(path)

            console.print(f"  [green]Success:[/green] Text extracted — {len(text)} characters")

            extraction = extract_fn(text)
            extractions.append(extraction)

            console.print(f"  [green]Success:[/green] Data extracted from document {i}")

        except Exception as e:
            console.print(f"  [red]Error:[/red] Failed on document {i}: {e}")
            continue

    if not extractions:
        raise RuntimeError("All documents failed to process")

    # Single document — no merge needed
    if len(extractions) == 1:
        console.print("\n[yellow]Single document — no merge required[/yellow]")
        result = extractions[0]

    else:
        console.print(f"\n[cyan]Merging {len(extractions)} extractions...[/cyan]")

        # Always do fast programmatic merge first
        result = merge_extractions_programmatically(extractions)
        console.print("  [green]Success:[/green] Programmatic merge complete")

        # Optional LLM merge review for complex conflicts
        if use_llm_merge:
            console.print("  [cyan]Running LLM merge review...[/cyan]")
            result = _llm_merge_review(extractions, result, merge_prompt_fn)
            console.print("  [green]Success:[/green] LLM merge review complete")

    # Final validation
    result = validate_merged_result(result)

    # Summary
    _print_merge_summary(extractions, result)

    return result


def _llm_merge_review(extractions: list[dict], programmatic_result: dict, merge_prompt_fn = None) -> dict:
    """Use Mistral to review and improve the programmatic merge."""
    try:
        from agent import call_ollama
        if merge_prompt_fn is None:
            from prompt_builder import build_merge_prompt as merge_prompt_fn
            
        import json

        system_prompt, user_prompt = merge_prompt_fn(extractions)
        raw = call_ollama(system_prompt, user_prompt)

        # Strip markdown if present
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        llm_result = json.loads(raw)
        console.print("  [green]Success:[/green] LLM merge successful")
        return llm_result

    except Exception as e:
        console.print(f"  [yellow]![/yellow] LLM merge failed ({e}), using programmatic merge")
        return programmatic_result


def _print_merge_summary(extractions: list[dict], result: dict) -> None:
    """Print a summary of what was merged."""
    total_fields = 0
    filled_fields = 0

    def count_fields(obj):
        nonlocal total_fields, filled_fields
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, dict):
                    count_fields(v)
                elif not isinstance(v, list):
                    total_fields += 1
                    if v is not None and v is not False:
                        filled_fields += 1

    count_fields(result)

    console.print(Panel(
        f"[green]Documents processed:[/green] {len(extractions)}\n"
        f"[green]Fields filled:[/green] {filled_fields}/{total_fields}\n"
        f"[green]Coverage:[/green] {round(filled_fields/total_fields*100)}%\n"
        f"[green]Human review needed:[/green] {result.get('requires_human_review', False)}",
        title="Merge Summary",
        border_style="green"
    ))