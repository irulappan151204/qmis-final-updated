import click
from flask.cli import with_appcontext
from extensions import db, bcrypt
from models import User

@click.command('create-admin')
@with_appcontext
def create_admin_command():
    """Create an admin user."""
    username = click.prompt('Enter admin username')
    password = click.prompt('Enter admin password', hide_input=True, confirmation_prompt=True)
    
    if User.query.filter_by(username=username).first():
        click.echo('Username already exists.')
        return
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    admin = User(username=username, password=hashed_password, role='Admin')
    db.session.add(admin)
    db.session.commit()
    click.echo('Admin user created successfully.') 