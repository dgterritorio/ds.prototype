# Intro

A webdav interface for S3 volumes.

Python based webdav server at [wsgidav](https://github.com/mar10/wsgidav).

Code developed for wsdidav version: `v4.3.3`.

Python version: `3.12.7` (source build with pyenv).

This S3-wsgidav implementation was tested with WUR (unsigned and global bucket) and OVH (signed and regional bucket). Important to understand that a global bucket like the WUR implementation (no regions) is also an unsigned bucket. Even if an object is public is may requre signed/unsiged acess.

## Pyenv for development

Local pyenv environment for development:

First clone the repo:

```bash
git clone https://git.wur.nl/isric/soilgrids/s3webdav
cd s3webdav
```

pyenv install without sqlite3:

```bash
# on s3webdav dir
pyenv upgrade
export PYENV_PYTHON_VERSION=3.12.7
PYTHON_CONFIGURE_OPTS=" --enable-optimizations --with-lto" CPPFLAGS="-march=native -O3" CFLAGS="-march=native -O3" CXXFLAGS=${CFLAGS} pyenv install -v $PYENV_PYTHON_VERSION
pyenv virtualenv 3.12.7 s3webdav # set virtualenv
```

## Docker build

To make a docker build:

```bash
docker build --progress=plain --no-cache -t dgt/s3.webdav:0.0.2 -f Dockerfile .
```

## Env variables

For proper docker run it is necessary the following envs.

```bash
# Avoid ""
ENV AWS_ACCESS_KEY_ID=72<REMOVED>
ENV AWS_SECRET_ACCESS_KEY=eb<REMOVED>
ENV AWS_S3_ENDPOINT=https://s3.de.io.cloud.ovh.net
ENV AWS_S3_BUCKET=soilgrids
ENV AWS_S3_SUBPATH=latest/data/
ENV AWS_S3_REGION=de
ENV AWS_S3_SIGNATURE_VERSION=s3v4
ENV AWS_EC2_METADATA_DISABLED=true
```

`IMPORTANT`: WUR bucket just remove the env variable `AWS_S3_REGION` (dont use it), and webdav will become region agnostic. The `AWS_S3_SIGNATURE_VERSION` will also be discarted if `AWS_S3_REGION` is not present, as signature is not used with global buckets.

`IMPORTANT`: The env variable `AWS_S3_SUBPATH` sets the subpath inside the S3 bucket that the webdav will see as the **root directory** (parent directory of all subfolders). No need o include "/" at start and **end of path with** "/", f  variable set to "" or not present wsgidav will with the root of the S3 bucket.

The `AWS_S3_ENDPOINT` is just the URL of the system containing the buckets. The S3 client implements `https://<AWS_S3_ENDPOINT>/<AWS_S3_BUCKET>` for acess and then `Filter=AWS_S3_SUBPATH`.

`AWS_EC2_METADATA_DISABLED=true` is necessary for s3 client to skip connecting to AWS metadata server (normally located on: `169.254.169.254`). Important for this env variable to be always on `.env/secrets` and true

## Yaml config

wsgidav implements a generic `./config/wsgidav.yaml` where we can define different endpoints and paths. The S3 provider is very simple and doesnt accept any arguments. Only needed the path webdav path  (e.g "/") and the class to be used as provider `wsgidav.aws_s3_provider.S3Provider` (basic python import).

```yaml
# For local file
provider_mapping:
    "/":
        root: "/data"
# For S3 bucket
provider_mapping:
    "/":
        class: wsgidav.aws_s3_provider.S3Provider        
```

`IMPORTANT NOTE`:
We have only ONE provider per folder level, wsgidav will only call the provider when it needs to access the folders contents.
Only when we call `https://localhost:8080/` we will see the S3 bucket contents. And we need to implement a small trick that we need to create a soilgids.s3 folder on the file system with nothing so that on `https://localhost:8080/` we can see the `soilgrids.s3` dummy folder:

```bash
Name  Type Size  Last modified
latest Directory -
other Directory -
public Directory -
```

Password setting follows the default webdav approach configuration and cos:

```yaml
# Additional options for SimpleDomainController only:
simple_dc:
    # Access control per share.
    # These routes must match the provider mapping.
    # NOTE: Provider routes without a matching entry here, are inaccessible.
    user_mapping:
        "/": true    
#        "/projects/smos":
#            "glosis2":
#                password: "soil4live"
```

### Yaml config DEBUG

Debbuging is implemented in the yaml config file [wsgidav.yaml](./wsgidav.yaml). On the yaml file we have:

```yaml
#: Set verbosity level (but will be overridden by -v or -q arguments)
#: 0 critical, 1 error, 2 warn, 3 info, 4 debug
verbose: 3

logging:
    #: Set logging output format
    #: (see https://docs.python.org/3/library/logging.html#logging.Formatter)
    logger_date_format: '%H:%M:%S'
    logger_format: '%(asctime)s.%(msecs)03d - %(levelname)-8s: %(message)s'
    # Example: Add date,thread id, and logger name:
    # logger_date_format: '%Y-%m-%d %H:%M:%S'
    # logger_format: '%(asctime)s.%(msecs)03d - <%(thread)05d> %(name)-27s %(levelname)-8s: %(message)s'
```

The yaml files sets the debug level for wsgidav but also for boto3, with `verbose: 4` the console will also have the **boto3 connection information**.

## Docker run

These can be set on a local `.env` for development or using kustomize on the k8s. We now have a local test folder.

or:

```bash
docker run -v `pwd`/mnt/data/DGT/dgt-756:/data -v `pwd`/config:/config -p8080:8080 dgt/s3.webdav:0.0.2`
```

Where `/mnt/data/DGT/dgt-756` is we store local file for serving

Docker run will implement:

```Dockerfile
CMD ["wsgidav","--config", "/config/wsgidav.yaml"]
```

With provider being called on the yaml file.
