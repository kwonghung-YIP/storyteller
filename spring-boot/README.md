```bash
curl -v -X GET \
    localhost:8080/story

curl -v -X POST \
    -H "Content-Type: text/plain" \
    -d 'tell me a fairy tale about Spongebob fall in love for litte pony.' \
    localhost:8080/story
```