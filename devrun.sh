poetry env activate
poetry install
poetry run black .
docker compose up --build
docker compose down