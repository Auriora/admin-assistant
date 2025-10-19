import typer
from click.testing import CliRunner

from cli.common.helpful_group import HelpfulGroup


def test_helpful_group_shows_help_for_unknown_command():
    # Instantiate HelpfulGroup directly to avoid Typer/Click runtime differences
    app = HelpfulGroup(name="testapp")

    @app.command()
    def hello():
        """A simple hello command"""
        typer.echo("hi")

    runner = CliRunner()

    # Invoke with a command that doesn't exist
    result = runner.invoke(app, ["nope"])

    # HelpfulGroup should show an error panel (to stderr) and then the help (stdout)
    assert result.exit_code == 2
    assert "Error" in result.stderr or "No such command" in result.stderr
    # The help should include the command name
    assert "hello" in result.output
