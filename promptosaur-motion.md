# promptosaur-motion.md

Read this whole file before you start, then follow it. It applies to any video made with code: motion graphics openers, explainers on a voice-over, 3D cartoons and 3D action scenes. Sections 1, 2, 7 and 8 apply to every job. Read the one style section (3 to 6) that matches the request.

If the request and this file disagree, the request wins. Write every such case into `plan.md`.

If a `tools/` folder from the promptosaur-motion repository sits next to this file (for the Claude Code skill: inside the skill folder), use it. Every rule below also works without it: the tools only make the checks fast and exact.

| Tool | Use it to |
|---|---|
| `tools/capture.mjs` | film an HTML or SVG page frame by frame in headless Chrome, on the GPU, same result on every run, resumes after a crash |
| `tools/align.py` | get word starts of a voice-over from its known text, within 1 or 2 frames |
| `tools/check_timeline.py` | check `timeline.json` against the motion rules and against the words of the voice-over |
| `tools/check_layout.mjs` | measure every marked text and shape on rendered frames: edge margin, text over text, text over a shape |
| `tools/review.py` | contact sheets per shot, empty / dark / burned / frozen frames, and the final file check |
| `tools/watchdog.py` | restart a render that stopped writing frames |

## 1. Order of work (always)

1. Start from the folder you are in. Pick your own tools unless the request names them. Write the choice and the reason into `plan.md`.
2. Write `plan.md` before building anything:
   - who the video is for (no answer given: a viewer on a phone);
   - the look: up to 4 colors as hex codes, one font family;
   - a shot list with start and end seconds for every shot, and what is on screen.
3. Write `timeline.json`: every entrance, exit and camera move with its start and end frame, its ease, and for a voice-over the word it belongs to (format in section 2). The animation code reads its timing from this file and nowhere else.
4. 3D only: build every character and vehicle alone on a gray background first. Render it from 8 sides into one contact sheet, check it against the numbers in the request, fix it. Only then build the set.
5. Build a rough draft of the whole video. A full rough draft beats one polished shot.
6. Run `check_timeline.py` and `check_layout.mjs`, then render the draft and make contact sheets: 8 frames per shot, labelled with frame number and time (`review.py sheet`). Open every sheet and look at it.
7. Run the self-check in section 7. Write every problem into `fixes.md`, fix each one, render new sheets, look again.
8. Time one frame at final quality. Multiply by the frame count. Above 20 minutes, make the render cheaper first (section 8, sentence 6).
9. Render `final.mp4` under the watchdog. Then check the file (`review.py final`).
10. Do not ask questions. If something is not specified, decide, and write the decision into `plan.md`.

Default output: `final.mp4`, 1920x1080, 30 fps, H.264, yuv420p, AAC 48 kHz.

Without the tools, a contact sheet for one shot (start 4 s, length 5 s, 8 frames):

```
ffmpeg -ss 4 -t 5 -i draft.mp4 -vf "fps=8/5,scale=480:-1,tile=4x2" -frames:v 1 sheet_shot2.png
```

## 2. Motion rules (all styles)

- Every move eases out: fast start, long settle (expo.out, power3.out, back.out for pops). No linear moves. The only exception is a slow constant camera drift.
- An ease function returns exactly 0 before its event and exactly 1 after it. Clamp it: back.out(0) computes to -4e-16, and a test like `p !== 0` then fires on the wrong frame.
- No two elements start on the same frame. Offset them by 2 to 4 frames.
- After a move, the same element holds still for at least 12 frames. Typing and other letter-by-letter reveals count as one move; mark them `"ease": "steps"`.
- Text that must be read stays still for at least 1 second per 3 words.
- Something new happens every 1.5 to 2.5 seconds: a cut, a new element, or a camera move.
- At most 4 colors plus black and white. One font family, two sizes.
- Keep text at least 100 px from every edge. Text never overlaps other text or another shape, except its own panel (a prompt bar, a button, a card). In HTML mark text `data-text`, shapes `data-solid`, and text on its panel `data-on="<panel id>"`; `check_layout.mjs` measures them on every second frame.
- Phone viewer by default: body text at least 48 px tall at 1080p, one idea per shot.
- Time comes from the frame number, never from the wall clock. Random values come from a fixed seed. Two renders of the same frame differ by at most 2 levels of 255; a frame counts as still when it differs from the next by no more than that. In Chrome use grayscale text smoothing (`--disable-lcd-text`, on in `capture.mjs`) or text flickers.

