import os
from azure.storage.blob import BlobServiceClient

AZURITE_BLOB_URL = os.getenv("AZURITE_BLOB_URL","http://azurite:10000/devstoreaccount1")
AZURITE_ACCOUNT  = os.getenv("AZURITE_ACCOUNT","devstoreaccount1")
AZURITE_KEY      = os.getenv("AZURITE_KEY","Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OU==")

class AzureClient:
    def __init__(self):
        # Azurite connection string format
        conn_str = (
            f"DefaultEndpointsProtocol=http;"
            f"AccountName={AZURITE_ACCOUNT};"
            f"AccountKey={AZURITE_KEY};"
            f"BlobEndpoint={AZURITE_BLOB_URL};"
        )
        self.bs = BlobServiceClient.from_connection_string(conn_str)

    def ensure_container(self, container: str):
        try:
            self.bs.create_container(container)
        except Exception:
            pass

    def put_blob(self, container: str, name: str, data: bytes):
        self.bs.get_blob_client(container=container, blob=name).upload_blob(data, overwrite=True)

    def get_blob(self, container: str, name: str) -> bytes | None:
        try:
            b = self.bs.get_blob_client(container=container, blob=name)
            return b.download_blob().readall()
        except Exception:
            return None

    def delete_blob(self, container: str, name: str):
        try:
            self.bs.get_blob_client(container=container, blob=name).delete_blob()
        except Exception:
            pass
