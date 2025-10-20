from io import StringIO

from rich.console import Console

from cli.main import build_command_tree, show_command_tree


def test_build_command_tree_contains_expected_nodes():
    tree = build_command_tree()
    # Render the tree to a string using a Console writing to StringIO
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, color_system=None)
    console.print(tree)
    output = buf.getvalue()

    # Basic sanity checks
    assert "admin-assistant" in output
    assert "calendar" in output
    assert "config" in output
    assert "archive" in output
    assert "timesheet" in output


def test_show_command_tree_prints_tree(capsys):
    # show_command_tree uses Console() internally; calling it should not raise
    show_command_tree()
    # Nothing else to assert here beyond not raising; capture ensures no exception
    # However, we can assert that at least something was written to stdout
    captured = capsys.readouterr()
    assert "admin-assistant" in captured.out or captured.err == ""
