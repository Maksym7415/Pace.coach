.PHONY: backend-install backend-run backend-test frontend-install frontend-run migrate

backend-install:
	cd backend && pip install -e ".[dev]"

backend-run:
	cd backend && python -m src.main

backend-test:
	cd backend && pytest -q

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

migrate:
	cd backend && alembic -c alembic.ini upgrade head
