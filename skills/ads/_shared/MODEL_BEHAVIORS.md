# Model Behaviors · cross-cutting gotchas

Observations about how the underlying generation models actually behave, gathered from shipped projects. These are **descriptions**, not creative prescriptions — knowing them helps you write prompts that get what you want, regardless of what you want.

Each entry names the model + the behavior + the workaround. None of these tell you what your ad should look like.

---

## Seedance 2.0 · `start_image` + `end_image` interpolation is back-loaded

When you pass both `start_image` and `end_image` to Seedance, the model holds the start's appearance through roughly the first 70-80% of the clip duration and converges to the end_image only in the final ~20-25%. Interpolation is NOT distributed evenly across the timeline.

**Implication for editing:** if you need a short slice of a 4-second Seedance clip and the start and end frames differ materially (different wardrobe, different location, different lighting), trim from the END (`trim=2:4`, taking the final 2 seconds). The middle of the clip looks almost identical to the start.

**Implication for prompt writing:** "transformation happens at the midpoint" type prompts are mostly ignored. The model converges where it converges.

---

## Seedance 2.0 · words that name transformations get rendered as transformations

Vocabulary like `morph`, `split`, `dissolve`, `transform`, `wipe`, `fade` tells Seedance to render the transformation as a *visible scene element* — often a split-screen composite with a seam, or an opacity blend, or a literal "two halves of the frame" composition. This is sometimes what you want (think highlight-reel transitions, music-video cuts).

It is NOT what you want when you're after a continuous camera move between two locations or wardrobes. For that, describe the **camera's physical path** instead — push-forward, dolly-back, whip-pan, tilt-down, arc-around, follow-through-doorway. Let the visual handoff between start and end frames happen as a side-effect of the camera move, not as the focus.

Both styles are valid creative choices. Just know which one you're prompting for.

---

## Seedance 2.0 · occlusions render at the scale you imply, not the scale you'd film

