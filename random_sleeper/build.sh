docker build -t sleeper .
docker tag sleeper:latest masu.speag.com/simcore/services/comp/sleeper:1.0
docker push masu.speag.com/simcore/services/comp/sleeper:1.0
