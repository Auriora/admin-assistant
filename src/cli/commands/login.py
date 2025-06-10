"""Authentication commands."""

import typer

login_app = typer.Typer(help="Authentication commands")


@login_app.command("msgraph")
def msgraph_login():
    """Login to Microsoft 365 using device code flow."""
    from core.utilities.auth_utility import msal_login

    msal_login()
    typer.echo("Microsoft 365 login completed. Token cached for future use.")


@login_app.command("logout")
def msgraph_logout():
    """Logout from Microsoft 365 and remove cached token."""
    from core.utilities.auth_utility import msal_logout

    msal_logout()
    typer.echo("Microsoft 365 token removed. You are now logged out.")
