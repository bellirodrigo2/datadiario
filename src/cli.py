import asyncio
import logging
from typing import Optional
from rich.console import Console
import click
from .container import  get_use_case,LinkRequest

console = Console()

@click.command(help="Read and filter links from database")
@click.argument("command")
@click.option("--entity", "-e", required=True, help="Entity name")
@click.option("--group", "-g", required=True, help="Group name")
@click.option(
    "--start-date",
    "-st",
    required=True,
    help="Start date for range (YYYY-MM-DD or DD/MM/YYYY format)",
)
@click.option(
    "--end-date",
    "-et",
    help="End date for range (YYYY-MM-DD or DD/MM/YYYY format)",
)
@click.option(
    "--status",
    type=click.Choice(["pending", "processed", "failed"]),
    help="Filter by link status",
)
@click.option(
    "--commit/--no-commit",
    default=True,
    help="Whether to save links to database",
)
@click.option("--output", "-o", help="Output file path (default: stdout)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def links(
    command: str,
    entity: str,
    group: str,
    start_date: str,
    end_date: Optional[str],
    status: Optional[str],
    commit: Optional[bool],
    output: Optional[str],
    verbose: bool,
):
    if not start_date and not end_date:
        console.print(f"[red]Error: At least one of --start-date or --end-date must be provided.[/red]")
        return

    if start_date and not end_date:
        end_date = start_date

    usecase = asyncio.run(get_use_case(command))
    # logger = usecase.logger
    
    if verbose:
        logger = usecase.logger
        logger.setLevel(logging.DEBUG)

    req = LinkRequest(
        entity=entity,
        group=group,
        start_date=start_date,
        end_date=end_date,
        status=status,
        commit=commit,
        output=output,
    )
    console.print(f"[green]'{command.upper()}' for entity '{entity}' and group '{group}' from {start_date} to {end_date}[/green]")
    results = asyncio.run(
        usecase.execute(
            entity_name=req.entity,
            group=req.group,
            start=req.start_date,
            end=req.end_date,
            status_filter=req.status,
            commit=req.commit,
        )
    )
    console.print(f"[blue]Found {len(results) if results else 0} links.[/blue]")    
    if req.output:
        with open(output, "w", encoding="utf-8") as f:
            if isinstance(results, dict):
                for date_key, links in results.items():
                    f.write(f"Date: {date_key}\n")
                    for link in links:
                        f.write(f"{link}\n")
                    f.write("\n")
            elif isinstance(results, list):
                for link in results:
                    f.write(f"{link}\n")
        console.print(f"Results written to {output}")
    
    return results

@click.group()
def cli():
    pass

cli.add_command(links)

if __name__ == "__main__":
    cli()