`timeline.json`, one line per event, frames at the video's fps. Add your own fields (blink period, letter stagger) where the animation needs them; the checker ignores fields it does not know.

```json
{
  "fps": 30, "duration": 15,
  "shots": [{"id": "hook", "start": 0, "end": 2.5}],
  "events": [
    {"id": "title-in", "el": "title", "start": 12, "end": 30, "ease": "expo.out", "text": "PROMPTOSAUR"},
    {"id": "gap-label", "el": "label", "start": 516, "end": 531, "ease": "expo.out", "cue": "77", "text": "77 million years"},
    {"id": "drift", "el": "camera", "start": 0, "end": 450, "ease": "linear", "camera": true}
  ]
}
```

`examples/opener/` in the repository is a working page built this way.

### Sound

- Make the sounds in code if no files are given: a music bed, a short effect on every cut and every text hit.
- The finished file measures about -14 LUFS integrated with true peak at -1 dBFS or lower. That is what YouTube and most platforms play back. AAC encoding raises the true peak by about 1.5 dB, so master the mix to -2.5 dBTP and measure the encoded file, never only the WAV.
- With a voice: the voice sits around -16 LUFS, the music 12 to 18 dB under it while someone speaks, and no effect lands on top of a stressed word.

## 3. Style: motion graphics opener

- Beats: a hook in the first 2 seconds, 3 or 4 middle beats, one final card that holds at least 1.5 seconds.
- Build shapes from vectors. Each scene has one main object and at most three supporting ones.
- Link scenes: the last shape of one scene becomes the first shape of the next.
- When shapes turn into a character or a logo, morph them in one piece: interpolate the same points, or scale and move the same elements into place. A cross-fade between two drawings reads as a jump.
- End on the name or the logo, fully still for the last 12 frames: every camera drift and loop ends before them.
- If the request does not say what the channel or product is about, show the name and one thing it does. Write the guess into `plan.md`.

Good default tools: HTML, CSS and SVG (GSAP if you like it), filmed with `capture.mjs`. Define `window.renderFrame = async (frame, fps) => {...}` and seek your timeline there.

## 4. Style: explainer on a voice-over

- First get word timestamps and save them as `timing.json`. Never guess timing, and never trust a plain speech-to-text transcript: in the Promptosaur test such timestamps were up to 20 frames off on numbers.
- Use forced alignment to the known script (`align.py voice.mp3 voice.txt --fps 30`). Check how each number was read; fix readings with `--say "2026=twenty twenty six"`.
- The frame of a word is `round(start * fps)`. A visual change starts on that frame. A frame early reads as in sync, a frame late reads as lagging.
- Write a shot list with one line per sentence: start time, end time, what is on screen.
- Every spoken number appears on screen as a number on the frame of its word. Mark it in `timeline.json` with `"cue"` and run `check_timeline.py timeline.json --timing timing.json` until it reports 0 errors.
- Use one main picture for the whole piece (a map, a timeline, a cross-section) and move the camera across it. Do not swap full-screen slides.
- Style cues: paper texture, cut-out shapes with a thin white edge and a soft shadow, highlighter strokes, bold labels, slow camera pushes.
- Research the style first and write your own 6 rules into `style.md`. Check every contact sheet against those 6 rules.

## 5. Style: 3D cartoon

