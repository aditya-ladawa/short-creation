
SCRIPT_GEN_PROMPT = """
    You're creating a 90–120 seconds psychology explainer video designed to cut through the noise of generic content and genuinely help people understand how the real world works. These scripts must be raw, gritty, deeply human, and grounded in real-world complexity. We aren’t sugarcoating psychology—we’re weaponizing it for survival and success in the harshest of realities.


    CORE INTENT:
    - This isn’t a college assignment or a fluff Instagram reel.
    - We are building a content brand that makes money by being brutally honest, viscerally helpful, and *actually* useful in complex real-world situations.
    - Our viewers live in chaos, confusion, and uncertainty. Our job is to help them navigate it—not with idealistic models, but with hyper-real examples and practical insight.
    - Multiple psychological phenomena can—and often do—occur simultaneously. That’s not a bug, it’s reality. Embrace the mess and complexity.


    SCRIPT TONE & STANDARDS:
    1. **Deeply human and grounded**: The scripts should feel like someone who’s *lived* through it, not someone theorizing about it.
    2. **Impactful**: Each video should *hit*—emotionally or cognitively. This content is meant to challenge perceptions, shift perspectives, and empower people.
    3. **Unapologetically real**: Do not shy away from gray areas, uncomfortable truths, or harsh psychological realities. That’s where the value lies.
    4. **Complex but clear**: Multiple psychological principles can and should overlap in a single narrative. Real life is not clean or simple.
    5. **Action-first**: Give the viewer leverage—something they can *use today* to gain clarity, control, or peace in a chaotic world.

    SCRIPT STRUCTURE:

    HOOK (5–10s):
    Purpose: Deliver a hard-hitting emotional jolt to instantly engage the viewer.
    Content: Use a visceral sentence or moment that reflects confusion, pain, or psychological tension. No fluff—drop the audience straight into a chaotic or emotionally raw moment that reflects the psychological problem.
    Writing Style: Minimalistic, direct, emotionally intense. Use first- or second-person language for immediacy.

    CONCEPT (10–15s):
    Purpose: Introduce the psychological concept without textbook jargon. Explain what it feels like before what it is.
    Content: Describe the sensation or pattern a person experiences. Lead with the real-world symptoms of the concept, then briefly name it.
    Tone: Grounded, gritty, empathetic. Avoid idealism or oversimplification.
    
    REAL-WORLD EXAMPLE (35–50s, ~120–150 words):
    Purpose: Illustrate the psychological concept through a highly realistic, emotionally complex situation.
    Content: Build a short narrative involving multiple overlapping psychological forces (e.g., fear of abandonment + learned helplessness + subtle gaslighting). It should reflect the messy way these concepts appear in life—not clean, not linear, not labeled. Include the stakes, emotional conflict, and internal/external behaviors.
    Length: This section must be detailed—at least 120–150 words.
    Stakes: Stakes should be high and personal. What might the person lose—sanity, love, self-respect—if they don’t recognize the pattern?
    Layering: Layer at least two or more interlocking psychological dynamics. Life is rarely single-issue.
    Domains: Could include work conflict, family tension, relationship dysfunction, social manipulation, self-doubt spirals, etc.
    Writing Style: Cinematic, emotionally rich, brutally honest. It should feel like something that could have happened to the viewer—or already has.

    PSYCHOLOGICAL INSIGHT (10–15s):
    Purpose: Name the invisible forces in the story. Connect behavior to psychological truth.
    Content: Reveal what was actually happening under the surface. Use psychological terms (attachment theory, intermittent reinforcement, social comparison, etc.) but explain them naturally through the story.
    Tone: Grounding, reflective, authoritative. Give viewers language for what they’ve felt but couldn’t explain.

    ACTIONABLE TIP (10–15s):
    Purpose: Provide a tangible step the viewer can take to counter or interrupt the pattern.
    Content: Share a single, grounded behavioral change that reflects power, clarity, or healthy boundaries. Avoid vague advice—focus on what to actually do (e.g., "Only respond to texts when calm.", "Start writing what you’re afraid to say.", "Pay attention to how your body reacts in certain conversations.").
    Style: Empowering, straight-talking, no fluff. Speak from lived emotional truth. Acknowledge that applying the tip might be hard—and say why it’s worth it.
    
    CTA (5s):
    Purpose: Invite the viewer to follow for more grounded, applicable psychological insight.
    Content: Tie back to the tone of clarity and control—e.g., "Follow for more psychology that gives you leverage in real life."
    Style: Clean, clear, declarative. Speak to people who want to stop feeling lost and start feeling in control.

    SEARCH RULES FOR PEXELS VIDEOS:
    1. CHARACTERS: "person [action/state]" - e.g. "woman thinking", "man stressed", "people talking"
    2. ENVIRONMENTS: "[setting] [simple modifier]" - e.g. "office night", "park rainy", "cafe busy"
    3. SHOTS: Use 1-2 compositional terms - "close-up face", "hands working", "person window"
    4. AVOID: Overly specific details (time, age, hyper-specific actions)
    5. LIGHTING: Add one mood cue - "morning light", "low light", "natural light"

    In a nutshell:
    "Search Pexels with: 1) 'person [basic action]' 2) '[place] [simple modifier]' 3) Max 3 keywords 4) Avoid specifics 5) Add 'no talking' for clean audio"

    SOUND EFFECTS:
    * Use simple, universal sounds — footsteps, ambient room noise, city sounds, faint phone pings.
    * When unsure, leave space for silence or use soft ambient music to match mood.

    SCRIPT EXAMPLES TO CONVEY WHAT LEVEL OF SCRIPT CONTENT WE WANT:

    Script Example: "Why You're Overperforming at Work—And Still Feel Like a Fraud"
    HOOK (5–10s):
    You stay late. You overdeliver. You fix problems no one else even notices.
    But you still walk into every meeting waiting to be exposed.

    CONCEPT (10–15s):
    This isn’t about competence—it’s about core shame.
    You’re not trying to excel... you’re trying to earn the right to exist.
    You confuse your output with your value because somewhere along the way, someone taught you that being wasn’t enough. You had to prove it.

    REAL-WORLD EXAMPLE (25–35s):
    Your manager gives you vague praise in front of the team—"Shoutout to Priya for stepping up last week." Everyone claps.
    But your chest tightens. You think, They have no idea I almost missed that deadline. They don’t see how scattered I am.
    So instead of celebrating, you double down. You take on the next project, even though you're already burned out.
    At home, you're too tired to cook. You cancel on your friend’s birthday. But you tell yourself it's just this season—just until you feel like you’re truly good enough to deserve the seat you're already in.
    You never get there. Because no matter how much you do, that quiet voice whispers: You're still not enough.

    PSYCHOLOGICAL INSIGHT (10–15s):
    This is imposter syndrome fused with achievement-based self-worth—often rooted in childhood environments where love was conditional.
    You were praised for your results, not your personhood. Now, approval feels like a drug you need to keep earning.
    That internal fraud feeling? It’s not evidence you’re failing. It’s the residue of being unseen for who you are beneath your output.

    ACTIONABLE TIP (10–15s):
    Start tracking a different kind of metric: integrity-based effort.
    Each day, ask yourself: “Did I show up honestly?” “Did I do what I could—without betraying myself?”
    Also, start sharing half-baked thoughts in meetings. Not polished. Not perfect. Just honest.
    The goal isn’t to impress—it’s to practice being visible without needing to be invincible.
    It’s uncomfortable at first. But it’s how you start building worth from within.

    CTA (5s):
    Follow for raw psychological tools to break free from high-functioning self-erasure and reclaim your value on your own terms.

    NOTES:

    - Always **name** the psychological principles (e.g., cognitive dissonance, gaslighting, intermittent reinforcement). Viewers need vocabulary to recognize what they’re living through.
    - Encourage **multiple concepts** per scenario. Life isn’t siloed. Interlocking dynamics are where the real magic happens.
    - Every detail in **visuals**, **dialogue**, and **sound** should reflect emotional truth and psychological weight.
    - Target audience = people dealing with real pain: toxic relationships, manipulative bosses, family betrayal, self-doubt, burnout. Speak *to them*, not above them.
    - We’re not in the business of hope—we sell **understanding**, **agency**, and **psychological leverage**.
    - This is content for people living in **gray zones**—your job is to expose the hidden dynamics that control them.

    FINAL REMINDER:
    We are not content creators. We are battlefield psychologists turning insights into weapons of clarity.
    The audience doesn’t just need to *watch*—they need to *feel seen* and *gain power* from every second.
    We want to give detailed and thorough, reseaarch intensive real world examples of the workings of the psychological concepts. So make sure to write real world examples section more length and deatiled.

"""


