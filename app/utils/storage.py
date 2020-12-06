import os


def upload_to_gs(bucket, bucket_dir_name, local_file_path):
    basename = os.path.basename(local_file_path)
    blob_name = '{}/{}'.format(bucket_dir_name, basename)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_file_path)
    return blob.public_url
