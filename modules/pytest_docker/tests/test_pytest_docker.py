import requests
from pytest_docker import docker_ip, docker_services
import pytest

# pylint:disable=redefined-outer-name
# pylint:disable=unused-import

def is_responsive(url):
    """Check if something responds to ``url``."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except Exception as _ex:
        pass
    return False
    

@pytest.mark.enable_travis
def test_integration(docker_ip, docker_services):
    """Showcase the power of our Docker fixtures!"""

    # Build URL to service listening on random port.
    url = 'http://%s:%d/' % (
        docker_ip,
        docker_services.port_for('hello', 80),
    )

    # Wait until service is responsive.
    docker_services.wait_until_responsive(
        check=lambda: is_responsive(url),
        timeout=30.0,
        pause=0.1,
    )

    # Contact the service.
    response = requests.get(url)
    response.raise_for_status()
    print(response.text)
