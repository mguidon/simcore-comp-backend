cd ..
docker-compose up -d postgres
cd -
id=`docker ps -n 1 -q`
echo $id
docker run -it -v ../migration:/migration -v ../models:/models python:3.6-alpine