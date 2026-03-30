"""Automated test suite for PawPal+ core scheduling behaviors."""
import pytest
from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def today():
    return date.today()


@pytest.fixture
def sample_owner():
    owner = Owner("Test Owner")
    owner.add_pet(Pet("Rex", "dog"))
    owner.add_pet(Pet("Whiskers", "cat"))
    return owner


# ── Task completion ───────────────────────────────────────────────────────────

def test_mark_complete_changes_status(today):
    """mark_complete() should set completed to True."""
    task = Task("Walk", "08:00", 20, "high", "once", due_date=today)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_count():
    """add_task() should grow the pet's task list."""
    pet = Pet("Buddy", "dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk", "08:00", 20, "medium", "once"))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Feed", "12:00", 10, "high", "daily"))
    assert len(pet.tasks) == 2


# ── Sorting ───────────────────────────────────────────────────────────────────

def test_sort_by_time_returns_chronological_order(sample_owner, today):
    """sort_by_time() should return tasks in ascending HH:MM order."""
    dog = sample_owner.pets[0]
    dog.add_task(Task("Evening walk", "18:00", 30, "medium", "once", due_date=today))
    dog.add_task(Task("Morning walk", "07:00", 20, "high",   "once", due_date=today))
    dog.add_task(Task("Noon treat",   "12:00", 5,  "low",    "once", due_date=today))

    scheduler = Scheduler(sample_owner)
    times = [t[1].time for t in scheduler.sort_by_time()]
    assert times == sorted(times)


def test_sort_handles_tasks_from_multiple_pets(sample_owner, today):
    """sort_by_time() should interleave tasks from different pets correctly."""
    dog = sample_owner.pets[0]
    cat = sample_owner.pets[1]
    dog.add_task(Task("Walk",    "09:00", 20, "high",   "once", due_date=today))
    cat.add_task(Task("Feeding", "07:30", 10, "medium", "once", due_date=today))

    scheduler = Scheduler(sample_owner)
    sorted_tasks = scheduler.sort_by_time()
    assert sorted_tasks[0][1].title == "Feeding"
    assert sorted_tasks[1][1].title == "Walk"


# ── Recurrence ────────────────────────────────────────────────────────────────

def test_daily_task_creates_next_day_occurrence(today):
    """Completing a daily task should produce a new task due tomorrow."""
    task = Task("Walk", "08:00", 20, "high", "daily", due_date=today)
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.completed is False


def test_weekly_task_creates_next_week_occurrence(today):
    """Completing a weekly task should produce a new task due in 7 days."""
    task = Task("Grooming", "10:00", 30, "medium", "weekly", due_date=today)
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_once_task_returns_no_next_occurrence(today):
    """Completing a one-time task should not create a follow-up task."""
    task = Task("Vet appointment", "14:00", 60, "high", "once", due_date=today)
    assert task.mark_complete() is None


def test_scheduler_mark_complete_adds_recurrence(today):
    """scheduler.mark_task_complete() should append the next occurrence to the pet."""
    owner = Owner("Jordan")
    dog = Pet("Mochi", "dog")
    owner.add_pet(dog)
    dog.add_task(Task("Walk", "08:00", 20, "high", "daily", due_date=today))

    scheduler = Scheduler(owner)
    scheduler.mark_task_complete("Mochi", "Walk")

    assert dog.tasks[0].completed is True
    assert len(dog.tasks) == 2
    assert dog.tasks[1].due_date == today + timedelta(days=1)


# ── Conflict detection ────────────────────────────────────────────────────────

def test_no_conflicts_when_times_differ(sample_owner, today):
    """Different times on the same day should produce no conflicts."""
    sample_owner.pets[0].add_task(Task("Walk",    "08:00", 20, "high",   "once", due_date=today))
    sample_owner.pets[1].add_task(Task("Feeding", "09:00", 10, "medium", "once", due_date=today))

    assert Scheduler(sample_owner).detect_conflicts() == []


def test_detects_same_time_conflict(sample_owner, today):
    """Two tasks at the same time on the same date should trigger a conflict warning."""
    sample_owner.pets[0].add_task(Task("Walk",    "08:00", 20, "high", "once", due_date=today))
    sample_owner.pets[1].add_task(Task("Feeding", "08:00", 10, "high", "once", due_date=today))

    conflicts = Scheduler(sample_owner).detect_conflicts()
    assert len(conflicts) == 1
    assert "08:00" in conflicts[0]


def test_same_time_different_dates_no_conflict(today):
    """Same HH:MM on different dates should not be flagged as a conflict."""
    owner = Owner("Test")
    dog = Pet("Dog", "dog")
    owner.add_pet(dog)
    dog.add_task(Task("Walk", "08:00", 20, "high", "once", due_date=today))
    dog.add_task(Task("Walk", "08:00", 20, "high", "once", due_date=today + timedelta(days=1)))

    assert Scheduler(owner).detect_conflicts() == []


# ── Filtering ─────────────────────────────────────────────────────────────────

def test_filter_returns_only_pending_tasks(sample_owner, today):
    """filter_by_status(completed=False) should exclude completed tasks."""
    dog = sample_owner.pets[0]
    task1 = Task("Walk", "08:00", 20, "high", "once", due_date=today)
    task2 = Task("Feed", "12:00", 10, "medium", "once", due_date=today)
    dog.add_task(task1)
    dog.add_task(task2)
    task1.mark_complete()

    pending = Scheduler(sample_owner).filter_by_status(completed=False)
    assert all(not t[1].completed for t in pending)
    assert len(pending) == 1


def test_filter_by_pet_name(sample_owner, today):
    """filter_by_status with pet_name should return only that pet's tasks."""
    sample_owner.pets[0].add_task(Task("Walk", "08:00", 20, "high",   "once", due_date=today))
    sample_owner.pets[1].add_task(Task("Feed", "09:00", 10, "medium", "once", due_date=today))

    rex_tasks = Scheduler(sample_owner).filter_by_status(completed=False, pet_name="Rex")
    assert len(rex_tasks) == 1
    assert rex_tasks[0][0] == "Rex"
