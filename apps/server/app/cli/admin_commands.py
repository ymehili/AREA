"""CLI commands for admin-related operations."""

import click
from sqlalchemy.orm import Session
from app.db.session import get_db_sync
from app.services.users import get_user_by_email


@click.group()
def admin_cli():
    """Admin CLI commands."""
    pass


@admin_cli.command()
@click.option(
    "--email", prompt="User email", help="Email of the user to grant admin rights"
)
def grant_admin(email: str):
    """Grant admin privileges to a user by email."""
    db: Session = next(get_db_sync())

    try:
        user = get_user_by_email(db, email)
        if user is None:
            click.echo(f"Error: User with email {email} not found.")
            return

        user.is_admin = True
        db.commit()
        db.refresh(user)

        click.echo(f"Admin privileges granted to user: {email}")
    except Exception as e:
        click.echo(f"Error granting admin privileges: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    admin_cli()
