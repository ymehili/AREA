"""Admin CLI commands for managing admin users."""

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.user import User
from app.services.users import get_user_by_email, grant_admin_privileges

app = typer.Typer()

@app.command()
def create_admin_user(email: str):
    """Grant admin privileges to a user by email."""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        user = get_user_by_email(db, email)
        if not user:
            typer.echo(f"Error: User with email {email} not found.")
            raise typer.Exit(code=1)
        
        grant_admin_privileges(db, user)
        typer.echo(f"Admin privileges granted to user with email: {email}")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)
    finally:
        db.close()

if __name__ == "__main__":
    app()