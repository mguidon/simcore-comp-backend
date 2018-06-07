import psycopg2
import pytest
from pytest_docker import docker_ip, docker_services

def is_responsive(dbname, user, password, host, port):
    """Check if there is a db"""
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        conn.close()
    except psycopg2.OperationalError as ex:
        print("Connection failed: {0}".format(ex))
        return False

    return True

@pytest.mark.enable_travis
def test_postgres(docker_ip, docker_services):
    """wait for postgres to be up"""

    dbname = 'test'
    user = 'user'
    password = 'pwd'
    host = docker_ip
    port = docker_services.port_for('postgres', 5432)
    # Wait until we can connect
    docker_services.wait_until_responsive(
        check=lambda: is_responsive(dbname, user, password, host, port),
        timeout=30.0,
        pause=1.0,
    )

    connection_ok = False
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        conn.close()
        connection_ok = True
    except psycopg2.OperationalError as ex:
        pass

    assert connection_ok


    