"""PawPal+ Streamlit app — smart daily pet care scheduling."""
import streamlit as st
from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart daily pet care scheduling")

# ── Session state bootstrap ───────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None

# ── Sidebar: owner + pet setup ────────────────────────────────────────────────
with st.sidebar:
    st.header("Setup")

    with st.form("owner_form"):
        default_name = st.session_state.owner.name if st.session_state.owner else "Jordan"
        owner_name = st.text_input("Your name", value=default_name)
        if st.form_submit_button("Set / Update Owner"):
            if st.session_state.owner is None:
                st.session_state.owner = Owner(owner_name)
            else:
                st.session_state.owner.name = owner_name
            st.success(f"Owner set to {owner_name}!")

    if st.session_state.owner is None:
        st.info("Enter your name above to get started.")
        st.stop()

    owner = st.session_state.owner

    st.divider()
    st.subheader("Add a Pet")
    with st.form("pet_form"):
        pet_name_input = st.text_input("Pet name")
        species_input = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        if st.form_submit_button("Add Pet"):
            if not pet_name_input.strip():
                st.error("Enter a pet name.")
            elif pet_name_input in [p.name for p in owner.pets]:
                st.warning(f"{pet_name_input} is already added.")
            else:
                owner.add_pet(Pet(pet_name_input.strip(), species_input))
                st.success(f"Added {pet_name_input}!")

    if owner.pets:
        st.divider()
        st.subheader("Your Pets")
        for p in owner.pets:
            st.write(f"• **{p.name}** ({p.species}) — {len(p.tasks)} tasks")

# ── Main area ─────────────────────────────────────────────────────────────────
owner = st.session_state.owner

if not owner.pets:
    st.info("Add at least one pet in the sidebar to get started.")
    st.stop()

scheduler = Scheduler(owner)

tab1, tab2, tab3 = st.tabs(["➕ Add Tasks", "📋 Daily Plan", "📊 All Tasks"])

# ── Tab 1: Add Tasks ──────────────────────────────────────────────────────────
with tab1:
    st.header("Add a Care Task")
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_pet   = st.selectbox("For pet", [p.name for p in owner.pets])
            task_title = st.text_input("Task title", value="Morning walk")
            task_desc  = st.text_input("Description (optional)")
            task_time  = st.text_input("Time (HH:MM)", value="08:00")
        with col2:
            duration  = st.number_input(
                "Duration (minutes)", min_value=1, max_value=480, value=20
            )
            priority  = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
            task_due  = st.date_input("Due date", value=date.today())

        if st.form_submit_button("Add Task", type="primary"):
            # Validate HH:MM
            try:
                h, m = task_time.strip().split(":")
                assert len(h) == 2 and len(m) == 2
                assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
                valid_time = True
            except Exception:
                valid_time = False

            if not valid_time:
                st.error("Time must be in HH:MM format (e.g., 08:00, 14:30).")
            elif not task_title.strip():
                st.error("Task title cannot be empty.")
            else:
                new_task = Task(
                    title=task_title.strip(),
                    time=task_time.strip(),
                    duration_minutes=int(duration),
                    priority=priority,
                    frequency=frequency,
                    description=task_desc,
                    due_date=task_due,
                )
                for p in owner.pets:
                    if p.name == task_pet:
                        p.add_task(new_task)
                        st.success(
                            f"Added '{task_title}' for {task_pet} "
                            f"at {task_time} on {task_due}"
                        )
                        break

# ── Tab 2: Daily Plan ─────────────────────────────────────────────────────────
if "plan" not in st.session_state:
    st.session_state.plan = None

