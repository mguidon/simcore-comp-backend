from minio import Minio
from minio.error import ResponseError

try:
    minioClient = Minio('osparc01.speag.com:10001',
        access_key='pNPLM9cpcvweLRVRXfRN',
        secret_key='JxkgxhmvuXpbMxnxeahyCHT4bMUXttAp',
        secure=False)
except ResponseError as err:
    print(err)

if minioClient.bucket_exists("guidon"):
    minioClient.remove_bucket("guidon")

minioClient.make_bucket("guidon")



buckets = minioClient.list_buckets()
for bucket in buckets:
    print(bucket.name, bucket.creation_date)
#minioClient.make_bucket("guidon2", location='eu-central-1')


    