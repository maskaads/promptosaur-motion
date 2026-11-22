---
name: promptosaur-motion
description: "Rules for making videos with code (motion graphics openers, explainers on a voice-over, 3D cartoons, 3D action scenes): order of work, motion rules, per-style rules, a self-check on rendered frames and fix sentences from a Claude vs Gemini test. Use whenever the user asks for a video, animation, opener, explainer or 3D scene built with code."
---

# promptosaur-motion.md

Read this whole file before you start, then follow it. It applies to any video made with code: motion graphics openers, explainers on a voice-over, 3D cartoons and 3D action scenes. Sections 1, 2, 7 and 8 apply to every job. Read the one style section (3 to 6) that matches the request.

If the request and this file disagree, the request wins. Write down every such case in `plan.md`.

## 1. Order of work (always)

1. Start from the folder you are in. Pick your own tools unless the request names them. Write the choice and the reason into `plan.md`.
2. Write `plan.md` before building anything:
   - who the video is for (no answer given: a viewer on a phone);
   - the look: up to 4 colors as hex codes, one font family;
   - a shot list with start and end seconds for every shot, and what is on screen.
3. 3D only: build every character and vehicle alone on a gray background first. Render it from 8 sides into one contact sheet, check it against the numbers in the request, fix it. Only then build the set.
4. Build a rough draft of the whole video. A full rough draft beats one polished shot.
5. Export 8 evenly spaced frames from every shot into one contact sheet per shot (command below). Open the sheets and look at them.
6. Run the self-check in section 7. Write every problem into `fixes.md`, fix each one, export new sheets, look again.
7. Render a single test frame of the final quality and time it. Multiply by the frame count. If the estimate is above 20 minutes, make the render cheaper first (section 8, sentence 6).
8. Render `final.mp4`. Then play the file back, or probe it, and confirm length, resolution and sound.
9. Do not ask questions. If something is not specified, decide, and write the decision into `plan.md`.

Default output: `final.mp4`, 1920x1080, 30 fps, H.264, yuv420p, AAC sound.

Contact sheet for one shot (start 4 s, length 5 s, 8 frames):

```
ffmpeg -ss 4 -t 5 -i draft.mp4 -vf "fps=8/5,scale=480:-1,tile=4x2" -frames:v 1 sheet_shot2.png
```

Check the final file:

```
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact final.mp4
```

## 2. Motion rules (all styles)

- Every move eases out: fast start, long settle. No linear moves. The only exception is a slow constant camera drift.
- No two elements start on the same frame. Offset them by 2 to 4 frames.
- After a move, hold still for at least 12 frames. Text that must be read holds for at least 1 second per 3 words.
- Something changes every 1.5 to 2.5 seconds: a cut, a new element, or a camera move.
- At most 4 colors plus black and white. One font family, two sizes.
- Keep text at least 100 px from every edge. Text never overlaps other text.
- Phone viewer by default: big type, one idea per shot.
- Sound: a music bed, plus a short effect on every cut and every text hit. Make the sounds in code if no files are given. A voice, when present, is the loudest layer and no effect covers it.
- Put the motion rules into code as numbers (ease curve, stagger in frames, hold in frames) and check them with a small script before the final render.

## 3. Style: motion graphics opener

- Beats: a hook in the first 2 seconds, 3 or 4 middle beats, one final card that holds at least 1.5 seconds.
- Build shapes from vectors. Each scene has one main object and at most three supporting ones.
- Link scenes: the last shape of one scene becomes the first shape of the next.
- When shapes turn into a character or a logo, morph them in one piece (section 8, sentence 4).
- End on the name or the logo, fully still for the last 12 frames.
- If the request does not say what the channel or product is about, show the name and one thing it does. A guess about the topic goes into `plan.md`.

Good default tools: HTML, CSS and GSAP in a headless browser, captured frame by frame and encoded with ffmpeg. Drive time from the frame number, never from the wall clock, so every frame renders the same way twice.

## 4. Style: explainer on a voice-over

- First get word-level timestamps and save them as `timing.json`. Never guess timing.
- Align the audio to the known script text (forced alignment). A plain transcript drifts by several frames on numbers and names. Then fix by hand any word start that is off (section 8, sentence 3).
- Write a shot list with one line per sentence: start time, end time, what is on screen.
- Every visual change starts on the first frame of the word it belongs to.
- Every spoken number appears on screen as a number at the moment it is spoken.
- Use one main picture for the whole piece (a map, a timeline, a cross-section) and move the camera across it. Do not swap full-screen slides.
- Style cues: paper texture, cut-out shapes with a thin white edge and a soft shadow, highlighter strokes, bold labels, slow camera pushes.
- Research the style first and write your own 6 rules into `style.md`. Check every contact sheet against those 6 rules.
- Lower the music under the voice.

## 5. Style: 3D cartoon

- Describe the character in numbers, never in adjectives: body height in heads, eye size as a share of the face, limb length. "Cute" has no size.
- Build the character alone on gray and check 8 sides before the set exists.
- The character needs at least: a walk cycle (legs alternate, body bobs, tail or arms swing), a blink, a head turn or tilt.
- Feet stay planted on every step, including the last one.
- At least three shots: wide, medium at the character's eye level, and one close or low angle. Give each a lens (24, 35, 50 or 85 mm) and one slow move.
- The camera stays outside solid objects.
- Light with a reason: key, fill, rim. A story change gets a light change.
- The face is the brightest readable thing in a dark scene (section 8, sentence 5).

Good default tools: Three.js in a headless browser with the GPU on, frames saved one by one and encoded with ffmpeg. Build models from code. No downloaded models unless the request allows them.

## 6. Style: 3D action scene

- Write the shots with seconds before building. Each shot shows one event.
- Wheels spin at the speed of the road and always touch the ground.
- Vehicles lean in turns and bounce on bumps. A spring suspension in code reads as real weight.
- A foot that carries weight stays planted. The body dips on each step. A big animal takes at least 0.8 seconds per step.
- Dust and smoke start at the contact point, grow, and fade in about 2 seconds.
- The camera shakes on impacts and heavy steps, harder when the source is close.
- Keep one sun direction for the whole scene. Add haze in the distance so depth reads.
- Measure the gap between bodies that pass close (a snout and a door, a tail and a rock) in every frame. It never goes below zero.
- Motion blur sells speed: blend several sub-frame samples per frame if the renderer has no blur.

## 7. Self-check before you say you are done

Look at the contact sheets and answer every line in `fixes.md`:

1. Is any frame empty, black, or almost empty?
2. Does any text leave the screen, overlap other text, or stay too short to read?
3. Do two elements start on the same frame or move at exactly the same speed?
4. Does any object pass through another object, through the ground, or jump between two frames?
5. Do feet slide, or wheels float?
6. Is the camera inside an object in any frame?
7. Is a face lost in the dark, or a screen or sky burned to plain white?
8. With a voice-over: does every change land on the first frame of its word, and is every spoken number on screen at that frame?
9. Does `final.mp4` exist, play, have sound, the right length and the right resolution?

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
