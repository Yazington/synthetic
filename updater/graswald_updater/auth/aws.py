from .auth import Authentication

import boto3
import json
import base64


class AWS(Authentication):

    def __init__(self,
                 aws_s3_uri=str,
                 aws_user_access_key_id=str(""),
                 aws_user_secret_access_key=str(""),
                 aws_secretsmanager_secret_name=str(""),
                 aws_secretsmanager_region_name=str(""),
                 **args) -> None:
        super().__init__()

        self.bucket_name = aws_s3_uri.split("/")[2]
        self.directory = "/".join(aws_s3_uri.split("/")[3:])
        self.aws_user_access_key_id = aws_user_access_key_id
        self.aws_user_secret_access_key = aws_user_secret_access_key

        self.aws_secretsmanager_secret_name = aws_secretsmanager_secret_name
        self.aws_secretsmanager_region_name = aws_secretsmanager_region_name

        if (self.aws_user_access_key_id != "" and self.aws_user_secret_access_key != ""):
            self.s3 = boto3.client('s3',
                                   aws_access_key_id=self.aws_user_access_key_id,
                                   aws_secret_access_key=self.aws_user_secret_access_key)
        else:
            if (self.aws_secretsmanager_secret_name != "" and self.aws_secretsmanager_region_name != ""):
                try:
                    # New Rolling-Secrets
                    self.s3 = self.__login__(self.aws_secretsmanager_secret_name, self.aws_secretsmanager_region_name)
                except Exception as e:
                    raise RuntimeWarning(f"Could not get secrets for checking Updates: {e}")
            else:
                raise RuntimeError("No Aws secret_name or aws region_name give for Rollover Keys")
            raise RuntimeError("No Aws secrets given")

    def __login__(self, secret_name, region_name):
        # Create a Secrets Manager client
        try:
            secrets_client = boto3.client("secretsmanager", region_name=region_name)
            # Retrieve the secret value
            response = secrets_client.get_secret_value(SecretId=secret_name)
            # # Parse the secret value JSON
            secret = json.loads(response["SecretString"])

            # Decode the access key and secret key from base64
            access_key = base64.b64decode(secret["access_key"]).decode("utf-8")
            secret_key = base64.b64decode(secret["secret_key"]).decode("utf-8")
        except Exception as e:
            raise RuntimeWarning(f"Could not get secrets for checking Updates: {e}")

        # Create an S3 client object
        try:
            s3 = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)
            pass
        except Exception as e:
            raise RuntimeWarning(f"Could not sign into AWS: {e}")

        return s3

    def __progress_callback(self, bytes_amount):
        self.progress_current += bytes_amount
        # Update the progress_total if it's not yet set
        if self.progress_total == 0:
            self.progress_total = self.s3.head_object(self.bucket_name, self.object_key)['ContentLength']
        # Call the progress event with the updated values
        self.progress_handler(self.progress_current, self.progress_total)

    def download_file(self, url, destination, progress_handler, cancelled_event):
        """
        url is used as the object key value for S3 buckets
        """
        self.object_key = url
        
        self.progress_current = 0
        self.progress_total = 0
        self.progress_handler = progress_handler

        self.cancel_download = False
        
        def cancel_download():
            self.cancel_download = True
        cancelled_event.add_handler(cancel_download)

        try:
            future = self.s3.download_file(self.bucket_name, self.object_key, destination, Callback=self.__progress_callback)

            # Wait for the download to complete or cancellation to be requested
            while not future.done():
                pass

            if self.cancel_download:
                future.cancel()  # Cancel the ongoing download
                return False
        except Exception as e:
            raise RuntimeWarning(f"Could not sign into AWS: {e}")

        return True

    def get_versions_info(self):
        object_key = f"{self.directory}/latest_versions.json"
        #response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=self.directory)
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=object_key)
            file_content = response["Body"].read().decode("utf-8")
            versions_info = file_content
            return versions_info
        except RuntimeError:# as e:
            # print(f"Error occurred while getting json: {str(e)}")
            ...
