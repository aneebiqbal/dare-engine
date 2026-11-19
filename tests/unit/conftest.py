"""Unit tests are hermetic: never inherit a host bridge from .env."""
import os

# pydantic-settings gives the environment precedence over .env, so an empty
# value here keeps the worker's MLX bridge off unless a test opts in.
os.environ["MLX_WHISPER_URL"] = ""
