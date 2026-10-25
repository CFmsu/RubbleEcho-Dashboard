# Model provenance

A catalog request and a short completion both returned HTTP 200 from this machine. No reasoning completion has been stored as a trial result.

| Field | Value |
| --- | --- |
| Provider | Nebius Token Factory |
| Base URL | `https://api.tokenfactory.nebius.com/v1/` |
| Key path | `backend/.env` only. `backend/.env.example` stays blank. |
| Catalog | HTTP 200. Five NVIDIA ids were listed: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3.5-Super-VL`. |
| Selected model | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` in the local env. It is a text model. The vision id is not selected. |
| Switch | `AI_ENABLED=true` in `backend/.env` |
| Completion probe | HTTP 200. Returned model id matched the selected Nano model. With `max_tokens` 16 the visible `content` was empty because the reply used a `reasoning` field. With `max_tokens` 64, `content` was present. |
| Client | `reason_live` requests 900 completion tokens. If `content` is empty, it reads one JSON object from the `reasoning` field. A reply still has to pass the local schema before the dashboard marks it NVIDIA. |
| Modalities tested | Text only. Do not attach images or claim the model heard a WAV. |

The dashboard still labels a reply NVIDIA only after a live call returns and passes the local schema. A valid reply cannot set motor speed or fire the solenoid.

The key was removed from `backend/.env.example`. That example file is kept by git, so the pasted key should be rotated in the Nebius console.
