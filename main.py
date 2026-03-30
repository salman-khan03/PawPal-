"""CLI demo script for PawPal+ - verifies core scheduling logic in the terminal."""
from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


def main() -> None:
    # ── Setup: owner and two pets ─────────────────────────────────────────────
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog")
    luna = Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    today = date.today()

    # ── Add tasks (intentionally out of time order to test sorting) ───────────
    mochi.add_task(Task(
        title="Evening walk", time="18:00", duration_minutes=30,
        priority="medium", frequency="daily", description="After dinner", due_date=today,
    ))
    mochi.add_task(Task(
        title="Morning walk", time="07:30", duration_minutes=20,
        priority="high", frequency="daily", description="Before work", due_date=today,
    ))
    mochi.add_task(Task(
        title="Heartworm med", time="08:00", duration_minutes=5,
        priority="high", frequency="weekly", description="With food", due_date=today,
    ))
    luna.add_task(Task(
        title="Breakfast", time="08:00", duration_minutes=10,
        priority="high", frequency="daily", description="Wet food", due_date=today,
    ))
    luna.add_task(Task(
        title="Grooming", time="10:00", duration_minutes=15,
        priority="low", frequency="weekly", due_date=today,
    ))

    scheduler = Scheduler(owner)

    # ── Today's schedule sorted by time ──────────────────────────────────────
    print("=" * 62)
    print(f"  Today's Schedule for {owner.name}  ({today})")
    print("=" * 62)
    for pet_name, task in scheduler.get_today_schedule():
        print(
            f"  {task.time}  [{task.priority.upper():6}]  "
            f"{task.title:<20} ({pet_name}, {task.duration_minutes} min)"
        )

    # ── Conflict detection ────────────────────────────────────────────────────
    print("\nConflict Check:")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for c in conflicts:
            print(f"  [!] {c}")
    else:
        print("  No conflicts found.")

    # Resolve the Mochi/Luna 08:00 conflict
    print("\n  -> Rescheduling Luna's Breakfast to 08:15 to resolve conflict...")
    for task in luna.tasks:
        if task.title == "Breakfast":
            task.time = "08:15"

    after = scheduler.detect_conflicts()
    print("  After fix:", "No conflicts." if not after else after)

    # ── Mark a recurring task complete ────────────────────────────────────────
    print("\nMarking 'Morning walk' complete for Mochi...")
    scheduler.mark_task_complete("Mochi", "Morning walk")

    pending_today = [
        t.title for t in mochi.tasks
        if not t.completed and t.due_date == today
    ]
    next_walk = [t for t in mochi.tasks if t.title == "Morning walk" and not t.completed]
    print(f"  Mochi's remaining tasks today: {pending_today}")
    if next_walk:
        print(f"  Next 'Morning walk' rescheduled for: {next_walk[0].due_date}")

    # ── Filter: pending tasks only ────────────────────────────────────────────
    print("\nPending tasks (all pets):")
    for pet_name, task in scheduler.filter_by_status(completed=False):
        print(f"  {pet_name}: {task.title} (due {task.due_date})")

    # ── Full priority-first daily plan ────────────────────────────────────────
    print("\n" + "=" * 62)
    print("  Daily Plan  (high priority first, then by time)")
    print("=" * 62)
    plan = scheduler.generate_daily_plan()
    print(f"  Total scheduled time: {plan['total_duration']} minutes\n")
    for line in plan["explanation"]:
        print(f"  {line}")

    print("\nDone!\n")


if __name__ == "__main__":
    main()
