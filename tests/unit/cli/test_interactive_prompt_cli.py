import typer
from typer.testing import CliRunner

from cli.commands import interactive_prompt as ip


def test_resolve_cli_user_no_user(monkeypatch):
    # Simulate resolve_user returning None
    monkeypatch.setattr('cli.commands.interactive_prompt.resolve_user', lambda x: None)
    monkeypatch.setattr('cli.commands.interactive_prompt.get_user_identifier_source', lambda x: 'env')

    app = typer.Typer(name="testapp")

    @app.command()
    def run():
        # This should raise typer.Exit with code 1
        ip.resolve_cli_user(None)

    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "No user identifier found from env" in result.output or "Please specify --user" in result.output


def test_resolve_cli_user_value_error(monkeypatch):
    # Simulate resolve_user raising ValueError
    def bad(x):
        raise ValueError("bad input")

    monkeypatch.setattr('cli.commands.interactive_prompt.resolve_user', bad)
    monkeypatch.setattr('cli.commands.interactive_prompt.get_user_identifier_source', lambda x: 'cli')

    app = typer.Typer(name="testapp")

    @app.command()
    def run():
        ip.resolve_cli_user('foo')

    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Error resolving user from cli" in result.output
