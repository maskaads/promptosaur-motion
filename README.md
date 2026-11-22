<p align="center">
  <img src="assets/hero.svg" alt="promptosaur-motion.md: one file in your project folder, read by Claude Fable 5.2 and Gemini 4 Hydrogen before they start" width="100%">
</p>

# promptosaur-motion

One instruction file for AI agents that make videos with code. The model reads it before it starts. It covers motion graphics openers, explainers on a voice-over, 3D cartoons and 3D action scenes.

It comes from the Promptosaur test **Claude Fable 5.2 vs Gemini 4 Hydrogen**: [watch the video](https://youtu.be/Bw7ly7Dsntc). Both models got the same five jobs. Every sentence that fixed a broken result went into this file.

## Quick start

1. Download [`promptosaur-motion.md`](promptosaur-motion.md) and put it into your project folder.
2. Start your prompt with:

   ```
   Read promptosaur-motion.md in this folder first and follow it.
   ```

3. Every time something breaks and one sentence fixes it, add that sentence to section 8.

That works with any agent that can read files: Claude Code, Gemini in Antigravity or Gemini CLI, Codex, Cursor.

**Claude Code as a skill.** Copy the folder [`skills/promptosaur-motion`](skills/promptosaur-motion) into `.claude/skills/` of your project, or into `~/.claude/skills/` for all projects. Claude then loads it by itself whenever you ask for a video made with code.

```
git clone https://github.com/maskaads/promptosaur-motion
cp -r promptosaur-motion/skills/promptosaur-motion ~/.claude/skills/
```

## What is inside

| Section | What it does |
|---|---|
| 1. Order of work | `plan.md` with a shot list in seconds, a full rough draft, contact sheets of 8 frames per shot, a fix list, a timed test frame, then the final render |
| 2. Motion rules | ease-out on every move, 2 to 4 frames between starts, 12-frame holds, a change every 1.5 to 2.5 s, 4 colors, one font |
| 3. Motion graphics opener | beats, one main object per scene, scenes linked by shape, a still final card |
| 4. Explainer on a voice-over | word timestamps by forced alignment, one shot line per sentence, every number on screen on its word |
| 5. 3D cartoon | the character in numbers, built alone on gray and checked from 8 sides, planted feet, three shots with lenses |
| 6. 3D action scene | wheels that touch the road, planted feet under weight, dust from contact points, camera shake by distance |
| 7. Self-check | nine questions the model answers on its own frames before it says it is done |
| 8. Fix sentences | seven sentences from the test, plus the ones you add |

## The seven fixed sentences

| # | Sentence | What broke without it |
|---|---|---|
| 1 | Every visual change starts on the first frame of its word. | Round 3: a number faded in a few frames before the voice said it |
| 2 | Feet stay planted on every step, including the last one. | Round 4: the last step snapped the foot to its final spot |
| 3 | Align the words to the text, then check the frame of every number before you render. | Round 3: the first transcript had word starts off by several frames |
| 4 | When shapes turn into a character, morph them in one piece. | Round 2: one picture was swapped for another and the shapes jumped |
| 5 | Light the face so it reads in every shot, and keep a screen in a dark scene below pure white. | Round 4: the face got lost in the dark and the laptop screen burned to white |
| 6 | Render on the graphics card and pick shadows that are cheap to draw. | Rounds 3 and 4: frames drawn on the processor, a slow shadow effect, half the time spent rendering |
| 7 | If the render writes no new frame for two minutes, stop it. | Round 1: the render froze and left an empty `final.mp4` |

## The test in numbers

Costs are at API prices. The runs were on subscriptions, where the same tokens eat the plan's limit.

| Round | Job | Claude Fable 5.2 | Gemini 4 Hydrogen | Winner |
|---|---|---|---|---|
| 1 | 15 s opener, one-line prompt | about $9, 17 min | under $1.50, 7 min | Fable |
| 2 | 15 s opener with a brief | about $10.50, 23 min | about $1.25, 6 min | Fable, by a little |
| 3 | 20 s explainer on a voice-over | about $19, 51 min | about $2, 54 min | Fable |
| 4 | 20 s 3D cartoon | about $18, 35 min | about $5, 27 min | Fable |
| 5 | 20 s 3D chase | about $23, 43 min | about $2.25, 16 min | Fable |
| | **All five** | **about $79, almost 3 h** | **about $12, under 2 h** | |

Then Hydrogen got this file and the one-line cartoon prompt with no brief. The feet stayed planted and the jungle lit up on the key press. It rendered on the graphics card and finished in 14.5 minutes for about $3, against 27 minutes and $5 with the full brief in round 4.

## The prompts

All prompts from the video are in [`prompts/`](prompts):

| File | Round |
|---|---|
| [`1-opener-one-line.txt`](prompts/1-opener-one-line.txt) | 1, the lazy prompt |
| [`2-opener-with-brief.txt`](prompts/2-opener-with-brief.txt) | 2, the same opener with a full brief |
| [`3-voiceover-explainer.txt`](prompts/3-voiceover-explainer.txt) | 3, the creative-director prompt; the voice-over text is in [`3-voice.txt`](prompts/3-voice.txt) |
| [`4-3d-cartoon.txt`](prompts/4-3d-cartoon.txt) | 4, the 3D cartoon with the character in numbers |
| [`5-3d-chase.txt`](prompts/5-3d-chase.txt) | 5, the chase with physics written as rules |
| [`6-skill-test.txt`](prompts/6-skill-test.txt) | the skill test: this file plus one sentence |
| [`after-each-run-log.txt`](prompts/after-each-run-log.txt) | sent after every run to get the model's own log of tools and fixes |

The header animation at the top of this page is one SVG file written by hand, no video and no image generator: [`assets/hero.svg`](assets/hero.svg).

## License

MIT. Use it, change it, ship it in your own projects.
