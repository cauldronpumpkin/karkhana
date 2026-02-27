"""Structured logging and progress tracking."""

import sys
from datetime import datetime
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.text import Text


class LoggerFactory:
    """Factory for creating logger instances."""

    _console: Console | None = None

    @classmethod
    def get_console(cls) -> Console:
        """Get or create console instance."""
        if cls._console is None:
            cls._console = Console(file=sys.stdout)
        return cls._console


def log_info(message: str):
    """Log info message with timestamp."""
    console = LoggerFactory.get_console()
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[bold cyan][{timestamp}[/bold cyan]] [white]{message}[/white]")


def log_success(message: str):
    """Log success message."""
    console = LoggerFactory.get_console()
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[bold green][{timestamp}[/bold green]] [green]{message}[/green]")


def log_error(message: str):
    """Log error message."""
    console = LoggerFactory.get_console()
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[bold red][{timestamp}[/bold red]] [red]{message}[/red]")


class BuildProgress:
    """Track build progress with Rich progress bar."""

    def __init__(self):
        self.progress = Progress()
        self.task_id: TaskID | None = None
        self.files_table = Table(title="File Generation Progress")
        
        self.files_table.add_column("File", style="cyan")
        self.files_table.add_column("Status", style="green")
        self.files_table.add_column("Time", style="yellow")

    def start(self):
        """Start the progress tracking."""
        self.progress.start()
        self.task_id = self.progress.add_task(
            "Building project...",
            total=100
        )

    def update_file_status(self, file_path: str, status: str, elapsed: float | None = None):
        """Update status for a specific file."""
        time_str = f"{elapsed:.1f}s" if elapsed is not None else "-"
        self.files_table.add_row(file_path, status, time_str)

    def update_progress(self, percentage: int):
        """Update overall progress bar."""
        if self.task_id:
            self.progress.update(self.task_id, completed=percentage)

    def stop(self):
        """Stop and display final summary."""
        self.progress.stop()
        
        # Display file table
        console = LoggerFactory.get_console()
        console.print("\n")
        console.print(Panel(
            self.files_table,
            title="Build Summary",
            border_style="green"
        ))


def print_summary(stats: dict):
    """Print build statistics summary."""
    console = LoggerFactory.get_console()
    
    table = Table(title="BUILD STATISTICS", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in stats.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print("\n")
    console.print(Panel(
        table,
        title="Project Build Complete!",
        border_style="green",
        padding=(1, 2)
    ))