with tab2:
    st.header(f"Today's Plan — {date.today().strftime('%A, %B %d, %Y')}")

    if st.button("Generate Schedule", type="primary"):
        st.session_state.plan = scheduler.generate_daily_plan()

    plan = st.session_state.plan

    if plan is not None:
        # Conflict warnings
        if plan["conflicts"]:
            for conflict in plan["conflicts"]:
                st.warning(f"⚠️  {conflict}")
        else:
            st.success("No scheduling conflicts detected.")

        if not plan["schedule"]:
            st.info("No tasks scheduled for today. Add tasks with today's date.")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Tasks today", len(plan["schedule"]))
            c2.metric("Total time", f"{plan['total_duration']} min")

            st.divider()
            st.subheader("Priority-first schedule")

            ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}

            for i, (pet_name, task) in enumerate(plan["schedule"]):
                icon      = ICONS.get(task.priority, "⚪")
                recur_tag = f" ↩ {task.frequency}" if task.frequency != "once" else ""
                label     = (
                    f"{icon} {task.time}  —  {task.title} for {pet_name}"
                    f"  ({task.duration_minutes} min){recur_tag}"
                )
                with st.expander(label, expanded=True):
                    ca, cb, cc = st.columns(3)
                    ca.metric("Priority",  task.priority.capitalize())
                    cb.metric("Duration",  f"{task.duration_minutes} min")
                    cc.metric("Frequency", task.frequency.capitalize())

                    if task.description:
                        st.caption(f"📝 {task.description}")

                    st.info(f"**Why scheduled:** {plan['explanation'][i]}")

                    if not task.completed:
                        if st.button("✅ Mark Complete", key=f"done_{i}_{task.title}_{pet_name}"):
                            scheduler.mark_task_complete(pet_name, task.title)
                            st.session_state.plan = scheduler.generate_daily_plan()
                            if task.frequency == "daily":
                                st.toast(
                                    f"Done! Next '{task.title}' scheduled for "
                                    f"{task.due_date + timedelta(days=1)}."
                                )
                            elif task.frequency == "weekly":
                                st.toast(
                                    f"Done! Next '{task.title}' scheduled for "
                                    f"{task.due_date + timedelta(weeks=1)}."
                                )
                            else:
                                st.toast(f"'{task.title}' marked complete!")
                            st.rerun()
                    else:
                        st.success("Already completed.")

# ── Tab 3: All Tasks ──────────────────────────────────────────────────────────
with tab3:
    st.header("All Tasks")

    col1, col2 = st.columns(2)
    with col1:
        filter_pet    = st.selectbox("Filter by pet",    ["All"] + [p.name for p in owner.pets])
    with col2:
        filter_status = st.selectbox("Filter by status", ["All", "Pending", "Completed"])

    all_tasks = scheduler.sort_by_time()

    if filter_pet != "All":
        all_tasks = [(pn, t) for pn, t in all_tasks if pn == filter_pet]
    if filter_status == "Pending":
        all_tasks = [(pn, t) for pn, t in all_tasks if not t.completed]
    elif filter_status == "Completed":
        all_tasks = [(pn, t) for pn, t in all_tasks if t.completed]

    if not all_tasks:
        st.info("No tasks match the current filters.")
    else:
        ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        # Header row
        h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1.5, 2.5, 1, 1.2, 1.5, 1.5, 1.5, 1.5])
        for col, label in zip(
            [h1, h2, h3, h4, h5, h6, h7, h8],
            ["Pet", "Task", "Time", "Duration", "Priority", "Frequency", "Due", "Action"],
        ):
            col.markdown(f"**{label}**")
        st.divider()

        for idx, (pn, t) in enumerate(all_tasks):
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.5, 2.5, 1, 1.2, 1.5, 1.5, 1.5, 1.5])
            c1.write(pn)
            c2.write(t.title)
            c3.write(t.time)
            c4.write(f"{t.duration_minutes} min")
            c5.write(f"{ICONS.get(t.priority, '')} {t.priority}")
            c6.write(t.frequency)
            c7.write(str(t.due_date))
            if t.completed:
                c8.write("✅ Done")
            else:
                if c8.button("Mark Done", key=f"alltask_{idx}_{pn}_{t.title}"):
                    scheduler.mark_task_complete(pn, t.title)
                    st.rerun()
