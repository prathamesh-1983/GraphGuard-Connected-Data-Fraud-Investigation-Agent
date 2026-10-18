services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: graphguard-falkordb
    ports:
      - "6379:6379"
      - "3000:3000"
    restart: unless-stopped
