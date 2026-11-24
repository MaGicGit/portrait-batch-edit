# Repository rules

- Never call OpenAI Platform APIs. No `OPENAI_API_KEY`, API SDK, or hidden backend endpoints.
- GPT vision analysis must be performed by the active Codex conversation through its supported image-viewing capability.
- Never modify `.lrcat` files directly.
- Never modify or overwrite source RAW/JPEG files.
- Only apply Develop settings to Lightroom virtual copies created after explicit user confirmation.
- First create representative preview virtual copies; wait for user review before full-batch application.
- Keep local mask suggestions separate from global Develop settings. Do not invent undocumented mask payloads.
- Preserve source file paths exactly; do not match photos by basename alone where duplicates may exist.
- All Python output must be deterministic and testable.
- Use conservative adjustments and clamp every Develop value to configured bounds.
- Never delete photos, virtual copies, sidecars, or previews automatically.
