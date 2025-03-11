# Intro

S3 bucket storage infrastructure for DGT and COG storage

Implementining docker image: [minio/minio:RELEASE.2024-11-07T00-52-20Z](https://hub.docker.com/layers/minio/minio/RELEASE.2024-11-07T00-52-20Z/images/sha256-d051d800a3025588f37f69f132bb5ef718547a9a4ee95ddee44e04ad952a0a96?context=explore).

## Docker compose

Docker compose runs 2 nodes working in a peer-to-peer approach, then it is necessay a load balancer, just for a single point access as Minio allows access to any node for admin or S3 bucket purpose.

Minio cluster needs a admin and pwd set in composition, this can be different from one node to another, but better for all of them to have the same credencials.

On an `.env` file:

```bash
MINIO_ROOT_USER=mende012
MINIO_ROOT_PASSWORD=9oi<REMOVED>
```

Each node needs a mount to a specific data volume, that should be XFS filesystem and on diferent disk.

```bash
volumes:
    - /mnt/minio/node1/data:/data
:
volumes:
    - /mnt/minio/node2/data:/data
```

### Docker compose run

NOTE: Need to add the `.env` file to the compose up

```bash
docker compose --env-file=.env up -d
```

### Load balancer

The nginx file uses `minio.local` as servername, so better to set it on `/etc/hosts`

```bash
127.0.0.1   minio.local
```
