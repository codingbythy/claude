# Autumn Rain – Mr. Fox (3-part short)

Vertical 1080x1920 shorts cut from the `glasshouse/` scene on branch `claude/focused-curie-orkd4f` (its loop video, rain ambience and lo-fi music), with narration and centred captions.

`tools/` holds the scripts: `story.py` (script), `tts.py` (narration, Kokoro `af_heart` voice), `build.py` (pixelated HD-2D look, pan, captions, audio mix). They expect that branch checked out at `src/`, the Kokoro model files in `tts/` and Pixelify Sans in `fonts/`.


## Part 1 – Mr. Fox

Someone is already sitting in your armchair. You know it before the lights even come on. You set your umbrella on the counter, and let out the sigh you’ve been holding all day. An autumn leaf still clings to your coat. You brush it away. The lamp flickers on. And there he is. Mr. Fox. Curled up in your spot. As usual. You chuckle, and put the kettle on. But here is the thing about Mr. Fox. You never brought him home. You never even went looking. A year ago, this house stood empty, and you had never seen him before in your life. Now, he waits for you every single night. So… where did he come from?

Part 1 is built by `tools/build-part1.py`: ElevenLabs v4 narration (voice "Jen"), word-timed captions kept inside the YouTube Shorts safe area, a lamp that starts off, flickers on with the line and dies at the end, and sound effects.

## Part 2 – The Cottage

Your cousins laughed when the will was read. They got the savings. The jewellery. The car. You got the cottage. And, though nobody knew it yet, a fox. “That tattered little shack? Good luck selling it.” You didn’t sell it. That spring, your rent went up again, and your job went remote for good. So you packed your shoebox apartment into eleven boxes, and took the key. It was never little. And it was never a shack. Just a Victorian cottage no one had been kind to in years. You couldn’t afford builders. So you learned. One room at a time. One paycheck at a time. Paint in your hair. Her old radio on the windowsill. By autumn, every room was warm. Every room but one. At the back of the house, there was a door your grandmother had always kept locked.

Part 2 is built by `tools/build-part2.py`: same voice and caption treatment as part 1, a cold, faded grade that warms as the house is restored, and a locked-door ending.

## Part 3 – The Glasshouse

Your grandmother kept one door locked her whole life. The day you finally got it open, you found nothing but glass, and rain. An old glasshouse. Cold, leaking, long forgotten. You sealed every pane. You saved up for a heater. And slowly, it became the warmest corner of the house. Every evening, you sit here with hot tea and a good book. Then, one autumn afternoon, something scratched at the glass. Two amber eyes. An auburn coat, shivering in the wind. You opened the door. He walked straight past you, and curled up in the armchair. As if he had done it a hundred times before. You cut him a little door of his own. And then, in her desk, you found an old photograph. Your grandmother, in that same armchair, fifty years younger. With a fox asleep in her lap.

Part 3 is built by `tools/build-part3.py`: same voice and captions, a cold grade that warms as the glasshouse is restored, and a sepia fade on the photograph.

## Parts 4–6

Scripts are in `next-parts.md`. Built with `tools/build_part.py <n>` (word timings from `tools/words.py <n>`): same voice, captions and subtle sound effects. Part 4 drifts to sepia over the photograph years, part 5 frosts the glass on its last line, part 6 stays on the frosty garden and cuts to the fox in the armchair on the final line.
