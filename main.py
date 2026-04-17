"""
Main entry point for the legal document extraction agent.

Supports:
1. Command Line Interface (CLI)
2. Desktop App Integration (via run_service function)
"""
import sys
import json
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

# Import existing logic
from agent import extract_document
from merger import process_multiple_documents
from folder_processor import process_all_cases
from validator import ExtractionValidator

console = Console()

def run_service(mode="single", target_path=None, company="speed", output_dir="./results", excel=False, llm_merge=False):
    """
    Core logic function that can be called by the PyQt Desktop App or the CLI.
    
    Args:
        mode (str): "single" for documents or "folder" for batch processing.
        target_path (str/list): Path to file, list of files, or folder path.
        company (str): "speed" or "mla".
        output_dir (str): Where to save results.
        excel (bool): Whether to export to Excel.
        llm_merge (bool): Whether to use LLM for merging.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    results_to_return = None

    # ── MLA MODE (Applies to all inputs for MLA) ───────────────
    if company.lower() == "mla":
        console.print(f"[cyan]Service Mode:[/cyan] MLA Processing")
        from mla_folder_processor import process_mla_cases
        results = process_mla_cases(
            target=target_path,
            output_folder=output_dir,
            use_llm_merge=llm_merge
        )
        if excel and results:
            from excel_writer import write_to_excel
            output_file = output_path / "mla_cases.xlsx"
            write_to_excel(results, str(output_file))
            console.print(f"[green]Success: Excel exported:[/green] {output_file}")
        return results

    # ── BATCH FOLDER MODE ──────────────────────────────────────
    if mode == "folder":
        console.print(f"[cyan]Service Mode:[/cyan] Batch Folder Processing")
        
        results = process_all_cases(
            input_folder=target_path,
            extract_fn=extract_document,
            output_folder=output_dir,
            use_llm_merge=llm_merge
        )

        if excel and results:
            from excel_writer import write_to_excel
            output_file = output_path / "all_cases.xlsx"
            write_to_excel(results, str(output_file))
            console.print(f"[green]Success: Excel exported:[/green] {output_file}")
        
        results_to_return = results

    # ── SINGLE / MULTI DOCUMENT MODE ───────────────────────────
    else:
        # Ensure target_path is a list
        docs = [target_path] if isinstance(target_path, str) else target_path
        
        console.print(f"[cyan]Service Mode:[/cyan] Single Case ({len(docs)} files)")

        try:
            result = process_multiple_documents(
                document_paths=docs,
                extract_fn=extract_document,
                use_llm_merge=llm_merge
            )
        except Exception as e:
            console.print(f"[red]Extraction failed: {e}[/red]")
            raise e

        # Validate
        validator = ExtractionValidator()
        try:
            validated_model, needs_review = validator.validate(result)
            output_data = validated_model.model_dump()
        except Exception as e:
            console.print(f"[red]Validation failed: {e}[/red]")
            output_data = result 

        # Save to JSON
        case_name = Path(docs[0]).stem if len(docs) == 1 else "merged_result"
        output_file = output_path / f"{case_name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]Success: Saved JSON to:[/green] {output_file}")

        if excel:
            from excel_writer import write_to_excel
            excel_file = output_path / f"{case_name}.xlsx"
            write_to_excel([output_data], str(excel_file))
            console.print(f"[green]Success: Excel exported:[/green] {excel_file}")
        
        results_to_return = output_data

    return results_to_return


def parse_args():
    parser = argparse.ArgumentParser(description="Legal Document Extraction Agent")
    parser.add_argument("documents", nargs="*", help="One or more document paths")
    parser.add_argument("--folder", "-f", type=str, help="Root folder for batch mode")
    parser.add_argument("--output", "-o", type=str, default="./output", help="Output folder")
    parser.add_argument("--llm-merge", action="store_true", help="Use Mistral LLM")
    parser.add_argument("--excel", action="store_true", help="Export to Excel")
    parser.add_argument("--company", "-c", type=str, default="speed", choices=["speed", "mla"], help="Style")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.folder:
        # Batch Mode via CLI
        console.print(Panel(f"[cyan]Folder Mode[/cyan]\nInput: {args.folder}", title="Legal Agent"))
        run_service(
            mode="folder",
            target_path=args.folder,
            company=args.company,
            output_dir=args.output,
            excel=args.excel,
            llm_merge=args.llm_merge
        )
    elif args.documents:
        # Single Mode via CLI
        console.print(Panel(f"[cyan]Single Case Mode[/cyan]\nFiles: {len(args.documents)}", title="Legal Agent"))
        data = run_service(
            mode="single",
            target_path=args.documents,
            company=args.company,
            output_dir=args.output,
            excel=args.excel,
            llm_merge=args.llm_merge
        )
        # Final display for CLI user
        console.print("\n[bold green]Extracted Data:[/bold green]")
        console.print(JSON(json.dumps(data, indent=2, ensure_ascii=False)))
    else:
        print("Error: Provide documents or use --folder. Use --help for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()