# Model provenance

No Nebius call has been made from this working tree.

| Field | Value |
| --- | --- |
| Provider | Nebius Token Factory, OpenAI-compatible HTTPS API |
| Base URL | `https://api.tokenfactory.nebius.com/v1/` |
| Model id | Unset. It must be an NVIDIA model id from the account catalog. |
| Key path | `backend/.env` variable `NEBIUS_API_KEY`, or the repo-root `.env` if that is the file the process loads |
| Switch | `AI_ENABLED=false` until the key and model id are present |
| Evidence | None. `/api/ai/healthcheck` returns `NOT_CONFIGURED` and does not open a socket. |
| Modalities tested | None. Do not attach images or claim the model heard a WAV. |

The dashboard advisory without a live call is the local rule-based readout. It is not an NVIDIA response. A valid model reply still cannot set motor speed or fire the solenoid.
