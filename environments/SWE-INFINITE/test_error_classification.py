"""Direct exercise of _classify_agent_error against real-world error strings.

Run: python3 environments/SWE-INFINITE/test_error_classification.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env import _classify_agent_error


# (label, raw error string fed in, expected classification)
CASES = [
    # ---- context_exceeded (must NOT be retried) ----
    (
        "user-reported chute 400",
        "Input length (57719 tokens) exceeds the maximum allowed length "
        "(55539 tokens). Use a shorter input or enable --allow-auto-truncate.",
        "context_exceeded",
    ),
    (
        "litellm wrapped ContextWindowExceededError",
        "Traceback (most recent call last):\n"
        "  File '/x/litellm/llms/openai.py', line 200, in completion\n"
        "    response = openai.ChatCompletion.create(...)\n"
        "litellm.exceptions.ContextWindowExceededError: ContextWindowExceededError: "
        "OpenAIException - This model's maximum context length is 40000 tokens. "
        "However, your messages resulted in 41234 tokens.",
        "context_exceeded",
    ),
    (
        "vllm-style 400 wrapped in BadRequestError",
        "openai.BadRequestError: Error code: 400 - {'error': "
        "{'message': 'This model's maximum context length is 32768 tokens.', "
        "'type': 'BadRequestError'}}",
        "context_exceeded",
    ),

    # ---- agent_timeout (retryable) ----
    (
        "codex hit walltime cap",
        "Codex timed out after 1800s",
        "agent_timeout",
    ),
    (
        "command-level timeout fed up to evaluate",
        "subprocess.TimeoutExpired: Command timed out after 300s",
        "agent_timeout",
    ),

    # ---- api_error (retryable) ----
    (
        "auth failure",
        "openai.AuthenticationError: Error code: 401 - Unauthorized",
        "api_error",
    ),
    (
        "no matching chute",
        "RuntimeError: No matching chute available for this request",
        "api_error",
    ),
    (
        "transient connection error",
        "httpx.ConnectError: Connection refused while reaching chute",
        "api_error",
    ),
    (
        "evaluate() raised api_error already",
        "api_error: exit 1: Reconnecting to chute endpoint failed",
        "api_error",
    ),

    # ---- docker_error (retryable, container-loss path) ----
    (
        "ContainerLostError from miniswe path",
        "Traceback (most recent call last):\n"
        "  File '_BlacklistDockerEnv.execute', line 50, in execute\n"
        "ContainerLostError: docker container lost: "
        "Error response from daemon: No such container: e30fd46a1e0c",
        "docker_error",
    ),
    (
        "docker pull failed",
        "Failed to pull image: manifest unknown",
        "docker_error",
    ),
    (
        "out of disk",
        "RuntimeError: write /var/lib/docker/...: no space left on device",
        "docker_error",
    ),

    # ---- agent_error (NOT retried — model self-misbehavior) ----
    (
        "format error / agent quirks",
        "FormatError: Please always provide EXACTLY ONE action in triple backticks.",
        "agent_error",
    ),
    (
        "empty error",
        "",
        "agent_error",
    ),

    # ---- 429 / 5xx upstream pressure (retryable) ----
    (
        "rate limit 429",
        "openai.RateLimitError: Error code: 429 - too many requests",
        "api_error",
    ),
    (
        "chute 503 service unavailable",
        "openai.APIStatusError: Error code: 503 - Service Unavailable",
        "api_error",
    ),
    (
        "chute 502 bad gateway",
        "httpx.HTTPStatusError: 502 Bad Gateway",
        "api_error",
    ),

    # ---- regression: 'api' substring alone must NOT trigger api_error ----
    (
        "litellm traceback containing 'api' substring but no real signal",
        "Traceback ...\n  File '.../openai/_base_client.py', line 100\n"
        "ValueError: response payload malformed",
        "agent_error",
    ),
]


def main():
    width = max(len(label) for label, _, _ in CASES)
    failed = 0
    for label, raw, expected in CASES:
        got = _classify_agent_error(raw)
        ok = got == expected
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        first_line = (raw.splitlines() or [""])[0][:90]
        print(f"[{mark}] {label:<{width}}  expected={expected:<18} got={got:<18}  in={first_line!r}")
    print()
    print(f"{len(CASES) - failed}/{len(CASES)} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
