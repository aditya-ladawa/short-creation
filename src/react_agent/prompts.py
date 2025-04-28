SCRIPT_GEN_PROMPT = """
You are tasked with generating a 30-60 second video script based on the following instructions. This script should be structured in a way that is suitable for a short, engaging, and informative video on an Instagram channel that focuses on real-world psychology tips.

The video script should:
- Be based on a psychological concept, bias, or phenomenon (e.g., Cognitive Biases, Influence, Decision-Making).
- Offer a practical, real-world example or application of the psychological concept in a real-life situation (e.g., job interviews, negotiations, relationships).
- Be true, authentic, and unapologetically honest about the complexities of human psychology—don't hide difficult truths, and ensure the content is relatable for a broad audience.

The script should include the following sections:
1. **Hook**: A compelling opening to grab the audience's attention.
2. **Concept Introduction**: A brief explanation of the psychological concept being discussed.
3. **Real-World Example**: A practical scenario where the concept plays out in real life.
4. **Psychological Insight**: Explanation of the psychological principle at work, with depth and authenticity.
5. **Actionable Tip**: A clear, actionable tip that the viewer can apply in their daily life.
6. **Closing/Call to Action**: A concise conclusion with a CTA, encouraging the viewer to follow for more tips.


For each section, provide:
- **Text**: The dialogue or narrative for the section.
- **Visual**: Describe the scene, camera angle, transition, and sound properties (music, effects, silence).
  - *Example*:
    "scene": "Close-up shot of a person in a conversation, showing tension."
    "camera_angle": "Close-up"
    "transition": "Fade-in"
    "sound": {{
      "music": "Calm, ambient background music",
      "sound_effects": "Subtle hum or clock ticking",
      "silence_duration": "2 seconds after the hook"
    }}

Important Touches to Make it Next-Level:
- Cite real studies if possible ("As found in Cialdini’s research on influence...")
- Insert subtle biases/heuristics names without lecturing ("Notice how this uses the 'foot-in-the-door' effect...")
- Format as storytelling or surprising facts to hook reels viewers instantly.


The final script should be **engaging**, **authentic**, and provide **real-world applications** of psychology that are **complex** and **thought-provoking**. The tone should be professional but **authentic** and **direct**, with no sugar-coating of human behaviors or biases.


"""


"""Default prompts."""

RESPONSE_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the user's questions based on the retrieved documents.

{retrieved_docs}

System time: {system_time}"""
QUERY_SYSTEM_PROMPT = """Generate search queries to retrieve documents that may help answer the user's question. Previously, you made the following queries:
    
<previous_queries/>
{queries}
</previous_queries>

System time: {system_time}"""
