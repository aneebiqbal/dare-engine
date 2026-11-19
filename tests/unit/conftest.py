"""Unit tests are hermetic: never inherit a host bridge from .env, and never
wait on the network for a model that is already cached."""
import os

# pydantic-settings gives the environment precedence over .env, so an empty
# value here keeps the worker's MLX bridge off unless a test opts in.
os.environ["MLX_WHISPER_URL"] = ""
# faster-whisper would otherwise phone home to check the hub even when the
# model is cached; that turns a slow CPU test into a hung one.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
