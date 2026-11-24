# Outdoor portrait editing policy

## Priority order
1. Preserve identity, facial proportions, natural skin texture, and believable color.
2. Correct obvious exposure and white-balance issues.
3. Establish a coherent scene-level color direction.
4. Apply restrained per-photo refinements.
5. Suggest local adjustments separately for human review.

## Scene grouping
Group photos using capture time, location metadata when available, and visual similarity. Do not combine direct sun, open shade, backlight, and golden-hour images into one edit group merely because they were taken in the same session.

## Global editing guardrails
- Exposure: usually within ±0.7 EV unless the image clearly requires more.
- Highlights/Shadows/Whites/Blacks: moderate changes; avoid flattening the image.
- Texture/Clarity: small changes only for global settings.
- HSL: skin orange/red channels should be adjusted conservatively.
- Saturation: avoid global oversaturation.
- Sharpening/noise reduction: prefer camera/ISO-aware settings; do not invent aggressive values.

## Local adjustment proposal targets
- facial_skin: preserve pores and texture; avoid plastic skin.
- iris_pupil: subtle detail and exposure; do not brighten sclera unnaturally.
- hair: recover detail without creating halos.
- background: reduce distraction while retaining believable depth and ambient light.
- subject: subtle face/body exposure balance.

Local proposals are not applied by the current plugin.