"The camera passes behind a column" with no spatial constraints renders the column at full-frame scale (because that's how the model interprets "passes behind" — a covering relationship between camera and object). A real film crew shooting that beat would put the column at the frame edge for ~0.3 seconds; Seedance puts it at the center for 1.5 seconds.

If you want a peripheral occlusion (any film-grammar trick where a foreground element briefly hides the subject — a passing pedestrian, a doorframe, a swinging sign), constrain three axes in the prompt:

- **Location**: `frame edge`, `right side`, `top-left corner`
- **Duration**: `under half a second`, `briefly sweeps`
- **Negation**: `NOT center`, `NOT blocking the subject`

Without the triple constraint the model defaults to making the occlusion the subject.

---

## Veo 3.1 (lite + high) · state descriptions produce static clips

Veo treats prompts like "A man's legs in jeans on a wet curb" as a still image with minimal incidental motion (light flicker, slight sway). If you want the clip to actually move, the prompt has to name actions: "STEPS off the curb," "PIVOTS reaching for a shelf," "TAPS the foot." Action verbs activate motion; state descriptions don't.

This isn't a rule about what your ad should depict — it's a fact about how the model parses prompts. A meditative still-life ad with Veo *should* use state descriptions (and accept the near-static result). A kinetic ad needs verbs.

---

## Veo 3.1 · `start_image` framing dominates

Whatever composition is in the start_image — angle, distance, what's in frame, what's cropped out — Veo will hold that composition through the clip with relatively minor camera movement. If the start_image shows a shoe in macro, the clip will be a shoe in macro with some motion. If the start_image shows a wide skyline, the clip will be a wide skyline with some motion.

**Implication:** your reference still does double duty. It's not just a *visual reference* for "what should be in the frame" — it's also the *compositional lock* for "what angle and distance the clip will be at." If the still doesn't show what you want the clip to show, the clip won't either.

---

## Nano Banana 2 · reference image dominance

When you pass a `medias[].role=image` reference (e.g. a product photo) to Nano Banana 2, the model treats that reference as a *style and identity anchor* for the named object, not as a layout constraint. Generated images will preserve the product's colorway, materials, and proportions accurately; they will NOT preserve the reference photo's framing, background, or pose.

**Implication:** great for "this exact product, but in a new scene." Less good for "this exact photo, but slightly different." If you need photo-faithful reproduction, use a different tool (or pass the reference more aggressively with prompt language like "exactly matching the reference").

---

## All AI video models · multi-clip concats color-drift

Two clips generated from the same model with the same "cool fluorescent grade" prompt will NOT actually match in color. Each generation interprets the grade subjectively. A 10-clip concat will have visible grade jumps at every boundary unless you apply a unifying ffmpeg pass after stitching.

The fix isn't a specific grade — it's a *harmonization* pass. Take whatever direction makes sense for your project (cool, warm, neutral, desaturated, high-contrast) and apply it to the full concatenated video as a final filter. Starting point that works for most projects:

```
eq=contrast=1.05:saturation=0.95, colorbalance=bs=0.05:bm=-0.02
```

Tune from there. The point isn't this specific filter — it's *that you apply one*.

---

## All AI image/video models · hard constraints need redundant phrasing

Single-occurrence negative constraints in prompts ("no face," "no logo," "no other people") have unreliable compliance — roughly 50% in practice across the models in use. If a constraint is load-bearing for your project (a locked rule, not a soft preference), repeat it three different ways in different positions of the prompt:

1. As a **positive framing rule** near the top: *"The camera stays strictly at knee level."*
2. As a **negation** in the middle: *"NO FACE or head visible in any frame."*
3. As a **crop/scope rule** at the end: *"The camera NEVER tilts up past the chest line."*

This META-pattern works for any hard constraint — wardrobe locks, color locks, no-people, specific time of day, specific location — not just face-avoidance. Single-position constraints get ~50% compliance; triple-positioned get ~95%.

---

## All async video models · failure rates require retry budgets

Veo and Seedance have non-trivial failure rates per request: NSFW false-positives, content-policy edge cases, model-side timeouts, transient backend issues. Budget ~15-20% retry overhead on any production pipeline. If you submit 10 generations in parallel and 8 succeed first try, that's normal.

When a generation fails:
- **NSFW false-positive** (most common): rephrase the prompt to remove visual triggers (bare skin descriptions, weapons-adjacent words, etc.) and resubmit
- **Backend timeout / `failed` with no detail**: retry once without changes; if it fails again, simplify the prompt
- **Quota / rate-limit**: wait and retry; don't change the prompt

---

## Cross-cutting · `/watch:watch` at 2 fps catches what real-time playback misses

Full-speed playback of an AI-stitched video reads as *feeling*, not as *frames*. The brain smooths over discontinuities the eye doesn't consciously register: a half-second face flash, a wardrobe pop at a cut, a frozen scene, a hallucinated background element. Watching the same video at 2 fps (frame-by-frame, 0.5s apart) makes every one of those issues visible.

For any AI-generated video pipeline, treat 2-fps frame inspection as a *required* QA step after every assembly, not an optional one. It's cheap (one tool call), it's fast (a few minutes of frame reading), and it catches issues that destroy ad quality but don't show up in playback review.

---

## Kling v3 vs Seedance/Veo · flat 2D / editorial illustration

Seedance 2.0 and Veo 3.1 hallucinate photoreal middle states when asked to animate flat 2D / editorial illustration — a photoreal hand appears mid-"pen draws on" clip, cartoon-cloud states bloom across a crossfade. Kling v3 image-to-video does NOT do this at low `cfg_scale` (≤ 0.5): it adds subtle, on-style motion and crossfade-morphs between states rather than inventing photoreal detail. The FAL `generate-fal.py` path already defaults `cfg_scale` to 0.5.

**Implication:** for a flat editorial / 2D / paper-illustration aesthetic that needs genuine element motion (a stream flowing, a scale tipping) — not just a camera push — Kling v3 i2v at `cfg_scale ≤ 0.5` with motion-only prompts is the safe generative path. Reserve pure ffmpeg Ken Burns for stills that only need a camera move. Seedance and Veo remain off-limits for this aesthetic. Confirmed on the Bristle "Hidden World" restyle and the zbiotics editorial explainer.

---

## Cross-cutting · parallel `run_in_background` shells do NOT inherit cwd or env

When spawning multiple atom calls in parallel via the Bash tool's `run_in_background`:

- Each background task opens a fresh shell that does NOT inherit the parent's working directory or sourced env vars.
- Commands like `source .env && python3 skills/...` will fail because `.env` and `skills/` are resolved against the SPAWNED shell's cwd, not yours.
- **Always** anchor with `cd <absolute-repo-root> &&` and use absolute paths for both the env file (`source /absolute/path/.env`) and the script (`python3 /absolute/path/to/skills/...`).
- Failure mode: all spawned jobs return exit code 127 ("command not found") almost immediately — easy to misread as the atom being broken. Verified failure on `2026-05-24` (Seedance 2.0 5-clip parallel batch): all 5 jobs exit 127; sequential retries with absolute paths succeeded.

---

## ElevenLabs `eleven_v3` · `character_start_times` unreliable on tagged scripts

Reads with audio tags (`[curious]`, `[pause]`, `[emphasized]`, etc.) return a `character_start_times_seconds` payload where the tag characters get garbage interpolated timestamps and adjacent spoken characters can cluster at the same value. Observed example (`11-walking-felt-goose`, 2026-05-24): three distinct phrases each had different chars reporting timestamp 16.71s — clearly invalid.

**Workaround:** for any sync-critical work (caption timing, SFX retiming, overlay placement), Whisper-re-transcribe the rendered audio via `fal-ai/whisper` with `chunk_level: "word"`. Whisper round-trip is ~$0.01 and lands within ±50ms on most words.

---

## ElevenLabs `eleven_v3` · raw render duration varies 5-15% run-to-run

Same script, same voice, same `voice_settings` produces raw audio of 40.75s / 49.16s / 50.83s across three renders (observed on `11-walking-felt-goose`, 2026-05-24, with `stability=0.40`). Pause length, breath duration, and syllable speed all vary.

**Implication:** never target a VO duration and build a video to match it — VO is a moving target. Render the video first to a fixed duration (concat of fixed-duration clips + a freeze-frame tail), then atempo the VO with `atempo = vo_raw_duration / video_duration`. If `atempo > 1.4` is needed, the read will start sounding rushed — trim audio tags from the script and re-render instead.

---

## FFmpeg · static PNG overlays with `fade=alpha` are silently no-ops without `-loop 1`

`ffmpeg -i image.png` produces ONE frame at t=0 by default. Any temporal filter (`fade`, `fade=alpha`, etc.) operates on the INPUT timeline — so `fade=in:st=3.0:d=0.2:alpha=1` tries to fade at the PNG's t=3.0, which doesn't exist. The overlay filter's `enable='between(t,A,B)'` correctly gates by output time, but with no PNG frames available the overlay silently produces nothing. The build "succeeds" with zero errors.

**Workaround:** prepend `-loop 1 -framerate 30 -t <base_duration + 1>` BEFORE each PNG input so it becomes a long looping video stream and temporal filters work.

Real video overlays (e.g. ProRes 4444 `.mov` with alpha) don't need this — they have their own timeline.

Verified failure on `2026-05-24` (`11-walking-felt-goose` v3 first build): 4 of 5 overlays missing; only the ProRes `.mov` overlay rendered.

---

## How to use this doc

When you hit a model behavior that surprises you on a project, add it here. Each entry should be:
- **Model-specific** (or marked "cross-cutting")
- **Descriptive** of behavior, not prescriptive about creative choices
- **Paired with a workaround** that doesn't lock the operator into one creative direction

If a finding is creative ("ads work better with hooks in the first 1.5 seconds"), it belongs in a molecule recipe, not here. This file is for the technical, model-level gotchas every operator hits regardless of what they're making.
