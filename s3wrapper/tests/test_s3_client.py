import os
import uuid
import pytest
import filecmp

import s3wrapper
from s3wrapper.s3_client import S3Client


@pytest.fixture(scope="module")
def s3_client():
    hostname = os.getenv("MINIO_HOST")
    access_key= os.getenv("MINIO_ACCESS_KEY")
    secret_key= os.getenv("MINIO_SECRET_KEY")
    secure=False
    s3_client = S3Client(hostname, access_key, secret_key, secure)
    return s3_client

@pytest.fixture(scope="module")
def bucket(s3_client, request):
    bucket_name = "simcore-test"
    s3_client.create_bucket(bucket_name, delete_contents=True)
    def fin():
        s3_client.remove_bucket(bucket_name, delete_contents=True)
    request.addfinalizer(fin)
    return bucket_name

@pytest.fixture(scope="function")
def text_files(tmpdir_factory):
    def _create_files(N):
        filepaths = []
        for _i in range(N):
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

def test_create_remove_bucket_with_contents(s3_client, text_files):
    bucket_name = "simcore-test"
    s3_client.create_bucket(bucket_name)
    assert s3_client.exists_bucket(bucket_name)
    object_name = "dummy"
    filepath = text_files(1)[0]    
    assert s3_client.upload_file(bucket_name, object_name, filepath)
    assert s3_client.remove_bucket(bucket_name, delete_contents=False)
    assert s3_client.exists_bucket(bucket_name)    
    s3_client.remove_bucket(bucket_name, delete_contents=True)
    assert not s3_client.exists_bucket(bucket_name)

def test_file_upload_download(s3_client, bucket, text_files):
    filepath = text_files(1)[0]
    object_name = "1"
    assert s3_client.upload_file(bucket, object_name, filepath)
    filepath2 = filepath + "."
    assert s3_client.download_file(bucket, object_name ,filepath2)
    assert filecmp.cmp(filepath2, filepath)

def test_file_upload_meta_data(s3_client, bucket, text_files):
    filepath = text_files(1)[0]
    object_name = "1"
    id = uuid.uuid4()
    metadata = {'user' : 'guidon', 'node_id' : str(id), 'boom-boom' : str(42.0)}

    assert s3_client.upload_file(bucket, object_name, filepath, metadata=metadata)

    metadata2 = s3_client.get_metadata(bucket, object_name)
    print (metadata2)
    assert metadata2["User"] == 'guidon'
    assert metadata2["Node_id"] == str(id)
    assert metadata2["Boom-Boom"] == str(42.0)

def test_sub_folders(s3_client, bucket, text_files):
    bucket_sub_folder = str(uuid.uuid4())
    filepaths = text_files(3)
    counter = 1
    for f in filepaths:
        object_name = bucket_sub_folder + "/" + str(counter)
        assert s3_client.upload_file(bucket, object_name, f)
        counter += 1

def test_search(s3_client, bucket, text_files):
    s3_client.create_bucket(bucket, delete_contents=True)
    
    metadata = [ {'User' : 'alpha'}, {'User' : 'beta' }, {'User' : 'gamma'}]

    for i in range(3):
        bucket_sub_folder = "Folder"+ str(i+1)

        filepaths = text_files(3)
        counter = 0
        for f in filepaths:
            object_name = bucket_sub_folder + "/" + "Data" + str(counter)
            assert s3_client.upload_file(bucket, object_name, f, metadata=metadata[counter])
            counter += 1

    query = "DATA1"
    results = s3_client.search(bucket, query, recursive = False, include_metadata=False)
    assert len(results) == 0

    results = s3_client.search(bucket, query, recursive = True, include_metadata=False)
    assert len(results) == 3

    query = "alpha"
    results = s3_client.search(bucket, query, recursive = True, include_metadata=True)
    assert len(results) == 3

    query = "dat*"
    results = s3_client.search(bucket, query, recursive = True, include_metadata=False)
    assert len(results) == 9

