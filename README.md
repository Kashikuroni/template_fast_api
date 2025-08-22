# Fast API Template
## Description
The basic template of the backend application with ready authorization and creation of workspaces.

### Stack
- uv          - Python manager.
- Fast API    - Backend Framework.
- PostgreSQL  - Database.
- Redis       - Cache (Optional).

### Core Libraries
- AuthX      - Authorization.
- SqlAlchemy - ORM.
- Alembic    - Migrations.
- Loguru     - Logging.
- Rich       - Displaying progress in the terminal during lengthy API requests.
- Uvicorn    - ASGI web server.
- Pydantic   - Data validation.

### Features
1. Authorization via JWT tokens in cookies.
2. The ability to create a superuser at the start of the backend via the env configuration.
3. Workspaces.

## Install
This project uses uv, if you don't have it, install it. If you need help, please visit their official website.
https://docs.astral.sh/uv/getting-started/installation/

1. Clone repository.
    ```bash
    git clone git@github.com:Kashikuroni/template_fast_api.git
    ```
2. Install dependencies.
    ```bash
    uv sync
    ```

3. Next, you need to initialize the database, you can do this via Docker or a local database server if you have a mac OS.
4. Create a .env.dev file in the .env directory and fill it in using this template.
    ### Env settings template
    ```
    # Configuring logging
    DEBUG=True

    # Configuring the PostgreSQL database.
    DB_HOST=
    DB_PORT=
    DB_NAME=
    DB_USER=
    DB_PASSWORD=

    # Configuring Superuser
    CREATE_SUPERUSER=False
    SUPERUSER_EMAIL=
    SUPERUSER_PASSWORD=
    SUPERUSER_FIRSTNAME=
    SUPERUSER_LASTNAME=
    SUPERUSER_USERNAME=

    # Secrets
    SECRET=
    JWT_SECRET_KEY=

    # Configuring Redis Optional.
    REDIS_HOST=
    REDIS_PORT=
    REDIS_DB=
    CACHE_TTL=
    ```
5. Run migration.
    ```bash
    uv run alembic upgrade head
    ```
6. Start app (From the root of the project).
    ```bash
    uv run uvicorn src.main:app --reload
    ```

> You should see the standard uvicorn message that the server is running, and also,
if you have configured the creation of superuser, you will see a message
that it has been created or an error if you have incorrectly connected/started your database.

Have fun developing!