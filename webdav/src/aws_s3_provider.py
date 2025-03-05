import os
import boto3
import botocore
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore import UNSIGNED
import awscrt
import logging
from wsgidav import util
from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVNonCollection
from wsgidav.dav_error import DAVError
from cachetools import LRUCache
import threading

_logger = util.get_module_logger(__name__)  # wsgidav.aws_s3_provider

# Check the current effective logging level
if _logger.getEffectiveLevel() == logging.DEBUG:
    boto3.set_stream_logger("boto3.resources", logging.DEBUG)
    boto3.set_stream_logger("botocore", logging.DEBUG)
    _logger.debug("Boto3 and botocore debug logging has been enabled.")

_logger.debug("This is a debug message, you only see this if DEBUG is set")

# Global script variables no need to implement them  as os envs
CACHE_MAX_SIZE = 10000
AWS_S3_MAX_KEYS = 10000  # default and max? S3 pagination value

# Global shared cache for all instances
shared_resource_cache = LRUCache(maxsize=CACHE_MAX_SIZE)
cache_lock = threading.Lock()

class StreamingBodyWrapper:
    """A wrapper for botocore.response.StreamingBody to mix a forward-only .seek() into a readable stream."""

    def __init__(self, sb):
        """Initialize the StreamingBodyWrapper with a StreamingBody instance."""
        assert isinstance(sb, botocore.response.StreamingBody)
        self.sb = sb
        self.pointer = 0

    def __del__(self):
        """Ensure the streaming body is closed when the wrapper is deleted."""
        self.sb.close()

    def read(self, size=-1):
        """Read data from the streaming body."""
        if size <= 0:
            r = self.sb.read()
        else:
            r = self.sb.read(amt=size)
        self.pointer += len(r)
        return r

    def __getattr__(self, name):
        """Warn and raise an AttributeError for unexpected attribute access."""
        _logger.warning(f"ga({name!r}) was called unexpectedly")
        raise AttributeError(name)

    def seek(self, position):
        """Implement a forward-only seek."""
        assert position >= self.pointer
        r = self.sb.read(amt=position)
        position -= len(r)
        while position:
            r = self.sb.read(amt=position)
            position -= len(r)

    def close(self):
        """Close the streaming body."""
        return self.sb.close()


