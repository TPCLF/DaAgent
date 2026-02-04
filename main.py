import typer
from rich.console import Console
from agent.config import AgentConfig
from agent.core import Agent

app = typer.Typer(help="Local CLI Coding Agent")
console = Console()

@app.command()
def run(
    task: str = typer.Argument(..., help="The coding task to perform."),
    model: str = typer.Option(None, help="Override model name."),
    diff_only: bool = typer.Option(False, "--diff-only", help="Only show diffs, don't apply."),
    auto_approve: bool = typer.Option(False, "--yes", "-y", help="Auto-approve dangerous actions."),
):
    """
    Start the coding agent with a specific task.
    """
    # Load config from env, then override with CLI opts
    config = AgentConfig.from_env()
    
    if model:
        config.model = model
    if diff_only:
        config.diff_only = True
    if auto_approve:
        config.confirm_dangerous = False

    console.print(f"[bold green]Starting Agent[/bold green] with model: [cyan]{config.model}[/cyan]")
    
    agent = Agent(config)
    agent.run(task)

if __name__ == "__main__":
    app()
