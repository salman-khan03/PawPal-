"""
PawPal+ backend logic layer.

Classes: Task (dataclass), Pet, Owner, Scheduler.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple


@dataclass
class Task:
    """Represents a single pet care activity."""

    title: str
    time: str                   # "HH:MM" 24-hour format
    duration_minutes: int
    priority: str               # "low" | "medium" | "high"
    frequency: str              # "once" | "daily" | "weekly"
    description: str = ""
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task complete and return the next occurrence if recurring."""
        self.completed = True
        if self.frequency == "daily":
            return Task(
                title=self.title,
                time=self.time,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                frequency=self.frequency,
                description=self.description,
                due_date=self.due_date + timedelta(days=1),
            )
        if self.frequency == "weekly":
            return Task(
                title=self.title,
                time=self.time,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                frequency=self.frequency,
                description=self.description,
                due_date=self.due_date + timedelta(weeks=1),
            )
        return None


class Pet:
    """Stores pet details and a list of associated care tasks."""

    def __init__(self, name: str, species: str) -> None:
        self.name = name
        self.species = species
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)

    def get_tasks(self) -> List[Task]:
        """Return all tasks for this pet."""
        return self.tasks


class Owner:
    """Manages an owner profile and their collection of pets."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's household."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List[Tuple[str, Task]]:
        """Return all tasks across all pets as (pet_name, Task) tuples."""
        result = []
        for pet in self.pets:
            for task in pet.tasks:
                result.append((pet.name, task))
        return result


class Scheduler:
    """Retrieves, organizes, and manages tasks across all pets for an owner."""

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def sort_by_time(
        self, tasks: Optional[List[Tuple[str, Task]]] = None
    ) -> List[Tuple[str, Task]]:
        """Return tasks sorted chronologically by time (HH:MM)."""
        if tasks is None:
            tasks = self.owner.get_all_tasks()
        return sorted(tasks, key=lambda x: x[1].time)

    def filter_by_status(
        self,
        completed: bool = False,
        pet_name: Optional[str] = None,
    ) -> List[Tuple[str, Task]]:
        """Filter tasks by completion status and optionally by pet name."""
        tasks = self.owner.get_all_tasks()
        result = [t for t in tasks if t[1].completed == completed]
        if pet_name:
            result = [t for t in result if t[0] == pet_name]
        return result

    def get_today_schedule(self) -> List[Tuple[str, Task]]:
        """Return today's pending tasks sorted by time."""
        today = date.today()
        tasks = self.owner.get_all_tasks()
        today_pending = [
            t for t in tasks if t[1].due_date == today and not t[1].completed
        ]
        return self.sort_by_time(today_pending)

    def detect_conflicts(self) -> List[str]:
        """Detect tasks at the exact same time on the same date. Returns warning strings."""
        seen: dict = {}
        conflicts = []
        for pet_name, task in self.owner.get_all_tasks():
            key = (task.time, task.due_date)
            if key in seen:
                prev_pet, prev_task = seen[key]
                conflicts.append(
                    f"Conflict at {task.time} on {task.due_date}: "
                    f"'{task.title}' ({pet_name}) vs '{prev_task.title}' ({prev_pet})"
                )
            else:
                seen[key] = (pet_name, task)
        return conflicts

    def mark_task_complete(self, pet_name: str, task_title: str) -> bool:
        """Mark a task complete and schedule the next occurrence if recurring."""
        for pet in self.owner.pets:
            if pet.name == pet_name:
                for task in pet.tasks:
                    if task.title == task_title and not task.completed:
                        next_task = task.mark_complete()
                        if next_task:
                            pet.add_task(next_task)
                        return True
        return False

    def generate_daily_plan(self) -> dict:
        """Generate a priority-first daily plan with scheduling explanations."""
        schedule = self.get_today_schedule()
        conflicts = self.detect_conflicts()

        # Sort high-priority tasks first; within the same priority level, sort by time
        priority_sorted = sorted(
            schedule,
            key=lambda x: (self.PRIORITY_ORDER.get(x[1].priority, 2), x[1].time),
        )

        explanation = []
        for pet_name, task in priority_sorted:
            note = (
                f"[{task.priority.upper()}] {task.title} for {pet_name} "
                f"at {task.time} ({task.duration_minutes} min)"
            )
            if task.frequency != "once":
                note += f" - repeats {task.frequency}"
            if task.description:
                note += f" | {task.description}"
            explanation.append(note)

        return {
            "schedule": priority_sorted,
            "conflicts": conflicts,
            "total_duration": sum(t[1].duration_minutes for t in schedule),
            "explanation": explanation,
        }
