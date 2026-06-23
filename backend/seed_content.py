"""
Velora — Content Library Seeder
Run once after DB creation: python -m backend.seed_content
"""

from backend.db.database import SessionLocal, engine, Base
from backend.models.user_model import ContentItem

Base.metadata.create_all(bind=engine)


def seed_database():
    db = SessionLocal()

    if db.query(ContentItem).count() > 0:
        print("Content library already seeded. Skipping.")
        db.close()
        return

    print("🌱 Seeding Velora Content Library...")

    content = [
        # ---- Focus ----
        ContentItem(category="Focus", content_type="Tip",
                    text="Block your best energy window for deep work. Everything else can wait."),
        ContentItem(category="Focus", content_type="Micro-Habit",
                    text="Before starting a session, write one sentence: 'Today I will finish ___.'"),
        ContentItem(category="Focus", content_type="Quote",
                    text="The successful warrior is the average person, with laser-like focus.",
                    author="Bruce Lee"),

        # ---- Consistency ----
        ContentItem(category="Consistency", content_type="Tip",
                    text="You do not rise to the level of your goals. You fall to the level of your systems."),
        ContentItem(category="Consistency", content_type="Micro-Habit",
                    text="Do at least 10 minutes of your core habit even on your worst days. The threshold matters more than the duration."),
        ContentItem(category="Consistency", content_type="Quote",
                    text="We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
                    author="Aristotle"),

        # ---- Procrastination ----
        ContentItem(category="Procrastination", content_type="Tip",
                    text="Use the 2-Minute Rule: if it takes less than 2 minutes, do it now. If it is big, start it for just 2 minutes."),
        ContentItem(category="Procrastination", content_type="Micro-Habit",
                    text="Write down the exact first physical action for the task you are avoiding. Action follows clarity."),
        ContentItem(category="Procrastination", content_type="Quote",
                    text="Amateurs sit and wait for inspiration. The rest of us just get up and go to work.",
                    author="Stephen King"),

        # ---- Burnout / Recovery ----
        ContentItem(category="Burnout", content_type="Tip",
                    text="Your brain consolidates learning during rest. Stepping away is part of the process, not an escape from it."),
        ContentItem(category="Burnout", content_type="Micro-Habit",
                    text="Close everything for 10 minutes. Walk outside. Look at something 20 feet away."),
        ContentItem(category="Recovery", content_type="Tip",
                    text="Resilience is not about never missing a day. It is about how quickly you return after you do."),
        ContentItem(category="Recovery", content_type="Micro-Habit",
                    text="After a miss, do the smallest version of the habit within 24 hours. The streak is mental, not just numerical."),

        # ---- Growth / Momentum ----
        ContentItem(category="Growth", content_type="Tip",
                    text="Identify your best execution window this week and protect it ruthlessly next week."),
        ContentItem(category="Momentum", content_type="Quote",
                    text="Small daily improvements are the key to staggering long-term results.",
                    author="Robin Sharma"),
        ContentItem(category="Growth", content_type="Micro-Habit",
                    text="At the end of today, write one thing you learned that you did not know this morning."),

        # ---- Mindfulness ----
        ContentItem(category="Mindfulness", content_type="Tip",
                    text="Before reacting to a distraction, pause for 4 seconds. That pause is where your focus lives."),
        ContentItem(category="Mindfulness", content_type="Micro-Habit",
                    text="Take 5 slow breaths before starting your most important work block."),

        # ---- Discipline / Habits ----
        ContentItem(category="Discipline", content_type="Tip",
                    text="Motivation is a visitor. Discipline is a resident. Build systems that do not require you to feel ready."),
        ContentItem(category="Habits", content_type="Micro-Habit",
                    text="Stack your core habit onto an existing routine — after coffee, after waking, after lunch. Context triggers behavior."),

        # ---- Small Wins ----
        ContentItem(category="Small Wins", content_type="Tip",
                    text="Winning small is not a consolation prize. It is how momentum is built."),
        ContentItem(category="Small Wins", content_type="Quote",
                    text="Progress, not perfection.",
                    author="Unknown"),

        # ---- Self Compassion ----
        ContentItem(category="Self Compassion", content_type="Tip",
                    text="Treat yourself like you would treat a friend who just had a hard week. Criticism shuts down learning. Compassion opens it."),
        ContentItem(category="Self Compassion", content_type="Quote",
                    text="You have been criticizing yourself for years and it has not worked. Try approving of yourself and see what happens.",
                    author="Louise Hay"),
    ]

    db.add_all(content)
    db.commit()
    print(f"✅ Seeded {len(content)} content items into Velora's knowledge base.")
    db.close()


if __name__ == "__main__":
    seed_database()
