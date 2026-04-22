### Dashboards

dashboards

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app dashboards
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/dashboards
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI/CD

GitHub Actions workflows are configured in `.github/workflows`:

- `CI`: runs pre-commit hooks, `pip-audit`, Frappe Semgrep rules, and a Frappe v15 install/migrate/build smoke test on pull requests and pushes to `develop` or `main`.
- `CD`: deploys a selected branch, tag, or SHA to a protected GitHub environment through SSH and Bench. Run it manually from the Actions tab.

Configure these environment secrets for each deploy target:

- `SSH_HOST`: deployment server hostname or IP.
- `SSH_USER`: SSH user that owns or can access the bench.
- `SSH_PRIVATE_KEY`: private key with access to the server and repository.
- `SSH_PORT`: optional SSH port, defaults to `22`.
- `BENCH_PATH`: absolute path to the bench directory, for example `/home/frappe/frappe-bench`.
- `SITE_NAME`: Frappe site to migrate.
- `APP_PATH`: optional absolute path to this app on the server. Defaults to `$BENCH_PATH/apps/dashboards`.

The deploy job updates the app checkout, installs requirements, runs `bench --site <site> migrate`, builds this app's assets, clears caches, and restarts Bench services.


### License

mit