class S3Resource(DAVNonCollection):
    """A DAV resource representing a single S3 object."""

    def __init__(self, path, environ, bucket, key, s3_client, subpath):
        """Initialize the S3Resource with path, environment, S3 bucket, key, client, and subpath."""
        super().__init__(path, environ)
        self.bucket = bucket
        self.path = path
        self.key = os.path.join(subpath, key)
        self.client = s3_client
        try:
            self.s3_metadata = self.client.head_object(Bucket=self.bucket, Key=self.key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise DAVError(404, f"Resource {path} not found") from e
            _logger.error(f"Unexpected error fetching metadata for {self.key}: {e}")
            raise DAVError(500, f"Internal server error: {e}") from e
    # This keeps an HTTP connection open that of could it will make an OOM
        #self.s3_object = self.client.get_object(Bucket=self.bucket, Key=self.key)

    def get_content_length(self):
        """Return the content length of the S3 object."""
        return self.s3_metadata["ContentLength"]
        #return self.s3_object["ContentLength"]

    def get_content_type(self):
        """Return the content type of the S3 object."""
        return self.s3_metadata.get("ContentType", "application/octet-stream")
        #return self.s3_object["ContentType"]

    def get_display_name(self):
        """Return the display name of the S3 object."""
        return self.key.split("/")[-1]

    def get_content(self):
        """Return the content of the S3 object as a streaming body."""
        range_header = self.environ.get("HTTP_RANGE", None)
        if range_header:
            _logger.debug(f"Handling HTTP_RANGE: {range_header}")
            s3_object = self.client.get_object(
                Bucket=self.bucket, Key=self.key, Range=range_header
            )
        else:
            s3_object = self.client.get_object(Bucket=self.bucket, Key=self.key)
        # Update s3_metadata with the latest object metadata
        #self.s3_metadata = s3_object
        self.s3_metadata = s3_object if not range_header else self.s3_metadata
        return StreamingBodyWrapper(s3_object["Body"])
        
        #older 1
        #s3_object = self.client.get_object(Bucket=self.bucket, Key=self.key)
        #return StreamingBodyWrapper(s3_object["Body"])
        
        # older 2
        #return StreamingBodyWrapper(self.s3_object["Body"])

    def get_etag(self):
        """Return the ETag of the S3 object."""
        #return self.s3_object["ETag"].strip('"').strip("'")
        return self.s3_metadata["ETag"].strip('"').strip("'")

    def get_last_modified(self):
        """Return the last modified timestamp of the S3 object."""
        #return self.s3_object["LastModified"].timestamp()
        return self.s3_metadata["LastModified"].timestamp()
    
    def get_creation_date(self):
        """Return the creation date of the S3 object (same as last modified)."""
        return self.get_last_modified()

    def support_etag(self):
        """Indicate whether ETag is supported (not supported in this implementation)."""
        return True

    def support_ranges(self):
        return True

    
    # Support call methods, check fs_dav_provider.py for full list and implementation example


class S3Collection(DAVCollection):
    """A DAV collection representing a directory-like structure in an S3 bucket."""

    def __init__(self, path, environ, bucket, listing, s3_client, subpath):
        """Initialize the S3Collection with path, environment, S3 bucket, listing, client, and subpath."""
        super().__init__(path, environ)
        self.bucket = bucket
        self.listing = listing
        self.prefix = os.path.join(subpath, path.lstrip("/"), "")
        self.client = s3_client

    def get_member_names(self):
        """Return the names of the members (files and subdirectories) in this collection."""
        seen = set()
        members = []
        prefix_len = len(self.prefix)

        for obj in self.listing:
            if self.prefix in obj["Key"]:
                key = obj["Key"][prefix_len:].strip("/")
                parts = key.split("/")

                if len(parts) > 1:
                    dir_name = parts[0]
                    if dir_name not in seen:
                        seen.add(dir_name)
                        members.append(dir_name + "/")
                else:
                    members.append(parts[0])
        return members


class S3Provider(DAVProvider):
    """A WsgiDAV provider for serving files from an S3 bucket."""

    def __init__(self):
        """Initialize the S3Provider with environment variables."""
        super().__init__()
        self.endpoint_url = os.getenv("AWS_S3_ENDPOINT", None)
        self.bucket = os.getenv("AWS_S3_BUCKET", None)
        self.region = os.getenv("AWS_S3_REGION", None)
        self.subpath = os.getenv("AWS_S3_SUBPATH", "").lstrip("/")
        self.sig_version = os.getenv("AWS_S3_SIGNATURE_VERSION", None)
        self.sig_version = (
            self.sig_version if self.sig_version in ["s3v4", "s3", "unsigned"] else None
        )

        _logger.info("Initiating S3 client")
        _logger.info(f"Using AWS_S3_ENDPOINT:{self.endpoint_url}")
        _logger.info(f"Using AWS_S3_BUCKET:{self.bucket}")
        _logger.info(f"Using AWS_S3_REGION:{self.region}")
        _logger.info(
            f"Using AWS_S3_SUBPATH: {self.subpath}"
            if self.subpath
            else "AWS_S3_SUBPATH is not implemented. Using root of bucket"
        )
        _logger.info(
            f"Using AWS_S3_SIGNATURE_VERSION: {self.sig_version}"
            if self.sig_version
            else "NO SIGNATURE specified implementing unsigned access to S3"
        )

        self.config = self.get_s3_config()
        self.client = self.get_s3_client()
        #self.resource_cache = LRUCache(maxsize=CACHE_MAX_SIZE)
        self.object_cache = None  # Cache for S3 objects

    def get_s3_config(self):
        """Create and return the S3 client configuration."""
        if self.region:
            _logger.info(
                f"Processing with signed implementation: {self.sig_version} and region: {self.region}"
            )
            config_params = {
                #retries: {"mode": "legacy",  "max_attempts": 3 },
                "retries": {"max_attempts": 5, "mode": "adaptive"},
                "connect_timeout": 10,
                "read_timeout": 10,
                "region_name": self.region,
                "signature_version": self.sig_version,
                "use_dualstack_endpoint": False,
                "max_pool_connections": 200,
                "use_fips_endpoint": False,
                "s3": {
                    "use_accelerate_endpoint": False,
                    "payload_signing_enabled": True,
                    "use_global_endpoint": False,
                    "use_arn_region": True,
                    "addressing_style": "path",
                },

            }
        else:
            _logger.info(f"Implementing unsigned simple conf, global regions")
            config_params = {"signature_version": UNSIGNED}

        return Config(**config_params)

    def get_s3_client(self):
        """Initialize and return the S3 client."""
        try:
            import awscrt

            _logger.info("Using C-based parser provided by awscrt")
            session = boto3.session.Session()
            client_config = self.config
            client_config.use_awscrt = True
            s3 = session.client(
                service_name="s3",
                endpoint_url=self.endpoint_url,
                config=client_config,
            )
        except ImportError:
            _logger.warning(
                "awscrt package is not installed. Falling back to the default parser."
            )
            session = boto3.session.Session()
            s3 = session.client(
                service_name="s3", endpoint_url=self.endpoint_url, config=self.config
            )

        return s3

    def list_objects_once(self):
        """Fetch and cache the list of objects in the specified subpath."""
        if self.object_cache is None:
            self.object_cache = self.list_all_objects(
                self.client, self.bucket, self.subpath
            )
        return self.object_cache

    def get_resource_inst(self, path, environ):
        """Return a DAV resource instance for the given path."""
        directory_path = path.lstrip("/")
        cache_key = path

        # Check if this is a range request
        is_range_request = "HTTP_RANGE" in environ

        # Try to fetch from cache regardless of request type
        cached_resource = shared_resource_cache.get(cache_key)
        if cached_resource:
            _logger.debug(f"Cache hit for: {path}")
            if is_range_request:
                # Use the cached resource without updating or modifying it
                _logger.debug(f"Using cached resource read-only for range request: {path}")
                return cached_resource
            return cached_resource

        # Cache miss: Proceed to fetch the resource
        all_objects = self.list_objects_once()
        prefix = os.path.join(self.subpath, directory_path)
        matching_objects = [obj for obj in all_objects if obj["Key"].startswith(prefix)]
        key_count = len(matching_objects)

        common_prefixes = set()
        for obj in matching_objects:
            relative_key = obj["Key"][len(directory_path):]
            if "/" in relative_key:
                common_prefix = relative_key.split("/", 1)[0] + "/"
                common_prefixes.add(common_prefix)

        is_directory = bool(common_prefixes) or key_count > 1

        try:
            if is_directory:
                listing = self.fetch_directory_listing(path)
                resource = S3Collection(
                    path, environ, self.bucket, listing, self.client, self.subpath
                )
            else:
                resource = S3Resource(
                    path,
                    environ,
                    self.bucket,
                    path.lstrip("/"),
                    self.client,
                    self.subpath,
                )
        except DAVError as e:
            if e.value == 404:
                _logger.info(f"Resource {path} not found, returning 404")
                raise e  # Propagate 404
            _logger.error(f"Unexpected DAVError while getting resource for {path}: {e}")
            raise DAVError(500, "Internal server error") from e

        # Add to cache only for non-range requests
        if not is_range_request:
            _logger.debug(
                f"Adding resource: {str(resource)} with key: {cache_key} to cache"
            )
            with cache_lock:
                shared_resource_cache[cache_key] = resource
                _logger.debug(f"Added {path} to cache and releasing lock")

        return resource

    def fetch_directory_listing(self, path):
        """Fetch and return the directory listing for the given path."""
        all_objects = self.list_objects_once()
        directory_path = path.lstrip("/")
        prefix = os.path.join(self.subpath, directory_path)
        matching_objects = [obj for obj in all_objects if obj["Key"].startswith(prefix)]
        return matching_objects

    def list_all_objects(self, s3_client, bucket_name, prefix, max_keys=1000):
        """List all objects in the specified S3 bucket and prefix, handling pagination."""
        objects = []
        continuation_token = None

        while True:
            response = self.list_objects_v2_with_continuation(
                s3_client, bucket_name, prefix, max_keys, continuation_token
            )
            if "Contents" in response:
                objects.extend(response["Contents"])

            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        return objects

    def list_objects_v2_with_continuation(
        self, s3_client, bucket_name, prefix, max_keys, continuation_token=None
    ):
        """List objects in the specified S3 bucket and prefix, handling continuation tokens."""
        if continuation_token:
            _logger.debug(
                f"Implementing continuation token: {continuation_token}, max_keys: {max_keys}"
            )
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
                ContinuationToken=continuation_token,
            )
        else:
            _logger.debug(f"No continuation token, max_keys: {max_keys}")
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, Prefix=prefix, MaxKeys=max_keys
            )
        _logger.debug(f"list_objects_v2 Response: {response}")
        return response