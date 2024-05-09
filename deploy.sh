service_name=oncall-web
old_version=$(docker ps -f name=$service_name -q | tail -n1)

echo "Creating instance with new version..."
docker compose up --build -d --no-recreate --no-deps --scale $service_name=2 $service_name > /dev/null

echo "Created\nRestarting nginx..."
docker compose exec nginx nginx -s reload > /dev/null

echo "Success\nDeleting container with old version..."
docker container stop $old_version > /dev/null
docker container rm $old_version > /dev/null
docker compose up -d --no-deps --scale $service_name=1 --no-recreate $service_name

echo "Success\nRestarting nginx..."
docker compose exec nginx nginx -s reload > /dev/null
echo "Success"
echo "Deploy finished"
