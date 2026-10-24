# Nebius and NVIDIA evidence

## Status of the live call

No live Token Factory call was made in this implementation session. `NEBIUS_API_KEY` was not present in the environment. The service therefore reports `NOT_CONFIGURED` and `nvidia_online: false`.

## Request path

- Code: `backend/app/ai/nebius_client.py` function `reason_live`.
- Client: `OpenAI(base_url=NEBIUS_BASE_URL, api_key=NEBIUS_API_KEY)`.
- Default base URL: `https://api.tokenfactory.nebius.com/v1/`.
- Endpoint used by that client: chat completions on the configured base URL.
- Model id: `NEBIUS_MODEL_ID`. The repository does not hardcode a guessed NVIDIA model id.
- `select_nvidia_model` accepts a catalog list and rejects ids that do not contain `nvidia` or `nemotron`.
- The browser never receives the key. `/api/ai/status` returns status and model id only.
- Live calls also require `RUBBLEECHO_AI_LIVE=1`, so a configured key is not used accidentally.
- Operator command: `py scripts/check_nebius.py --live` from the repository root after exporting the key and model id.

## Redacted live example

Not available. There is no request or response to redact until an operator runs the live check.

## Failure behavior

Invalid JSON, a non-allowlisted recommendation, HTTP 429, HTTP 500, and timeout are handled by `apply_model_result`. The tested behavior is a local safety hold, solenoid disarm, and `nvidia_online: false`. Unit coverage is in `backend/tests/test_ai_mock.py`.

## Feedback

ACTUAL OBSERVATION REQUIRED.

Onboarding, catalog latency, token cost, and output quality were not observed because the key was not available. Do not paste invented impressions into the Devpost form.