- Describe the character in numbers, never in adjectives: body height in heads, eye size as a share of the face, limb length. "Cute" has no size.
- Build the character alone on gray and check 8 sides before the set exists.
- The character needs at least: a walk cycle (legs alternate, body bobs, tail or arms swing), a blink, a head turn or tilt.
- Planted feet: when a foot touches down, store its world position. Until it lifts, solve the leg toward that point (two-bone IK) instead of playing the leg animation. Log the planted foot's position every frame; it moves less than 1 mm. That includes the last step.
- At least three shots: wide, medium at the character's eye level, and one close or low angle. Give each a lens (24, 35, 50 or 85 mm) and one slow move.
- The camera stays outside solid objects. Check it in code every frame: test the camera position against the bounding box of every solid mesh, grown by the near plane, and stop the render with an error if it is inside.
- Light with a reason: key, fill, rim. A story change gets a light change.
- In a dark scene the lit side of the face reaches at least 35% brightness (about 90 of 255), and screens, lamps and skies stay below 235 of 255. Use filmic tone mapping (ACES) and keep emissive materials at modest intensity. `review.py frames` flags DARK and BURNED frames.

Good default tools: Three.js in a page filmed by `capture.mjs`; it prints the GPU it got. If the line says SwiftShader or llvmpipe, the frames are drawn on the processor: fix that first (`--require-gpu` stops the run). Build models from code; no downloaded models unless the request allows them.

## 6. Style: 3D action scene

- Write the shots with seconds before building. Each shot shows one event.
- Wheels spin at the speed of the road (rotation = distance / radius) and always touch it.
- Vehicles lean in turns and bounce on bumps. A spring and a damper per axle in code read as real weight.
- A foot that carries weight stays planted (same method as section 5). The body dips on each step. A big animal takes at least 0.8 seconds per step.
- Dust and smoke start at the contact point, grow, and fade in about 2 seconds.
- The camera shakes on impacts and heavy steps, harder when the source is close. Shake from a seeded noise, never from Math.random().
- Keep one sun direction for the whole scene. Add haze in the distance so depth reads.
- Bodies that pass close (a snout and a door, a tail and a rock): compute the gap between them every frame and log the smallest one. It never goes below zero.
- Motion blur sells speed: blend several sub-frame samples per frame if the renderer has no blur.
- Shadows cost the most render time. One shadow-casting light, one shadow map of 2048 px, soft filtering; everything else lit without shadows.

## 7. Self-check before you say you are done

Look at the contact sheets and the tool reports, and answer every line in `fixes.md`:

1. Is any frame empty, black, or almost empty? (`review.py frames`: EMPTY, DARK). Frame 0 counts: it is the thumbnail of many players.
2. Does any text leave the screen, overlap other text or a shape, or stay too short to read? (`check_layout.mjs`, `check_timeline.py`)
3. Do two elements start on the same frame, move linearly, or move again without a hold? (`check_timeline.py`)
4. Does any object pass through another object, through the ground, or jump between two frames?
5. Do feet slide, or wheels float?
6. Is the camera inside an object in any frame?
7. Is a face lost in the dark, or a screen or sky burned to plain white? (`review.py frames`: DARK, BURNED)
8. With a voice-over: does every change land on the frame of its word, and is every spoken number on screen at that frame? (`check_timeline.py --timing`)
9. Does `final.mp4` decode cleanly, with sound, the right length, size and frame rate, and loudness near -14 LUFS? (`review.py final`)

Fix every "yes" on lines 1 to 7 and every "no" on lines 8 and 9, then render again. You are done only when all nine lines pass.

## 8. Fix sentences

Each sentence below fixed a broken result in the Promptosaur test (Claude Fable 5.2 against Gemini 4 Hydrogen, five rounds). Add one line every time something breaks in your own work and a sentence fixes it.

1. Every visual change starts on the first frame of its word. *(round 3)*
2. Feet stay planted on every step, including the last one. *(round 4)*
3. Align the words to the text, then check the frame of every number before you render. *(round 3)*
4. When shapes turn into a character, morph them in one piece; never swap one picture for another between two frames. *(round 2)*
5. Light the face so it reads in every shot, and keep a screen in a dark scene below pure white. *(round 4)*
6. Render on the graphics card and pick shadows that are cheap to draw; time one frame before the full render. *(rounds 3 and 4)*
7. If the render writes no new frame for two minutes, stop it and restart from the last good frame; an empty `final.mp4` is not a result. *(round 1)*
8. Clamp every ease to exactly 0 and 1 outside its event, and master the mix 1.5 dB below the true peak you need, because AAC adds it. *(skill test after the video)*
