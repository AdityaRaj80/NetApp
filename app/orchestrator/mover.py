import os
from pathlib import Path
from typing import Iterable, Optional

from storage_clients.s3_client import S3Client
from storage_clients.azure_client import AzureClient
from storage_clients.gcs_client import GCSClient
from security import security_manager

S3_BUCKET = os.getenv("S3_BUCKET","netapp-bucket")
GCS_BUCKET = os.getenv("GCS_BUCKET","netapp-gcs")

s3 = S3Client()
az = AzureClient()
gcs = GCSClient()

def ensure_buckets():
    # S3 is required for seeds
    try:
        s3.ensure_bucket(S3_BUCKET)
    except Exception:
        pass

    # Best-effort for others; don't crash on failures
    try:
        az.ensure_container("netapp-blob")
    except Exception:
        pass
    try:
        gcs.ensure_bucket(GCS_BUCKET)
    except Exception:
        pass


def put_seed_objects(seed_dir: str):
    p = Path(seed_dir)
    for fp in p.glob("*.txt"):
        key = fp.name
        body = fp.read_bytes()
        encrypted = security_manager.encrypt("s3", body, {"system"})
        s3.put_object(S3_BUCKET, key, encrypted)

def move_object(
    obj_key: str,
    src: str,
    dst: str,
    principal_roles: Optional[Iterable[str]] = None,
):
    """
    Copy between emulated clouds; delete source after copy (simulate move).
    Locations: "s3", "azure", "gcs"
    """
    data = None
    if src == "s3":
        data = s3.get_object(S3_BUCKET, obj_key)
    elif src == "azure":
        data = az.get_blob("netapp-blob", obj_key)
    elif src == "gcs":
        data = gcs.get_object(GCS_BUCKET, obj_key)
    else:
        raise ValueError("unknown src")

    if data is None:
        raise FileNotFoundError(f"{obj_key} not found in {src}")

    roles = principal_roles if principal_roles is not None else {"system"}
    plaintext = security_manager.decrypt(src, data, roles)
    encrypted = security_manager.encrypt(dst, plaintext, roles)

    if dst == "s3":
        s3.put_object(S3_BUCKET, obj_key, encrypted)
    elif dst == "azure":
        az.put_blob("netapp-blob", obj_key, encrypted)
    elif dst == "gcs":
        gcs.put_object(GCS_BUCKET, obj_key, encrypted)
    else:
        raise ValueError("unknown dst")

    # delete source
    if src == "s3":
        s3.delete_object(S3_BUCKET, obj_key)
    elif src == "azure":
        az.delete_blob("netapp-blob", obj_key)
    elif src == "gcs":
        gcs.delete_object(GCS_BUCKET, obj_key)
