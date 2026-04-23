# docker-image-cleaner

[![CI](https://github.com/aleasoluciones/docker-image-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/aleasoluciones/docker-image-cleaner/actions/workflows/ci.yml)

Daemon that removes old Docker images, keeping only the N most recent per repository.

## Installation

### From .deb package
```bash
sudo dpkg -i bifer-docker-image-cleaner_*.deb
sudo systemctl enable docker-image-cleaner
sudo systemctl start docker-image-cleaner
```

### From binary
```bash
./docker-image-cleaner --help
```

## Examples

### Dry run (preview what will be deleted)
```bash
./docker-image-cleaner --oneshot --noop -v
```

### Delete all except the 5 most recent per repo
```bash
./docker-image-cleaner --oneshot -images-to-keep 5
```

### Keep `<none>` dangling images
```bash
./docker-image-cleaner --oneshot --keep-none-images
```

### Daemon mode (runs every 10 minutes)
```bash
./docker-image-cleaner -images-to-keep 2 --sleepDuration 10m
```

### Force delete (for images used by containers)
```bash
./docker-image-cleaner --oneshot --force
```

## Flags

| Flag | Default | Description |
|------|---------|--------------|
| `--oneshot` | false | Run once and exit (daemon mode by default) |
| `--images-to-keep` | 2 | Number of images to keep per repository |
| `--keep-none-images` | false | Keep `<none>` dangling images |
| `--force` / `-f` | false | Force delete (for images used by containers) |
| `--sleepDuration` | 5m | Time between runs (daemon mode) |
| `--debug` / `-d` | false | Debug logging |
| `--quiet` / `-q` | false | Suppress info messages |
| `-v` | false | Verbose output |

## Systemd Service

After installation, enable and start the service:

```bash
sudo systemctl enable docker-image-cleaner
sudo systemctl start docker-image-cleaner
sudo systemctl status docker-image-cleaner
```

## Development

```bash
# Check code (fmt, vet, staticcheck)
make check

# Compile
make compile

# Build .deb package
make package
```