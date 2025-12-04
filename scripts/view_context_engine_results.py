"""
View Context Engine Test Results

Displays detailed results from saved context engine test runs.
Shows the full process flow for each test case.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.tree import Tree
from rich.syntax import Syntax

console = Console()

def view_results_file(file_path: str):
    """View results from a saved test file"""
    path = Path(file_path)
    
    if not path.exists():
        console.print(f"[bold red]Error: File not found: {file_path}[/bold red]")
        return
    
    with open(path, 'r') as f:
        results = json.load(f)
    
    console.print(f"\n[bold cyan]Viewing results from: {file_path}[/bold cyan]\n")
    
    for i, result in enumerate(results, 1):
        if 'error' in result:
            console.print(f"\n[bold red]Test {i}: {result.get('test_name', 'Unknown')} - ERROR[/bold red]")
            console.print(f"[red]{result['error']}[/red]")
            continue
        
        test_name = result.get('test_name', 'Unknown')
        console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        console.print(f"[bold cyan]Test {i}: {test_name}[/bold cyan]")
        console.print(f"[bold cyan]{'='*80}[/bold cyan]")
        
        # Message
        message = result.get('message', {})
        console.print(f"\n[bold]Message:[/bold] {message.get('text', 'N/A')}")
        console.print(f"[bold]Channel:[/bold] {message.get('channel_name', 'N/A')}")
        console.print(f"[bold]User:[/bold] {message.get('user_name', 'N/A')}")
        console.print(f"[bold]Priority:[/bold] {message.get('priority_score', 'N/A')}")
        
        steps = result.get('steps', {})
        
        # Context Assembly
        if 'context_assembly' in steps:
            context_assembly = steps['context_assembly']
            console.print(f"\n[bold yellow]Step 1: Context Assembly[/bold yellow]")
            console.print(f"[dim]Total Context Size: {context_assembly.get('total_size', 0)} characters[/dim]")
            
            components = context_assembly.get('components', {})
            context_table = Table(title="Context Components")
            context_table.add_column("Component", style="cyan")
            context_table.add_column("Size (chars)", style="green")
            
            for component, content in components.items():
                if content:
                    context_table.add_row(component, str(len(content)))
            
            console.print(context_table)
        
        # Detection
        if 'detection' in steps:
            detection = steps['detection']
            console.print(f"\n[bold yellow]Step 2: Ticket Type Detection[/bold yellow]")
            
            detection_table = Table(title="Detection Results")
            detection_table.add_column("Field", style="cyan")
            detection_table.add_column("Value", style="green")
            
            for key, value in detection.items():
                detection_table.add_row(key, str(value))
            
            console.print(detection_table)
        
        # Query
        if 'query' in steps:
            query = steps['query']
            console.print(f"\n[bold yellow]Step 3: Search Query[/bold yellow]")
            console.print(Panel(query, title="Generated Query", border_style="blue"))
            
            # Query Analysis
            if 'query_analysis' in steps:
                query_analysis = steps['query_analysis']
                analysis_table = Table(title="Query Quality Analysis")
                analysis_table.add_column("Metric", style="cyan")
                analysis_table.add_column("Value", style="green")
                analysis_table.add_column("Status", style="yellow")
                
                for metric, (value, status) in query_analysis.items():
                    status_emoji = "✅" if status == "good" else "⚠️" if status == "warning" else "❌"
                    analysis_table.add_row(metric, str(value), f"{status_emoji} {status}")
                
                console.print(analysis_table)
        
        # Sources
        if 'sources' in steps:
            sources = steps['sources']
            console.print(f"\n[bold yellow]Step 4: Research Sources[/bold yellow]")
            console.print(f"[green]Found {len(sources)} sources[/green]")
            
            if sources:
                sources_table = Table(title="Research Sources")
                sources_table.add_column("#", style="cyan")
                sources_table.add_column("Title", style="green")
                sources_table.add_column("URL", style="blue")
                sources_table.add_column("Summary", style="yellow")
                
                for i, source in enumerate(sources[:5], 1):
                    title = source.get('title', 'Untitled')
                    url = source.get('url', '')
                    summary = source.get('summary', '')[:100] + "..." if len(source.get('summary', '')) > 100 else source.get('summary', '')
                    sources_table.add_row(str(i), title, url, summary)
                
                console.print(sources_table)
        
        # Synthesis
        if 'synthesis' in steps:
            synthesis = steps['synthesis']
            console.print(f"\n[bold yellow]Step 5: Research Synthesis[/bold yellow]")
            if synthesis:
                console.print(Panel(Markdown(synthesis), title="Synthesis & Recommendation", border_style="green"))
            else:
                console.print("[yellow]No synthesis generated[/yellow]")
        
        # Final Summary
        if 'final_summary' in steps:
            final_summary = steps['final_summary']
            console.print(f"\n[bold yellow]Step 6: Final Research Summary[/bold yellow]")
            if final_summary:
                # Truncate if too long
                display_summary = final_summary[:2000] + "\n\n..." if len(final_summary) > 2000 else final_summary
                console.print(Panel(Markdown(display_summary), title="Final Research Summary", border_style="cyan"))
        
        # Context Usage Analysis
        if 'context_usage_analysis' in steps:
            context_usage = steps['context_usage_analysis']
            console.print(f"\n[bold yellow]Step 7: Context Usage Analysis[/bold yellow]")
            
            usage_table = Table(title="Context Usage Analysis")
            usage_table.add_column("Context Component", style="cyan")
            usage_table.add_column("Found", style="green")
            usage_table.add_column("Details", style="yellow")
            
            for component, analysis in context_usage.items():
                found = analysis.get('found', False)
                details = analysis.get('details', '')
                status_emoji = "✅" if found else "❌"
                usage_table.add_row(component, f"{status_emoji} {'Yes' if found else 'No'}", details)
            
            console.print(usage_table)
        
        console.print("\n")


def list_results_files():
    """List all available test result files"""
    simulations_dir = Path(__file__).parent.parent / "simulations"
    
    if not simulations_dir.exists():
        console.print("[yellow]No simulations directory found[/yellow]")
        return []
    
    result_files = list(simulations_dir.glob("context_engine_test_*.json"))
    
    if not result_files:
        console.print("[yellow]No context engine test results found[/yellow]")
        return []
    
    console.print(f"\n[bold cyan]Found {len(result_files)} test result file(s):[/bold cyan]\n")
    
    files_table = Table(title="Available Test Results")
    files_table.add_column("#", style="cyan")
    files_table.add_column("File", style="green")
    files_table.add_column("Date", style="yellow")
    
    for i, file_path in enumerate(sorted(result_files, reverse=True), 1):
        files_table.add_row(
            str(i),
            file_path.name,
            file_path.stat().st_mtime  # Could format this better
        )
    
    console.print(files_table)
    return result_files


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # View specific file
        file_path = sys.argv[1]
        view_results_file(file_path)
    else:
        # List and let user choose
        result_files = list_results_files()
        
        if result_files:
            console.print("\n[bold]Usage:[/bold] python view_context_engine_results.py <file_path>")
            console.print(f"\n[bold]Most recent:[/bold] {result_files[0].name}")
            console.print(f"\n[bold]To view:[/bold] python view_context_engine_results.py simulations/{result_files[0].name}")
        else:
            console.print("\n[bold]No test results found. Run test_context_engine.py first.[/bold]")


if __name__ == "__main__":
    main()


