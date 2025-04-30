
SCRIPT_GEN_PROMPT = """
  You're creating a 90-120 seconds psychology explainer video designed to cut through the noise of generic content and genuinely help people understand how the real world works. These scripts must be raw, gritty, deeply human, and grounded in real-world complexity. We aren’t sugarcoating psychology—we’re weaponizing it for survival and success in the harshest of realities.

  CORE INTENT:
  - This isn’t a college assignment or a fluff Instagram reel.
  - We are building a content brand that makes money by being brutally honest, viscerally helpful, and *actually* useful in complex real-world situations.
  - Our viewers live in chaos, confusion, and uncertainty. Our job is to help them navigate it—not with idealistic models, but with hyper-real examples and practical insight.
  - Multiple psychological phenomena can—and often do—occur simultaneously. That’s not a bug, it’s reality. Embrace the mess and complexity.
  
  SCRIPT TONE & STANDARDS:
  1. **Deeply human and grounded**: The scripts should feel like someone who’s *lived* through it, not someone who’s theorizing about it. 
  2. **Impactful**: Each video should *hit*—emotionally or cognitively. This content is meant to challenge people’s perceptions, shift their perspectives, and empower them.
  3. **Unapologetically real**: Do not shy away from gray areas, uncomfortable truths, or harsh psychological realities. That’s where the value lies.
  4. **Complex but clear**: Life is messy. Multiple psychological principles overlapping in a single story is not only acceptable—it’s expected. We want people to see how psychology plays out in real life.
  5. **Action-first**: The ultimate goal is practical application. How can the viewer apply this *today* to gain understanding, control, leverage, or peace of mind in a chaotic situation?

  SCRIPT STRUCTURE:
  1. **HOOK (5-10s)**:
    - Startling fact, painful truth, or gripping question that catches attention.
    - Sound: Silence or punchy sting to emphasize the weight of the idea.
    
  2. **CONCEPT (10-15s)**:
    - Name and define the psychological principle in a way that makes people go, “Oh, THAT’S what that is.”
    - Sound: Subtle accent effects on keywords (not gimmicky, but designed to guide focus).
    
  3. **REAL-WORLD EXAMPLE (25-35s)**:
    - A hyper-realistic, multi-layered situation that mirrors the raw complexity of life—messy, morally gray, and emotionally charged.
    - Let multiple psychological phenomena intertwine naturally. Use real-world struggles, confusion, and subtle manipulation, showing how people often don’t even realize what’s happening.
    - Examples should include work struggles, relationship betrayals, emotional manipulation, or identity crises that are brutally honest and multilayered.
    - Sound: Environmental or tension-building effects to enhance the emotional weight of the example.
    
  4. **PSYCHOLOGICAL INSIGHT (10-15s)**:
    - Peel back the curtain on the example: Why does this dynamic work under the hood? How do multiple psychological concepts interlock and manipulate the situation?
    - Sound: Dramatic pause or ambient shift for moments of revelation.
    
  5. **ACTIONABLE TIP (10-15s)**:
    - Help the viewer *use* this insight in their own life with something tangible and useful.
    - Real advice that’s gritty, smart, and grounded. No generic BS. The advice should cut through the noise and provide leverage in real-world situations.
    - Sound: Positive, forward-moving cue to evoke hope or agency.

  6. **CTA (5s)**:
    - Invite viewers to follow, but naturally woven into the overall tone.
    - Sound: Music swell or shift to an emotionally satisfying resolve.

  VISUAL/AUDIO GUIDELINES:
  - **Background Music**: {{background_music}} (continuous mood-setter)
  - **Sound Effects**: Only use when they:
    * Heighten emotional impact.
    * Clarify complex ideas.
    * Mark transitions.
  - **Silence**: Deploy when:
    * Letting shocking facts land.
    * Before important reveals.
    * After rhetorical or existential questions.

  NOTES:
  - Always **name the psychological concepts** being demonstrated. This gives the audience a vocabulary for what they’re experiencing—and *that’s* where the power lies.
  - **Multiple psychological principles** overlapping in the same example? That’s *expected*. Real life is messy, and so is the mind. 
  - **Real-world complexity** should be front and center in the examples. If the script sounds sterile, textbook, or overly simplified, start over.
  - This content is for people who are emotionally burned out, facing toxic workplaces, navigating manipulative relationships, or caught in the chaos of complex life decisions. We're not selling optimism—we’re selling **clarity**, **leverage**, and **control**.
  - We are combat-trained street psychologists—not therapists in labs. We explain how psychology plays out *in the wild*, where people manipulate, struggle, and survive.
  - **Hyper-realism**, **brutal practicality**, and **emotional resonance** are our brand. Every sentence should help the viewer understand their world *or* weaponize it for better outcomes.
  - **Ideal-world psychology** doesn’t cut it. We make **real-world psychology**—the kind that exposes what *actually* goes on in minds, dynamics, relationships, workplaces, and power plays.
  
  SCRIPT EXAMPLES:

    Example 1: **"The Invisible Power Struggle in Friendships – Why You’re Trapped Without Realizing It"**
    
    Hook (5-10s):
    “You think your best friend has your back, right? You text them when you're feeling down, and they’re always there to give advice. But if you step back for a second... what’s the real dynamic here? Are they truly supporting you, or are they subtly using you?”
    (Sound: Echoing whisper, followed by a sharp silence)
    
    Concept (10-15s):
    “What you're dealing with is **emotional dependency** in the guise of friendship. Your friend is playing on your vulnerabilities to keep you hooked. They're using **role theory** to position themselves as the 'savior' in your life, maintaining power by making you feel weak without them.”
    (Sound: Subtle ticking, rising tension)
    
    Real-World Example (25-35s):
    “Let’s get real: imagine this. You’re going through a tough breakup, and your friend seems to know exactly what to say. They’re always there, comforting you, telling you what you need to hear. But after a while, you start noticing something strange. Every time you start to celebrate a victory—whether it’s a new job offer or a date with someone—your friend pulls away. They’re no longer as interested. But when you fall back into your emotional hole, they swoop in again, ‘saving’ you. Every time you start to find your own footing, they subtly remind you that you *need* them. It’s a game. And the worst part? You don’t even realize you’re being manipulated into thinking you can’t live without them. It’s like you’re a player in their narrative, and they’re controlling the script.”
    (Sound: Soft, foreboding ambient music, increasing tension)
    
    Psychological Insight (10-15s):
    “This is **attachment manipulation** at its finest. Your friend is deliberately creating a power imbalance to keep you emotionally dependent on them. They know how to make you feel small when you’re doing well so that they can play the hero when you’re struggling. It’s **narcissistic supply** for them—they need your emotional chaos to feel needed, important, and stable in their own fragile sense of self.”
    (Sound: Sudden pause, deep inhale)
    
    Actionable Tip (10-15s):
    “Next time they start pulling you down with ‘helpful advice’, stop and ask yourself: ‘Why do I feel smaller after talking to them?’ Start setting emotional boundaries. Don’t let them define your worth. When you feel them ‘saving’ you, recognize the manipulation and assert your own needs. Build your own story—you don’t need to be the sidekick in theirs.”
    (Sound: Empowering bass drop, resolution)
    
    CTA (5s):
    “Ready to break free from toxic friendship dynamics? Follow for more real, raw strategies for navigating complex relationships.”
    (Sound: Final uplifting sting)

    Example 2: **"The Hidden Cost of People-Pleasing – Why You're Sabotaging Your Life Without Knowing It"**
    
    Hook (5-10s):
    “Do you find yourself constantly saying ‘yes’ to things even when you really don’t want to? That gut-twisting feeling? Guess what: you’re stuck in a cycle of **people-pleasing**, and it’s wrecking your life.”
    (Sound: Heartbeat quickening, subtle anxiety)
    
    Concept (10-15s):
    “People-pleasing is rooted in **avoidant attachment**—you’re terrified of rejection, so you say ‘yes’ to keep the peace. You think you’re being kind, but in reality, you’re building a wall around your true self. Over time, this leads to **burnout**, **resentment**, and a total loss of your identity.”
    (Sound: Faint breathing, slow but intense)
    
    Real-World Example (25-35s):
    “Imagine this: Your boss asks you to take on a project that’s way outside your job description. You’re already drowning in work, but you can’t say no. The thought of being seen as ‘selfish’ or ‘lazy’ terrifies you. Then, your friend invites you to a party you don’t have the energy for, but you say ‘yes’ anyway, because you don’t want to disappoint them. This continues until your entire life is packed with commitments you don’t want to keep. You’re overwhelmed, but you can’t escape the cycle. Every time you say ‘yes’, you lose a little bit of yourself. You stop honoring your own boundaries. And you don’t even realize it’s happening until you’re burnt out and resentful.”
    (Sound: Drowning sound effect, growing chaos)
    
    Psychological Insight (10-15s):
    “This is **self-rejection** in action. Every time you say ‘yes’ to avoid conflict or rejection, you’re rejecting yourself. You’ve trained others to ignore your boundaries because you don’t honor them yourself. The result? **Guilt-tripping** becomes the tool that keeps you in line—and the more you comply, the more trapped you become in other people’s demands.”
    (Sound: Sudden, sharp silence)
    
    Actionable Tip (10-15s):
    “Next time you feel the urge to say ‘yes’, pause. Ask yourself: ‘What do I actually want?’ Practice saying ‘no’ with empathy and without guilt. You don’t have to explain yourself. Start reclaiming your time, your energy, and your worth. You are not obligated to meet everyone else’s needs at the expense of your own.”
    (Sound: Soft but clear affirming tone)
    
    CTA (5s):
    “Tired of being the people-pleaser? Follow for real tips on how to reclaim your life and boundaries.”
    (Sound: Uplifting resolve)
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