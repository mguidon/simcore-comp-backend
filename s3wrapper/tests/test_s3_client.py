import os
import uuid
import pytest
import filecmp

import s3wrapper
from s3wrapper.s3_client import S3Client


@pytest.fixture(scope="module")
def s3_client():
    hostname = 'osparc01.speag.com:10001'
    access_key='pNPLM9cpcvweLRVRXfRN'
    secret_key='JxkgxhmvuXpbMxnxeahyCHT4bMUXttAp'
    secure=False
    s3_client = S3Client(hostname, access_key, secret_key, secure)
    return s3_client

@pytest.fixture(scope="function")
def text_files(tmpdir_factory):
    def _create_files(N):
        filepaths = []
        for i in range(N):
            name = str(uuid.uuid4())
            filepath = os.path.normpath(str(tmpdir_factory.mktemp('data').join(name + ".txt")))
            with open(filepath, 'w') as fout:
                fout.write("Hello world\n")
            filepaths.append(filepath)

        return filepaths
    return _create_files


def test_create_remove_bucket(s3_client):
    bucket_name = "simcore-test"
    s3_client.create_bucket(bucket_name)
    assert s3_client.exists_bucket(bucket_name)
    s3_client.remove_bucket(bucket_name, delete_contents=True)
    assert not s3_client.exists_bucket(bucket_name)

def test_file_upload_download(s3_client, text_files):
    bucket_name = "simcore-test"
    s3_client.create_bucket(bucket_name, delete_contents=True)
    filepath = text_files(1)[0]
    object_name = "1"
    assert s3_client.upload_file(bucket_name, object_name, filepath)
    filepath2 = filepath + "."
    assert s3_client.download_file(bucket_name, object_name ,filepath2)
    assert filecmp.cmp(filepath2, filepath)

def test_file_upload_meta_data(s3_client, text_files):
    bucket_name = "simcore-test"
    s3_client.create_bucket(bucket_name, delete_contents=True)
    filepath = text_files(1)[0]
    object_name = "1"
    id = uuid.uuid4()
    metadata = {'user' : 'guidon', 'node_id' : str(id), 'boom-boom' : str(42.0)}

    assert s3_client.upload_file(bucket_name, object_name, filepath, metadata=metadata)

    metadata2 = s3_client.get_metadata(bucket_name, object_name)
    print (metadata2)
    assert metadata2["User"] == 'guidon'
    assert metadata2["Node_id"] == str(id)
    assert metadata2["Boom-Boom"] == str(42.0)

def test_sub_folders(s3_client, text_files):
    bucket_name = "simcore-test-sub"
    s3_client.create_bucket(bucket_name, delete_contents=True)
    bucket_sub_folder = str(uuid.uuid4())

    filepaths = text_files(3)
    counter = 1
    for f in filepaths:
        object_name = bucket_sub_folder + "/" + str(counter)
        assert s3_client.upload_file(bucket_name, object_name, f)
        counter += 1