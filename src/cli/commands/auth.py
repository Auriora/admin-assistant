"""Authentication commands."""

import typer
from cli.common.helpful_group import HelpfulGroup

# Create the main auth app
auth_app = typer.Typer(help="Authentication and authorization commands", rich_markup_mode="rich", cls=HelpfulGroup)

# Create the msgraph sub-app
msgraph_app = typer.Typer(help="Microsoft Graph authentication", rich_markup_mode="rich", cls=HelpfulGroup)


@msgraph_app.callback()
def msgraph_callback(ctx: typer.Context):
    """Microsoft Graph authentication commands.
    
    Manage authentication with Microsoft 365 services.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@msgraph_app.command("login")
def msgraph_login():
    """Login to Microsoft 365 using device code flow."""
    from core.utilities.auth_utility import msal_login

    msal_login()
    typer.echo("Microsoft 365 login completed. Token cached for future use.")


@msgraph_app.command("logout")
def msgraph_logout():
    """Logout from Microsoft 365 and remove cached token."""
    from core.utilities.auth_utility import msal_logout

    msal_logout()
    typer.echo("Microsoft 365 token removed. You are now logged out.")


# Register the msgraph app under auth
auth_app.add_typer(msgraph_app, name="msgraph")


@auth_app.callback()
def auth_callback(ctx: typer.Context):
    """Authentication and authorization commands.
    
    Manage authentication with various service providers.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
