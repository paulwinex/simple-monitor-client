# Simple Monitor Client

Client app for Simple Monitor Service

### Install

1. Clone repository
2. Go to repository directory
3. Run command
```bash
# if just installed
just run
# or
uv run -m sm_client
```

### Collectors

- CPU
  - load percent
  - temperature
- RAM
  - usage percent
  - used Mb
  - available Mb
  - swap used Mb
  - temperature
- NET
  - upload speed
  - download speed
- Storages (HDD, SSD)
  - temperature
  - health (info form smart based on errors count)
  - used MB persent\bytes
  - free MB persent\bytes
- ZFS Pool
  - usage percent
  - total Mb
  - used Mb
  - free Mb
  - fragmentation percent
  - pool health
