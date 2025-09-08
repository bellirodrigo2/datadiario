# CLI wrapper around click library with register and listen functions
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

import click


class CLIWrapper:
    """A wrapper around Click CLI library providing register and listen functionality"""

    def __init__(
        self, name: str = "dou-cli", help_text: str = "DOU Data Collection CLI"
    ):
        self.cli_group = click.Group(name=name, help=help_text)
        self.commands: Dict[str, click.Command] = {}
        self.logger = logging.getLogger(__name__)

    def register(
        self, name: Optional[str] = None, **kwargs: Any
    ) -> Callable[..., Callable[..., Any]]:
        """
        Decorator to register a command with the CLI

        Args:
            name: Command name (defaults to function name)
            **kwargs: Additional click command options
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            command_name = name or func.__name__

            # Convert function to click command
            click_command = click.command(name=command_name, **kwargs)(func)

            # Add to CLI group
            self.cli_group.add_command(click_command)
            self.commands[command_name] = click_command

            self.logger.debug(f"Registered CLI command: {command_name}")

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def listen(self, args: Optional[list[str]] = None, standalone_mode: bool = True):
        """
        Start listening for CLI commands

        Args:
            args: Command line arguments (defaults to sys.argv)
            standalone_mode: Whether to handle exceptions internally
        """
        try:
            self.logger.info("Starting CLI listener...")
            return self.cli_group(args=args, standalone_mode=standalone_mode)
        except Exception as e:
            self.logger.error(f"CLI execution failed: {e}")
            if not standalone_mode:
                raise

    def add_command(self, command: click.Command, name: Optional[str] = None):
        """
        Manually add a click command to the CLI

        Args:
            command: Click command to add
            name: Command name (defaults to command.name)
        """
        command_name = name or command.name
        self.cli_group.add_command(command, name=command_name)
        self.commands[command_name] = command
        self.logger.debug(f"Added CLI command: {command_name}")

    def list_commands(self) -> list[str]:
        """Get list of registered command names"""
        return list(self.commands.keys())

    def get_command(self, name: str) -> Optional[click.Command]:
        """Get a registered command by name"""
        return self.commands.get(name)
