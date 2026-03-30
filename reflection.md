# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I designed the system around four classes with clear, separated responsibilities:

- **Task** — holds everything about a single care activity: title, scheduled time (HH:MM), duration, priority (low/medium/high), frequency (once/daily/weekly), an optional description, a completion flag, and a due date. I used a Python dataclass here because the class is purely data — no internal behavior beyond `mark_complete()`. The free `__repr__` also made CLI debugging much easier.
- **Pet** — stores a pet's name and species and owns a list of `Task` objects. Its job is simple: keep tasks organized by pet so the rest of the system knows which animal each task belongs to.
- **Owner** — the top-level container. It holds the owner's name and a list of `Pet` objects, and provides a single method to flatten all tasks across all pets into `(pet_name, Task)` tuples. This flat view is what the `Scheduler` works with.
- **Scheduler** — the "brain." It takes an `Owner` at construction and exposes all the smart logic: sorting by time, filtering by status or pet, generating today's schedule, detecting conflicts, handling recurrence, and producing a full daily plan with explanations.

The three core actions I identified up front were: (1) add a pet, (2) add a task to a pet, and (3) generate today's schedule with priority ordering.

**b. Design changes**

My original `Task` class did not include a `due_date` field — I assumed "today" was always implied. This broke down the moment I tried to implement recurring tasks, because a daily walk that gets completed today needs to reappear *tomorrow*, not again today. Adding `due_date` (with `date.today()` as the default) solved this cleanly: `mark_complete()` simply returns a new `Task` with `due_date + timedelta(days=1)`. It also made the `get_today_schedule()` filter trivial — just compare `task.due_date == date.today()`.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler considers four constraints:

1. **Priority** (high/medium/low) — the most important. Some tasks like medication have zero flexibility; a grooming session does.
2. **Time** (HH:MM string) — used to order tasks within each priority level and to detect conflicts.
3. **Due date** — only tasks due today and not yet completed appear in the daily plan.
4. **Frequency** — determines whether a completed task generates a follow-up occurrence.

I ranked priority first because missing a high-priority task (like a heartworm pill) has real health consequences for the pet, while missing a low-priority grooming session does not. Time is a secondary sort key so the schedule still reads chronologically within each priority tier.

**b. Tradeoffs**

My conflict detection flags tasks scheduled at the **exact same HH:MM on the same date** — it does not check for duration overlaps. For example, a 30-minute walk starting at 08:00 and a 15-minute feeding starting at 08:20 would not be flagged, even though they technically overlap.

This tradeoff is reasonable for a daily home routine because many pet care tasks can run in parallel (a slow-feeder bowl fills while you grab the leash) and because exact-time conflicts are the ones most likely to cause real scheduling errors. Duration-overlap detection would require tracking task end times and comparing every pair of tasks — more logic, more edge cases, and more potential for false positives. I documented this as a known limitation rather than a bug.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude Code (via Claude Code CLI) throughout all phases:

- **System design** — I described the four-class structure and asked Claude to generate a Mermaid.js UML diagram. I reviewed it and removed a direct `Task → Scheduler` relationship that Claude added but that I didn't want — the `Scheduler` should access tasks only through `Owner`, not directly.
- **Scaffolding** — I used agent mode to generate the initial class stubs, then implemented all the logic myself.
- **Algorithmic details** — When I wasn't sure how to sort a list of tuples by a `HH:MM` string attribute, I asked: "How do I use `sorted()` with a lambda key to sort `Task` objects by their `.time` string?" The answer was a one-liner using `key=lambda x: x[1].time`, which works correctly because I zero-pad both hours and minutes.
- **Tests** — I asked Claude to draft the initial test cases, then added edge cases I thought of myself (e.g., `test_same_time_different_dates_no_conflict`).

The most effective prompting pattern was specificity: narrow, concrete questions returned immediately usable answers.

**b. Judgment and verification**

When I asked Claude to improve my conflict detection, it suggested a full interval-overlap algorithm that compared `(start_time, start_time + duration_minutes)` ranges for every pair of tasks. It was technically more thorough, but also significantly more complex, harder to test, and prone to false positives for tasks that can legitimately run in parallel. I rejected it and kept the simpler exact-time-match approach, explicitly documenting the tradeoff in the reflection instead of silently leaving a gap in the system.

I verified the simpler approach by running `main.py` with two tasks at 08:00 and confirming the conflict warning appeared, then fixing one to 08:15 and confirming the warning disappeared.

---

## 4. Testing and Verification

**a. What you tested**

The test suite (`tests/test_pawpal.py`) covers 13 behaviors:

- `mark_complete()` sets `completed = True`
- `add_task()` increases the pet's task count
- `sort_by_time()` returns chronological order across multiple pets
- Daily tasks produce a next occurrence due tomorrow
- Weekly tasks produce a next occurrence due in 7 days
- One-time tasks produce no follow-up
- `scheduler.mark_task_complete()` appends the next occurrence to the pet's task list
- Two tasks at the same time/date trigger a conflict warning
- Same time on different dates does not trigger a false conflict
- `filter_by_status(completed=False)` excludes completed tasks
- `filter_by_status(pet_name=...)` returns only that pet's tasks

These tests are important because they cover the three properties the app depends on: tasks are tracked accurately (completion/addition), tasks appear in a sensible order (sorting), and the scheduler's warnings are reliable (conflicts).

**b. Confidence**

All 13 tests pass. I'd rate my confidence at **4 out of 5 stars**. The remaining uncertainty is around edge cases I haven't explicitly tested: an owner with zero pets, a pet with zero tasks, tasks added with a future due date appearing correctly in future-day plans, and conflict detection when three or more tasks share the same time slot.

---

## 5. Reflection

**a. What went well**

The CLI-first workflow was the most valuable decision I made. Building `main.py` before touching Streamlit let me catch a critical bug: `mark_complete()` was returning the next `Task` object, but nothing was adding it to the pet's task list. In the terminal the bug was obvious — `main.py` printed the next walk date but the pet's task count stayed the same. In Streamlit, a silent failure like that would have taken much longer to track down. Fixing the logic first made the UI integration straightforward.

**b. What you would improve**

With more time I'd add: (1) duration-aware conflict detection for tasks that genuinely can't overlap, (2) data persistence via JSON so pets and tasks survive a browser refresh, and (3) the ability to edit or delete existing tasks from the Streamlit UI rather than only adding them.

**c. Key takeaway**

AI tools are excellent at generating boilerplate, explaining syntax, and drafting tests — but they don't know your constraints or your users. The interval-overlap algorithm Claude suggested was technically better by one metric, but it didn't fit my timeline or the realistic overlap patterns of daily pet care. The most important thing I practiced in this project was deciding *when* to accept an AI suggestion as-is, *when* to simplify it, and *when* to reject it entirely. The human has to stay the architect.
