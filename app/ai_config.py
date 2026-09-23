"""Shared model defaults; environment overrides remain explicit deployment choices."""
import os


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def model_for(provider):
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-5.5")
    if provider == "nvidia":
        return os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
    return None  # Templates and mock rules do not invoke a model.


def openai_options():
    model = model_for("openai")
    options = {"model": model}
    if model.startswith("gpt-5"):
        options["reasoning"] = {"effort": os.getenv("OPENAI_REASONING_EFFORT", "low")}
    return options
