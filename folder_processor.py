"""
Folder processor — handles batch processing of multiple cases.

Structure:
    input_folder/
        Clinic Schedule.docx  → Shared schedule (parsed once, injected per-case)
        subfolder1/  → Case 1 (1-N documents)
        subfolder2/  → Case 2 (1-N documents)
        subfolder3/  → Case 3 (1-N documents)

Each subfolder = one person/case → one merged JSON → one Excel row.
The Clinic Schedule.docx (if present) provides appointment times, client
names, clinic date, expert name, and medical records status.
"""
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from clinic_schedule_parser import find_clinic_schedule, parse_clinic_schedule

console = Console()

# Supported file types
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def get_case_folders(input_folder: str) -> list[Path]:
    """
    Scan input folder and return all subfolders that contain documents.
    Ignores empty folders and hidden folders.
    """
    input_path = Path(input_folder)

    if not input_path.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")

    if not input_path.is_dir():
        raise ValueError(f"Path is not a folder: {input_folder}")

    case_folders = []
    for subfolder in sorted(input_path.iterdir()):
        if not subfolder.is_dir():
            continue
        if subfolder.name.startswith("."):
            continue

        # Check if subfolder has at least one supported document
        docs = get_documents_in_folder(subfolder)
        if docs:
            case_folders.append(subfolder)
        else:
            console.print(f"[yellow]! Skipping empty folder:[/yellow] {subfolder.name}")

    return case_folders


def get_documents_in_folder(folder: Path) -> list[Path]:
    """
    Return all supported documents in a folder.
    Ignores subfolders, hidden files, and unsupported formats.
    Sorted for consistent processing order.
    """
    documents = []
    for file in sorted(folder.iterdir()):
        if not file.is_file():
            continue
        if file.name.startswith("."):
            continue
        if file.name.startswith("~"):  # ignore Word temp files
            continue
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append(file)

    return documents


def process_all_cases(
    input_folder: str,
    extract_fn,
    output_folder: str = None,
    use_llm_merge: bool = False
) -> list[dict]:
    """
    Process all case subfolders in the input folder.

    Args:
        input_folder:  Root folder containing subfolders (one per case)
        extract_fn:    extract_document function from agent.py
        output_folder: Where to save individual case JSONs (optional)
        use_llm_merge: Whether to use Mistral for merge review

    Returns:
        List of merged result dicts — one per case/subfolder
    """
    from merger import process_multiple_documents, inject_schedule_data

    case_folders = get_case_folders(input_folder)

    if not case_folders:
        raise ValueError(f"No valid case folders found in: {input_folder}")

    # ── Detect and parse Clinic Schedule ──────────────────────────
    schedule_data = {}
    schedule_path = find_clinic_schedule(input_folder)
    if schedule_path:
        console.print(f"\n[cyan]📋 Clinic Schedule found:[/cyan] {Path(schedule_path).name}")
        try:
            schedule_data = parse_clinic_schedule(schedule_path)
        except Exception as e:
            console.print(f"  [yellow]⚠ Could not parse schedule:[/yellow] {e}")
    else:
        console.print("\n[dim]No Clinic Schedule found in root folder[/dim]")

    # Print batch summary
    _print_batch_summary(input_folder, case_folders, schedule_data)

    # Setup output folder
    if output_folder:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None

    all_results = []
    failed_cases = []

    for i, case_folder in enumerate(case_folders, 1):
        documents = get_documents_in_folder(case_folder)

        console.print(
            f"\n[bold cyan]{'='*60}[/bold cyan]\n"
            f"[bold cyan]Case {i}/{len(case_folders)}:[/bold cyan] {case_folder.name}\n"
            f"[cyan]Documents:[/cyan] {len(documents)} file(s)"
        )

        for doc in documents:
            console.print(f"  [dim]→ {doc.name}[/dim]")

        try:
            # Process all documents in this subfolder as one case
            result = process_multiple_documents(
                document_paths=[str(doc) for doc in documents],
                extract_fn=extract_fn,
                use_llm_merge=use_llm_merge
            )

            # ── Inject clinic schedule data if available ──
            client_ref = case_folder.name  # e.g. "W2587243"
            if client_ref in schedule_data:
                console.print(f"  [cyan]📋 Injecting schedule data for {client_ref}[/cyan]")
                result = inject_schedule_data(result, schedule_data[client_ref])
            elif schedule_data:
                console.print(f"  [yellow]⚠ No schedule entry for {client_ref}[/yellow]")

            # Tag result with case metadata
            result["_case_metadata"] = {
                "case_folder": case_folder.name,
                "documents_processed": [doc.name for doc in documents],
                "document_count": len(documents),
                "schedule_matched": client_ref in schedule_data
            }

            all_results.append(result)

            # Save individual case JSON if output folder specified
            if output_path:
                case_output = output_path / f"{case_folder.name}.json"
                with open(case_output, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                console.print(f"  [green]✓ Saved:[/green] {case_output.name}")

        except Exception as e:
            console.print(f"  [red]✗ Case failed:[/red] {e}")
            failed_cases.append({
                "folder": case_folder.name,
                "error": str(e)
            })
            continue

    # Final batch report
    _print_final_report(all_results, failed_cases)

    return all_results


def _print_batch_summary(
    input_folder: str,
    case_folders: list[Path],
    schedule_data: dict = None
) -> None:
    """Print overview of what will be processed."""
    table = Table(title="Batch Processing Summary", border_style="cyan")
    table.add_column("Case Folder",  style="cyan")
    table.add_column("Documents",    style="green", justify="center")
    table.add_column("File Types",   style="yellow")
    if schedule_data:
        table.add_column("Schedule", style="magenta", justify="center")

    total_docs = 0
    matched = 0
    for folder in case_folders:
        docs = get_documents_in_folder(folder)
        total_docs += len(docs)
        extensions = ", ".join(sorted({d.suffix.lower() for d in docs}))
        if schedule_data:
            has_schedule = "✓" if folder.name in schedule_data else "—"
            if folder.name in schedule_data:
                matched += 1
            table.add_row(folder.name, str(len(docs)), extensions, has_schedule)
        else:
            table.add_row(folder.name, str(len(docs)), extensions)

    console.print(table)
    summary = (
        f"\n[bold]Total:[/bold] {len(case_folders)} cases, "
        f"{total_docs} documents to process"
    )
    if schedule_data:
        summary += f"\n[bold]Schedule:[/bold] {matched}/{len(case_folders)} cases matched"
    console.print(summary + "\n")


def _print_final_report(results: list[dict], failed: list[dict]) -> None:
    """Print final batch processing report."""
    needs_review = sum(
        1 for r in results
        if r.get("requires_human_review", False)
    )

    console.print(Panel(
        f"[green]Success: Successfully processed:[/green] {len(results)} cases\n"
        f"[red]Error: Failed:[/red]              {len(failed)} cases\n"
        f"[yellow]! Needs human review:[/yellow]  {needs_review} cases\n"
        + (
            "\n[red]Failed cases:[/red]\n" +
            "\n".join(f"  • {f['folder']}: {f['error']}" for f in failed)
            if failed else ""
        ),
        title="Batch Complete",
        border_style="green" if not failed else "yellow"
    ))