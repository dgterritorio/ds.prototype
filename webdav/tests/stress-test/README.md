# Intro

Stress test for webdav using siege and urls of tiffs


## Generate URLs

Something like: `export NUM_URLS=20000 && python3 url_generator.py > urls.txt`

## Siege

To make a request using siege with auth it is necessary to code `user:password`

```bash 
echo -n "admin:3<REMOVED>" | base64
YWRt<REMOVED>
```

Then:

`siege -c 10 -r 10 -H "Authorization: Basic YWRt<REMOVED>" -f urls.txt -i -b`

10 concurrent users, and each with 10 requests (100 in total) 
