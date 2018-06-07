import pytest
import os



@pytest.fixture(scope='session')
def docker_compose_file(pytestconfig):
    my_path = os.path.join(os.path.dirname(__file__), 'docker-compose.yml')
    return my_path
