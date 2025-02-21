poetry env activate
poetry install
poetry run black .
docker compose up --build -d
docker compose logs
docker compose down