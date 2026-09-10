# Deploy Money Earn

## Render
1. Create a new Web Service.
2. Upload/push this project to a Git repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variable `SECRET_KEY` with a long random value.
6. Deploy.

## Railway
1. Create a new Python project from this repository.
2. Railway will install `requirements.txt`.
3. Start command: `gunicorn app:app`
4. Add `SECRET_KEY` in Variables.
5. Deploy.

## Important production note
The current app uses SQLite. For a small test deployment this is okay, but many cloud hosts use ephemeral filesystems.
For a real public service, use PostgreSQL/MySQL so user accounts, task approvals, payments and withdrawals are not lost after redeploys.

## Admin
Default demo admin:
Phone: 03000000000
Password: admin123

Change this before public launch.
