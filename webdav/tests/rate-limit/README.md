# Intro 

Sige testing support files or information

## Url generator

Example of command to generate random urls from specific section folder

`seq -f "https://dadosabertos.dgterritorio.gov.pt/webdav/ortos/ortosat2023/1_OrtoSat2023_CorVerdadeira/1_Seccoes_OrtoSat2023_CorVerdadeira/Seccoes_0400/OrtoSat2023_%04g_CorVerdadeira.tif" 400 499 | shuf > urls.txt`


## Rate limit

Curent rate limit imposed on docker-compose label / traefik

```yaml
    labels:
      - "traefik.http.routers.webdav.rule=Host(`${BASE_URL}`) && PathPrefix(`/webdav`)"
      - "traefik.http.routers.webdav.service=webdav"
      - "traefik.http.routers.webdav.middlewares=traefik-auth,webdav-ratelimit"
      - "traefik.http.services.webdav.loadbalancer.server.port=8080"
      - "traefik.http.routers.webdav.entrypoints=https"
      - "traefik.http.routers.webdav.tls=true"
      - "traefik.http.routers.webdav.tls.certresolver=letsencrypt"
      - "traefik.http.middlewares.webdav-ratelimit.ratelimit.average=10"
      - "traefik.http.middlewares.webdav-ratelimit.ratelimit.burst=20"

```

## Tests

Tests done with:

```yaml
      - "traefik.http.middlewares.webdav-ratelimit.ratelimit.average=1"
      - "traefik.http.middlewares.webdav-ratelimit.ratelimit.burst=2"
```

and then:

`cat urls.txt | xargs -P10 -I{} curl -s -o /dev/null -w "%{http_code}\n" "{}"`

The output will contain mainly `HTTP-429` and at the end a HTTP-200, this is the expected behaviour

Changing back to:

```yaml
      - "traefik.http.middlewares.webdav-ratelimit.ratelimit.average=10"
      - "traefik.http.middlewares.webdav-ratelimit.ratelimit.burst=20"
```

The results are all `HTTP-200`