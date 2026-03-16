set dotenv-load

# List of commands
default:
    @just --list


# Backend commands
install:
    uv sync --all-packages

# Start client locally
[working-directory: 'client']
start:
    uv run --package client python -m sm_client
