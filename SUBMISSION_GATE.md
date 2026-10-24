# Submission gate

| Condition | Status | Evidence |
| --- | --- | --- |
| Physical AI track software runs locally | PASS | `pytest` in `backend`; `npm run build` in `frontend` |
| Public repository | PASS | Existing GitHub remote `CFmsu/RubbleEcho-Dashboard` |
| OSI license file | PASS, confirm with the team | `LICENSE` is MIT. The brief requested an open-source license; the team should confirm MIT before submission |
| README with run steps | PASS | `README.md` |
| Real Nebius Token Factory call with an NVIDIA model | FAIL | No API key in this session. See `docs/NEBIUS_NVIDIA_EVIDENCE.md` |
| Working hardware footage, at least 60 seconds, public YouTube video under 3 minutes | FAIL | No hardware was attached. `docs/DEMO_SCRIPT.md` is a script, not a published video |
| Devpost copy | PARTIAL | `docs/DEVPOST_SUBMISSION.md` has copy. Video link and team roster are placeholders |
| Claims match evidence | PASS | UI badges and device rows stay disconnected or replay until a real sample exists |
| Secrets out of git | PASS | `.env.example` has empty values. `.gitignore` ignores `.env` |
| Significant update after 2026-08-26 | PASS | This branch adds the sand-table contract, replay, safety gate, and operations UI |

The human team still has to wire hardware, record the video, run the live model call, and confirm the license.
