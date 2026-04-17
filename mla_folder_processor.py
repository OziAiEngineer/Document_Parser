"""
MLA Folder Processor — handles flat folder structure where documents are grouped by filename.

Structure:
    input_folder/
        001 - Mr Michael Kloska - Solicitor Instruction.doc
        002 - Mr Michael Kloska - Client Instruction.doc
        003 - Mrs Kirsty Louise Entwistle - Solicitor Instruction.doc
        ...

Grouping: Files are grouped by the 'Name' part (split by ' - ', index 1).
"""
import json
from pathlib import Path
from collections import defaultdict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from folder_processor import SUPPORTED_EXTENSIONS, get_documents_in_folder
from merger import process_multiple_documents
from agent import extract_document
import mla_prompt_builder

console = Console()

def get_mla_groups(target) -> dict[str, list[Path]]:
    documents = []
    
    if isinstance(target, str):
        input_path = Path(target)
        if not input_path.exists():
            raise FileNotFoundError(f"Input path not found: {target}")
        if not input_path.is_dir():
            raise ValueError(f"Path is not a folder: {target}")
            
        # Get all supported documents in the flat folder (not recursive)
        for file in sorted(input_path.iterdir()):
            if not file.is_file():
                continue
            if file.name.startswith((".", "~")):
                continue
            if file.suffix.lower() in SUPPORTED_EXTENSIONS:
                documents.append(file)
    else:
        # It's a list of file paths
        for path_str in target:
            file = Path(path_str)
            if file.is_file() and not file.name.startswith((".", "~")) and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                documents.append(file)

    groups = defaultdict(list)
    for doc in documents:
        # Split by ' - ' to find the name
        # Pattern: [Seq] - [Name] - [Type]
        parts = doc.stem.split(" - ")
        if len(parts) >= 2:
            name_key = parts[1].strip()
            groups[name_key].append(doc)
        else:
            # Fallback for files that don't match the pattern - use full stem
            console.print(f"[yellow]! Filename doesn't match MLA pattern:[/yellow] {doc.name}")
            groups[doc.stem].append(doc)
            
    return groups

def process_mla_cases(
    target,
    output_folder: str = None,
    use_llm_merge: bool = False
) -> list[dict]:
    """
    Process all MLA cases from a flat folder or a list of files.
    """
    groups = get_mla_groups(target)
    
    if not groups:
        target_name = target if isinstance(target, str) else f"{len(target)} files"
        raise ValueError(f"No valid MLA documents found in: {target_name}")

    # Print summary
    table = Table(title="MLA Batch Summary", border_style="cyan")
    table.add_column("Case (Name Group)", style="cyan")
    table.add_column("Documents", style="green", justify="center")
    
    for name, docs in groups.items():
        table.add_row(name, str(len(docs)))
    console.print(table)

    # Setup output folder
    if output_folder:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None

    all_results = []
    failed_cases = []

    # Wrapper for extraction to use MLA builder
    def mla_extract(text):
        return extract_document(
            text, 
            system_prompt_fn=mla_prompt_builder.build_system_prompt,
            extraction_prompt_fn=mla_prompt_builder.build_extraction_prompt
        )

    for i, (name, documents) in enumerate(groups.items(), 1):
        console.print(
            f"\n[bold cyan]{'='*60}[/bold cyan]\n"
            f"[bold cyan]Case {i}/{len(groups)}:[/bold cyan] {name}\n"
            f"[cyan]Documents:[/cyan] {len(documents)} file(s)"
        )

        for doc in documents:
            console.print(f"  [dim]→ {doc.name}[/dim]")

        try:
            # Process all documents in this group as one case
            result = process_multiple_documents(
                document_paths=[str(doc) for doc in documents],
                extract_fn=mla_extract,
                use_llm_merge=use_llm_merge,
                merge_prompt_fn=mla_prompt_builder.build_merge_prompt
            )

            # Tag result with case metadata
            result["_case_metadata"] = {
                "case_name": name,
                "documents_processed": [doc.name for doc in documents],
                "document_count": len(documents),
                "company_style": "MLA"
            }

            all_results.append(result)

            # Save individual case JSON - use sanitized name for filename
            if output_path:
                safe_name = name.replace(" ", "_").replace(".", "")
                case_output = output_path / f"{safe_name}.json"
                with open(case_output, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                console.print(f"  [green]✓ Saved:[/green] {case_output.name}")

        except Exception as e:
            console.print(f"  [red]✗ Case failed:[/red] {e}")
            failed_cases.append({
                "name": name,
                "error": str(e)
            })
            continue

    # Final report (re-use logic from folder_processor if we wanted, but keeping it simple here)
    console.print(Panel(
        f"[green]Success:[/green] {len(all_results)} cases processed\n"
        f"[red]Failed:[/red]  {len(failed_cases)} cases",
        title="MLA Batch Complete",
        border_style="green" if not failed_cases else "yellow"
    ))

    return all_results
