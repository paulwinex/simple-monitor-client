set dotenv-load

# List of commands
default:
    @just --list


# Backend commands
install:
    uv sync --all-packages

# Start client locally
start:
    uv run -m sm_client


build:
    uv run nuitka --standalone --onefile --output-dir=build --remove-output sm_client