import asyncio
import json
import logging
from typing import Any, Optional

import click
from rich.console import Console

from .container import LinkRequest, get_use_case

console = Console()


@click.command(help="Read and filter links from database")
@click.argument("operation")
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
def run(
    operation: str,
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
        console.print(
            f"[red]Error: At least one of --start-date or --end-date must be provided.[/red]"
        )
        return

    if start_date and not end_date:
        end_date = start_date

    command = f"{operation.upper()}:{command.upper()}"

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
    console.print(
        f"[green]'{command.upper()}' for entity '{entity}' and group '{group}' from {start_date} to {end_date}[/green]"
    )
    results: dict[Any, Any] = asyncio.run(
        usecase.execute(
            entity_name=req.entity,
            group=req.group,
            start=req.start_date,
            end=req.end_date,
            status_filter=req.status,
            commit=req.commit,
        )
    )
    res_str = {str(date_key): len(links) for date_key, links in results.items()}
    console.print(res_str)
    if req.output:
        with open(req.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        console.print(f"Results written to {req.output}")

    if verbose:
        for date, links in results.items():
            console.log(f"Date: {date}")
            for link in links:
                console.log(f"\tLink: {link}")

    return results


# @click.group()
# def cli():
#     pass


# cli.add_command(links)

if __name__ == "__main__":
    # cli()
    run()