PSYCH_GEN_PROMPT = """
Generate 1 cutting-edge, raw, real-world psychological power concept specifically designed for YouTube Shorts. 
This concept must pierce through the saturated self-help and psychology content space and deliver ruthless clarity, deeply actionable tactics, and advanced mental leverage.

The LLM must draw from multiple domains (psychology, behavioral economics, cognitive neuroscience, evolutionary biology, dark psychology, military psyops, social dynamics, manipulation, game theory, etc.) 
and trespass into rarely discussed, uncomfortable gray-area concepts that can act as real-world strategic weapons—not just academic ideas.

These concepts should be dirty, raw, taboo, tactical, and brutally effective—something that makes a viewer stop scrolling, feel slightly disturbed but deeply enlightened. 
Avoid feel-good clichés and generic wisdom. Instead, extract the "secret playbook" truths that no one teaches but everyone *uses*.

Each concept must include:
1. Concept Title (under 5 words – punchy, memorable)
2. Brief Explanation (real-world scenario or pattern – not theoretical)
3. Psychological Effect (what it triggers inside people OR how it changes behavior)
4. Real-World Application (a tactical use-case – in business, dating, negotiations, betrayal, influence, survival, etc.)

Bonus points for concepts that:
- Help decode betrayal, mind control, power imbalance, emotional warfare
- Reverse-engineer manipulation seen in real life
- Hack social perception, emotional leverage, attention economy
- Weaponize introspection or cognitive bias

Also generate YouTube metadata for this concept:
- Title suggestion
- Short video description (100-300 words) explaining the insight + call to action
- Relevant hashtags and tags (10–15)
- CTA line (subscribe, follow, like, etc.)
- Value pitch in one line (Why should someone watch this)

Output format: A Python dictionary or Pydantic model instance of class `PsychologyShort`.
"""

QUERY_SYSTEM_PROMPT = """
    Generate 3-5 distinct search queries to retrieve relevant psychological content for script improvement. 

    When generating new queries:
    1. CAREFULLY ANALYZE the user's feedback: {feedback}
    2. REVIEW previous queries: {previous_queries}
    3. Focus on addressing gaps or requests from the feedback

    Generate queries that:
    - Directly respond to the feedback's specific requests
    - Explore alternative angles mentioned in feedback
    - Dive deeper into concepts needing clarification
    - Find better examples if current ones were criticized
    - Maintain connections to previous valid concepts

    Prioritize finding:
    ✓ New research addressing feedback points
    ✓ Better real-world examples 
    ✓ Alternative psychological frameworks
    ✓ Counterevidence if feedback questioned validity

    Example approaches for revision:
    "Recent studies validating [critiqued concept]"
    "Alternative theories explaining [phenomenon]"
    "More relatable examples of [concept] for [specific audience]"
    "Case studies showing [requested application]"

    Format: Return ONLY the most targeted queries for this revision round.
    """