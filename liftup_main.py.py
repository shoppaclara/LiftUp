import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from PIL import Image, ImageTk

# =============================================================================
# LiftUp — Workout Planning and Tracking App (Tkinter)
#
# This application supports three primary workflows:
#   1) Create and manage reusable workout plans (Plans).
#   2) Start and guide a workout session based on a plan (Track).
#   3) View summary statistics and recent workout history (Dashboard).
#
# Persistent storage:
#   - Plans are stored in workoutPlans.json
#   - Completed workout logs are stored in workoutLogs.json
#
# Transient runtime state:
#   - An in-progress workout is stored in LiftUp.current_workout until saved/exited.
# =============================================================================

PLANS_FILE = "workoutPlans.json"
LOGS_FILE = "workoutLogs.json"


# =============================================================================
# Data Persistence Helpers
# =============================================================================
def load_json(filename: str, default):
    """
    Load JSON data from disk.

    Args:
        filename: Path to the JSON file.
        default: Value to return if the file does not exist or is unreadable.

    Returns:
        Parsed JSON content (commonly a list or dict) or `default` on failure.

    Notes:
        The application is designed to be resilient to missing/corrupted files.
        In those cases, it falls back to an empty structure and continues.
    """
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename: str, data) -> None:
    """
    Write JSON data to disk.

    Args:
        filename: Destination JSON file path.
        data: Python structure to serialize to JSON.

    Notes:
        - Uses indent=2 for human-readable formatting.
        - Uses default=str so datetime-like objects can be serialized safely.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def parse_dt(value: str | None) -> datetime | None:
    """
    Parse an ISO-format datetime string to a datetime object.

    Args:
        value: Datetime string (typically produced by datetime.isoformat()).

    Returns:
        datetime instance if parsable, otherwise None.

    Notes:
        The app primarily stores datetimes as ISO strings in JSON. This helper
        centralizes parsing and provides a fallback format used by some systems.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")


# =============================================================================
# UI Utility Widgets
# =============================================================================
class ScrollableFrame(ttk.Frame):
    """
    A reusable scrollable container implemented with a Canvas + inner ttk.Frame.

    Purpose:
        Tkinter frames do not scroll natively. This widget hosts an inner frame
        inside a canvas and provides a vertical scrollbar. Child widgets should
        be created within `self.inner`.
    """

    def __init__(self, master, height: int = 300, **kwargs):
        super().__init__(master, **kwargs)

        canvas = tk.Canvas(self, height=height)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        self.inner = ttk.Frame(canvas)
        self.inner_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def on_configure(_event):
            """
            Update the canvas scrollregion to match the size of the inner content.

            This ensures the scrollbar accurately reflects the scrollable area.
            """
            bbox = canvas.bbox("all")
            if not bbox:
                return

            x1, y1, x2, y2 = bbox
            visible_h = canvas.winfo_height()

            # Prevent scrolling when content is shorter than the viewport.
            if (y2 - y1) < visible_h:
                y2 = y1 + visible_h

            canvas.configure(scrollregion=(x1, y1, x2, y2))

        self.inner.bind("<Configure>", on_configure)

        def on_canvas_resize(event):
            """
            Keep the inner frame width matched to the canvas width.

            This avoids horizontal clipping when the window is resized.
            """
            canvas.itemconfig(self.inner_id, width=event.width)

        canvas.bind("<Configure>", on_canvas_resize)


# =============================================================================
# Application Root (Controller)
# =============================================================================
class LiftUp(tk.Tk):
    """
    Main application window and controller.

    Responsibilities:
        - Load and hold persistent data (plans/logs).
        - Hold transient workout session state (current_workout).
        - Create and manage navigation between pages.
    """

    def __init__(self):
        super().__init__()

        self.title("Lift Up")
        self.geometry("1000x750")
        self.minsize(800, 500)

        # Persistent application data
        self.workout_plans = load_json(PLANS_FILE, [])
        self.workout_logs = load_json(LOGS_FILE, [])

        # Transient session state for an in-progress workout
        self.current_workout = None

        self.create_widgets()

    def create_widgets(self) -> None:
        """
        Build the navigation header and initialize page frames.

        Pages are created once and stacked in a shared container.
        Navigation simply raises the desired page to the front.
        """
        style = ttk.Style()
        style.configure("Indigo.TFrame", background="#3B3355")

        top_frame = ttk.Frame(self, style="Indigo.TFrame", padding=25)
        top_frame.pack(side="top", fill="x")

        top_frame.columnconfigure(0, weight=0)  # Logo
        top_frame.columnconfigure(1, weight=1)  # Title/subtitle
        top_frame.columnconfigure(2, weight=0)  # Navigation buttons

        # Logo (optional asset; must exist alongside script)
        logo_png = Image.open("logo_image.png")
        logo_image = ImageTk.PhotoImage(logo_png)
        logo_label = ttk.Label(top_frame, image=logo_image)
        logo_label.image = logo_image  # retain reference to prevent GC
        logo_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))

        # Title and subtitle
        title = ttk.Label(
            top_frame,
            text="LiftUp",
            font=("Gill Sans Ultra Bold Condensed", 20, "bold"),
            background="#3B3355",
            foreground="#FEFCFD",
        )
        title.grid(row=0, column=1, sticky="w", padx=(12, 12))

        subtitle = ttk.Label(
            top_frame,
            text="Plan, track, and monitor your lifts!",
            font=("Gill Sans", 12, "bold"),
            background="#3B3355",
            foreground="#BFCDE0",
        )
        subtitle.grid(row=1, column=1, sticky="w", padx=(12, 12))

        # Navigation button styling
        b_style = ttk.Style()
        b_style.configure(
            "IndigoButton.TButton",
            foreground="#5d5d81",
            font=("Gill Sans", 15, "bold"),
            padding=(15, 10),
            borderwidth=0,
        )

        btn_frame = ttk.Frame(top_frame, style="Indigo.TFrame")
        btn_frame.grid(row=0, column=2, rowspan=2, sticky="e")

        nav_buttons = [
            ("Dashboard", self.show_dashboard),
            ("Plans", self.show_plans),
            ("Track", self.show_track),
        ]
        for idx, (label, cmd) in enumerate(nav_buttons):
            ttk.Button(btn_frame, text=label, command=cmd, style="IndigoButton.TButton").grid(
                row=0, column=idx, padx=6
            )

        # Container for page frames
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=12, pady=8)

        self.pages: dict[str, ttk.Frame] = {}
        for PageClass in (DashboardPage, PlansPage, TrackPage):
            page = PageClass(self.container, self)
            self.pages[PageClass.__name__] = page
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_dashboard()

    # ---- Navigation callbacks -------------------------------------------------
    def show_dashboard(self) -> None:
        self.pages["DashboardPage"].refresh()
        self.pages["DashboardPage"].tkraise()

    def show_plans(self) -> None:
        self.pages["PlansPage"].refresh()
        self.pages["PlansPage"].tkraise()

    def show_track(self) -> None:
        self.pages["TrackPage"].refresh()
        self.pages["TrackPage"].tkraise()


# =============================================================================
# Dashboard Page
# =============================================================================
class DashboardPage(ttk.Frame):
    """
    Displays summary statistics and a recent-workouts list.

    Statistics include:
        - Total number of logged workouts
        - Workouts completed this week
        - Total completed sets across all logs
        - Average workout duration
    """

    def __init__(self, parent, app: LiftUp):
        super().__init__(parent)
        self.app = app

        header = ttk.Label(self, text="Track your lifting progress", font=("Gill Sans Bold", 16))
        header.pack(anchor="w", pady=(6, 12))

        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", pady=(0, 10))

        # StringVars allow UI labels to update dynamically during refresh()
        self.total_workouts_var = tk.StringVar(value="0")
        self.this_week_var = tk.StringVar(value="0")
        self.sets_completed_var = tk.StringVar(value="0")
        self.avg_duration_var = tk.StringVar(value="0m")

        stats_items = [
            ("Total Workouts", self.total_workouts_var),
            ("This Week", self.this_week_var),
            ("Sets Completed", self.sets_completed_var),
            ("Avg Duration", self.avg_duration_var),
        ]
        for i, (label_text, var) in enumerate(stats_items):
            frame = ttk.LabelFrame(stats_frame, text=label_text, padding=8)
            frame.grid(row=0, column=i, padx=6, sticky="n")
            ttk.Label(frame, textvariable=var, font=("Gill Sans", 14, "bold")).pack()

        ttk.Label(self, text="Recent Workouts", font=("Gill Sans", 12)).pack(anchor="w", pady=(10, 4))
        self.recent_scroll = ScrollableFrame(self, height=360)
        self.recent_scroll.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """
        Recompute statistics and rebuild the recent-workouts list.
        """
        logs = self.app.workout_logs

        # --- Aggregate stats ---------------------------------------------------
        total = len(logs)
        self.total_workouts_var.set(str(total))

        now = datetime.now()
        week_start = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
        this_week_count = sum(1 for l in logs if parse_dt(l["end_time"]) and parse_dt(l["end_time"]) >= week_start)
        self.this_week_var.set(str(this_week_count))

        sets_completed = 0
        durations_min: list[float] = []

        for entry in logs:
            # Count completed sets (if present in stored log structure)
            for ex in entry.get("exercises", []):
                sets_completed += sum(1 for s in ex.get("sets", []) if s.get("completed"))

            # Compute duration when times are valid
            try:
                start = parse_dt(entry["start_time"])
                end = parse_dt(entry["end_time"])
                if start and end:
                    durations_min.append((end - start).total_seconds() / 60.0)
            except Exception:
                pass

        self.sets_completed_var.set(str(sets_completed))

        if durations_min:
            avg_min = sum(durations_min) / len(durations_min)
            self.avg_duration_var.set(f"{avg_min:.0f}m")
        else:
            self.avg_duration_var.set("0m")

        # --- Recent list -------------------------------------------------------
        for widget in self.recent_scroll.inner.winfo_children():
            widget.destroy()

        recent_sorted = sorted(logs, key=lambda x: x.get("end_time", ""), reverse=True)
        for plan in recent_sorted[:10]:
            frame = ttk.Frame(self.recent_scroll.inner, relief="ridge", padding=8)
            frame.pack(fill="x", pady=4, padx=(0, 25))

            name = plan.get("plan_name", "Unknown Plan")
            date = plan.get("date", "")
            exercises = len(plan.get("exercises", []))
            sets = sum(len(ex.get("sets", [])) for ex in plan.get("exercises", []))

            ttk.Label(frame, text=name, font=("Gill Sans", 11, "bold")).pack(anchor="w")
            ttk.Label(frame, text=f"{date} • {exercises} exercises • {sets} sets").pack(anchor="w")


# =============================================================================
# Plans Page
# =============================================================================
class PlansPage(ttk.Frame):
    """
    Create, edit, and delete workout plans.

    A plan is a reusable template:
        {
            "name": str,
            "exercises": [
                {"name": str, "sets": [{"reps": int, "weight": int}, ...]},
                ...
            ]
        }
    """

    def __init__(self, parent, app: LiftUp):
        super().__init__(parent)
        self.app = app

        header = ttk.Label(self, text="Create and manage your workout routines", font=("Gill Sans", 16))
        header.pack(anchor="w", pady=(6, 12))

        top_controls = ttk.Frame(self)
        top_controls.pack(fill="x")

        b_style = ttk.Style()
        b_style.configure(
            "IndigoButton.TButton",
            foreground="#5d5d81",
            font=("Gill Sans", 15, "bold"),
            padding=(15, 10),
            borderwidth=0,
        )

        self.new_plan_btn = ttk.Button(
            top_controls, style="IndigoButton.TButton", text="+ New Plan", command=self.show_new_plan_frame
        )
        self.new_plan_btn.pack(side="left")

        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True, pady=(12, 0))

        self.plans_list_frame = ScrollableFrame(self.content, height=420)
        self.plans_list_frame.pack(fill="both", expand=True)

        # New-plan form container (shown/hidden as needed)
        self.new_plan_frame = ttk.Frame(self.content)

        # Internal state for the new/edit plan form
        self.exercise_frames = []
        self.edit_index = None

        self.build_new_plan_frame()
        self.show_list_view()

    def show_list_view(self) -> None:
        """
        Render the plan list view.

        Each plan is displayed with basic metadata and edit/delete controls.
        """
        self.plans_list_frame.pack(fill="both", expand=True)
        for child in self.plans_list_frame.inner.winfo_children():
            child.destroy()

        self.plans_list_frame.inner.columnconfigure(0, weight=1)

        b2_style = ttk.Style()
        b2_style.configure(
            "IndigoButton2.TButton",
            foreground="#5d5d81",
            font=("Gill Sans", 8, "bold"),
            padding=(2, 2),
            borderwidth=0,
        )

        for i, plan in enumerate(self.app.workout_plans):
            box = ttk.Frame(self.plans_list_frame.inner, relief="ridge", padding=8)
            box.grid(row=i, column=0, sticky="ew", pady=6, padx=(0, 25))
            box.columnconfigure(0, weight=1)

            name = plan.get("name", "Unnamed")
            exercises = len(plan.get("exercises", []))
            sets = sum(len(ex.get("sets", [])) for ex in plan.get("exercises", []))

            ttk.Label(box, text=name, font=("Gill Sans", 11, "bold")).grid(row=0, column=0, sticky="w")
            ttk.Label(box, text=f"{exercises} exercises • {sets} sets").grid(row=1, column=0, sticky="w")

            btn_frame = ttk.Frame(box)
            btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

            ttk.Button(
                btn_frame, text="Edit", style="IndigoButton2.TButton",
                command=lambda index_val=i: self.edit_plan(index=index_val)
            ).pack(side="top", pady=1, padx=5)

            ttk.Button(
                btn_frame, text="Delete", style="IndigoButton2.TButton",
                command=lambda index_val=i: self.delete_plan(index=index_val)
            ).pack(side="top", pady=1, padx=5)

    def build_new_plan_frame(self) -> None:
        """
        Construct the new/edit plan form UI.

        The form is rebuilt on refresh to ensure a clean state.
        """
        f = self.new_plan_frame

        for widget in f.winfo_children():
            widget.destroy()

        ttk.Label(f, text="Create New Plan", font=("Gill Sans", 14)).pack(anchor="w", pady=(0, 8))

        ttk.Label(f, text="Plan Name").pack(anchor="w")
        self.plan_name_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.plan_name_var).pack(fill="x", pady=(0, 8))

        ttk.Label(f, text="Exercises").pack(anchor="w")
        self.ex_scroll = ScrollableFrame(f, height=260)
        self.ex_scroll.pack(fill="both", expand=True, pady=(2, 8))
        self.exercise_frames = []

        ttk.Button(f, text="+ Add Exercise", command=lambda: self.add_exercise_frame()).pack(anchor="w", pady=(0, 8))

        btns = ttk.Frame(f)
        btns.pack(anchor="e")
        self.save_btn = ttk.Button(btns, text="Save Plan", command=self.save_plan)
        self.save_btn.pack(side="right", padx=6)
        ttk.Button(btns, text="Cancel", command=self.refresh).pack(side="right")

    def show_new_plan_frame(self, prefill=None, edit_index=None) -> None:
        """
        Switch from list view to the new/edit plan form.

        Args:
            prefill: Existing plan data to populate the form (used for editing).
            edit_index: Index of the plan being edited (None when creating a new plan).
        """
        self.plans_list_frame.pack_forget()
        self.new_plan_frame.pack(fill="both")

        self.edit_index = edit_index if edit_index is not None else None

        if prefill:
            self.plan_name_var.set(prefill.get("name", ""))

            for w in self.ex_scroll.inner.winfo_children():
                w.destroy()
            self.exercise_frames = []

            for ex in prefill.get("exercises", []):
                self.add_exercise_frame(prefill=ex)
        else:
            # Provide at least one exercise block by default for usability.
            self.add_exercise_frame()

    def add_exercise_frame(self, prefill=None) -> None:
        """
        Add an exercise editor block to the plan form.

        Each exercise block includes:
            - Exercise name entry
            - One or more set rows (reps/weight)
            - Buttons to add sets or remove the exercise
        """
        idx = len(self.exercise_frames) + 1
        frame = ttk.LabelFrame(self.ex_scroll.inner, text=f"Exercise {idx}", padding=8)
        frame.pack(fill="both", pady=6)

        ttk.Label(frame, text="Exercise Name: ").grid(row=0, column=0, sticky="w")
        ex_name_var = tk.StringVar(value=(prefill.get("name") if prefill else ""))
        ttk.Entry(frame, textvariable=ex_name_var).grid(row=1, column=0, sticky="we")

        sets_frame = ttk.Frame(frame)
        sets_frame.grid(row=2, column=0, columnspan=3, sticky="we")

        sets_entries = []

        def add_set(pref=None) -> None:
            """
            Add a set row to the current exercise block.

            The row stores StringVars for reps and weight so they can be collected
            during save_plan().
            """
            set_idx = len(sets_entries) + 1
            row = ttk.Frame(sets_frame)
            row.pack(fill="x", pady=2)

            ttk.Label(row, text=f"Set {set_idx}").pack(side="left")

            reps_var = tk.StringVar(value=str(pref.get("reps")) if (pref and "reps" in pref) else "")
            weight_var = tk.StringVar(value=str(pref.get("weight")) if (pref and "weight" in pref) else "")

            ttk.Entry(row, width=8, textvariable=reps_var).pack(side="left", padx=(8, 6))
            ttk.Label(row, text="reps").pack(side="left")

            ttk.Entry(row, width=8, textvariable=weight_var).pack(side="left", padx=(8, 6))
            ttk.Label(row, text="lbs").pack(side="left")

            sets_entries.append({"reps_var": reps_var, "weight_var": weight_var, "widget": row})

        if prefill and "sets" in prefill:
            for s in prefill["sets"]:
                add_set(pref=s)
        else:
            add_set()

        ttk.Button(frame, text="+ Add Set", command=add_set).grid(row=3, column=0, pady=(8, 0), sticky="w")

        def remove_exercise() -> None:
            """
            Remove the current exercise block and re-number remaining blocks.
            """
            frame.destroy()

            for i, item in enumerate(self.exercise_frames):
                if item["frame"] is frame:
                    del self.exercise_frames[i]
                    break

            for j, item in enumerate(self.exercise_frames, start=1):
                item["frame"].configure(text=f"Exercise {j}")

        ttk.Button(frame, text="Remove Exercise", command=remove_exercise).grid(
            row=3, column=1, pady=(8, 0), sticky="e"
        )

        self.exercise_frames.append({"frame": frame, "ex_name_var": ex_name_var, "sets": sets_entries, "add_set": add_set})

    def save_plan(self) -> None:
        """
        Validate and persist the current plan form.

        - Ensures plan name exists
        - Validates reps/weight fields are integers
        - Writes to disk, either updating an existing plan or appending a new one
        """
        name = self.plan_name_var.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Please enter a plan name")
            return

        plan = {"name": name, "exercises": []}

        for ex in self.exercise_frames:
            ex_name = ex["ex_name_var"].get().strip() or "Unnamed Exercise"
            sets_data = []

            for s in ex["sets"]:
                reps = s["reps_var"].get().strip()
                weight = s["weight_var"].get().strip()

                try:
                    reps_i = int(reps) if reps != "" else 0
                    weight_i = int(weight) if weight != "" else 0
                except ValueError:
                    messagebox.showerror("Invalid input", "Reps and weights must be integers.")
                    return

                sets_data.append({"reps": reps_i, "weight": weight_i})

            plan["exercises"].append({"name": ex_name, "sets": sets_data})

        if self.edit_index is not None:
            self.app.workout_plans[self.edit_index] = plan
            self.edit_index = None
        else:
            self.app.workout_plans.append(plan)

        save_json(PLANS_FILE, self.app.workout_plans)
        messagebox.showinfo("Saved", f"Plan {name} saved.")
        self.refresh()

    def refresh(self) -> None:
        """
        Reset the plan editor state and return to list view.
        """
        self.plan_name_var.set("")
        self.edit_index = None

        self.exercise_frames = []
        for w in self.ex_scroll.inner.winfo_children():
            w.destroy()

        self.build_new_plan_frame()
        self.new_plan_frame.pack_forget()
        self.show_list_view()

    def delete_plan(self, index: int) -> None:
        """
        Delete a plan after confirmation and persist changes.
        """
        plan = self.app.workout_plans[index]
        if messagebox.askyesno("Delete", f"Delete plan {plan.get('name')} ?'"):
            del self.app.workout_plans[index]
            save_json(PLANS_FILE, self.app.workout_plans)
            self.refresh()

    def edit_plan(self, index: int) -> None:
        """
        Open the new/edit plan form prefilled with the selected plan.
        """
        plan = self.app.workout_plans[index]
        self.show_new_plan_frame(prefill=plan, edit_index=index)


# =============================================================================
# Track Page
# =============================================================================
class TrackPage(ttk.Frame):
    """
    Guides the user through a workout session based on a selected plan.

    Workflow:
        - User selects a plan
        - start_workout() creates a session state under app.current_workout
        - show_active_workout() renders the current set and accepts input
        - complete_set() records performance and advances progress
        - finish_and_save() writes a finalized workout log to disk
    """

    def __init__(self, parent, app: LiftUp):
        super().__init__(parent)
        self.app = app

        header = ttk.Label(self, text="Start Your Workout", font=("Gill Sans", 16))
        header.pack(anchor="w", pady=(6, 12))

        ttk.Label(self, text="Choose a plan and start your guided workout session: ").pack(anchor="w")

        selector_frame = ttk.Frame(self, padding=(0, 8))
        selector_frame.pack(fill="x")

        ttk.Label(selector_frame, text="Select Workout Plan:", font=("Gill Sans", 16)).grid(row=0)
        self.plan_combo = ttk.Combobox(selector_frame, values=[], state="readonly")
        self.plan_combo.set("Choose a workout plan!")
        self.plan_combo.grid(row=0, column=1, padx=8, sticky="we")
        selector_frame.columnconfigure(1, weight=1)
        self.plan_combo.bind("<<ComboboxSelected>>", lambda _e: self.plan_selected())

        self.plan_info_box = ttk.LabelFrame(self, text="Plan Info", padding=8)
        self.plan_info_box.pack(fill="x", pady=(8, 12))
        self.plan_info_text = tk.StringVar(value="")
        ttk.Label(self.plan_info_box, textvariable=self.plan_info_text).pack(anchor="w")

        start_btn = ttk.Button(self, style="IndigoButton.TButton", text="Start Workout", command=self.start_workout)
        start_btn.pack(anchor="w", pady=(6, 0))

        # Active workout UI is constructed dynamically when a workout starts.
        self.active_frame = ttk.Frame(self, relief="groove", padding=8)

    def refresh(self) -> None:
        """
        Refresh plan dropdown values and hide the active workout UI when idle.
        """
        names = [p.get("name", "Unnamed") for p in self.app.workout_plans]
        self.plan_combo["values"] = names
        self.plan_combo.set("Choose a workout plan!")
        self.plan_info_text.set("")

        if self.app.current_workout is None:
            self.active_frame.pack_forget()

    def plan_selected(self) -> None:
        """
        Update the plan info box with a summary of the currently selected plan.
        """
        idx = self.plan_combo.current()
        if idx < 0:
            return

        plan = self.app.workout_plans[idx]
        ex_list = plan.get("exercises", [])
        ex_count = len(ex_list)
        total_sets = sum(len(ex.get("sets", [])) for ex in ex_list)
        ex_names = ", ".join(ex.get("name", "") for ex in ex_list)

        self.plan_info_text.set(f"{ex_count} exercises • {total_sets} sets\nExercises: {ex_names}")

    def start_workout(self) -> None:
        """
        Initialize an in-progress workout session based on the selected plan.

        The session state mirrors the plan but adds per-set completion fields:
            - completed (bool)
            - reps_done / weight_done (user performance)
        """
        idx = self.plan_combo.current()
        if idx < 0:
            messagebox.showerror("No plan selected", "Please choose a workout plan first.")
            return

        plan = self.app.workout_plans[idx]

        self.app.current_workout = {
            "plan_index": idx,
            "plan_name": plan.get("name"),
            "start_time": datetime.now().isoformat(),
            "exercises": [],
            "saved_sets": [],
            "progress": {"exercise_idx": 0, "set_idx": 0},
        }

        for ex in plan.get("exercises", []):
            ex_copy = {"name": ex.get("name"), "sets": []}
            for s in ex.get("sets", []):
                ex_copy["sets"].append(
                    {
                        "target_reps": s.get("reps", 0),
                        "target_weight": s.get("weight", 0),
                        "completed": False,
                        "reps_done": None,
                        "weight_done": None,
                    }
                )
            self.app.current_workout["exercises"].append(ex_copy)

        self.show_active_workout()

    def show_active_workout(self) -> None:
        """
        Render the current step in the active workout.

        This method:
            - Clears and rebuilds the active workout panel
            - Shows the current exercise/set targets
            - Accepts input for completed reps/weight
            - Provides controls to skip or complete the current set
        """
        self.active_frame.pack(fill="both", expand=True, pady=(12, 0))

        for w in self.active_frame.winfo_children():
            w.destroy()

        top = ttk.Frame(self.active_frame)
        top.pack(fill="x")
        ttk.Button(top, text="Exit", command=self.exit_workout).pack(side="left")

        ttk.Label(top, text=self.app.current_workout["plan_name"], font=("Gill Sans", 12, "bold")).pack(
            side="left", padx=(12, 8)
        )

        cur_box = ttk.LabelFrame(self.active_frame, padding=8)
        cur_box.pack(fill="x", pady=(8, 6))

        cur = self.app.current_workout["progress"]
        cei = cur["exercise_idx"]
        csi = cur["set_idx"]
        exercises = self.app.current_workout["exercises"]

        # Terminal state: all exercises complete
        if cei >= len(exercises):
            ttk.Label(cur_box, text=f"Workout Complete\nGreat job! You completed {len(exercises)} exercises").pack()
            ttk.Button(self.active_frame, text="Save workout", command=self.finish_and_save).pack(anchor="e", pady=(8, 0))
            return

        cur_ex = exercises[cei]
        ttk.Label(cur_box, text=cur_ex["name"], font=("Gill Sans", 12, "bold")).pack(anchor="w")

        total_sets = len(cur_ex["sets"])
        ttk.Label(cur_box, text=f"Set {csi + 1} of {total_sets}").pack(anchor="w")

        target = cur_ex["sets"][csi]
        ttk.Label(
            cur_box,
            text=f"Target: {target.get('target_reps', 0)} reps @ {target.get('target_weight', 0)} lbs",
        ).pack(anchor="w", pady=(4, 8))

        input_frame = ttk.Frame(cur_box)
        input_frame.pack(fill="x", pady=(4, 4))

        ttk.Label(input_frame, text="Reps Completed").grid(row=0, column=0, sticky="w")
        reps_var = tk.StringVar(value=str(target.get("target_reps", "") or ""))
        ttk.Entry(input_frame, textvariable=reps_var).grid(row=1, column=0, padx=(8, 0))

        ttk.Label(input_frame, text="Weight").grid(row=0, column=1, sticky="w")
        wt_var = tk.StringVar(value=str(target.get("target_weight", "") or ""))
        ttk.Entry(input_frame, textvariable=wt_var).grid(row=1, column=1, padx=(8, 0))

        btn_frame = ttk.Frame(self.active_frame)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Skip Set", command=lambda: self.next_set()).pack(side="left")
        ttk.Button(
            btn_frame,
            text="Complete Set",
            command=lambda: self.complete_set(reps_var.get().strip(), wt_var.get().strip()),
        ).pack(side="right")

    def next_set(self) -> None:
        """
        Advance progress to the next set (or next exercise if the set list is finished).

        This does not modify completion values; it simply moves the current index.
        """
        cur = self.app.current_workout["progress"]
        cei = cur["exercise_idx"]
        csi = cur["set_idx"]
        exercises = self.app.current_workout["exercises"]

        if cei >= len(exercises):
            return

        if csi + 1 < len(exercises[cei]["sets"]):
            cur["set_idx"] += 1
        else:
            cur["exercise_idx"] += 1
            cur["set_idx"] = 0

        self.show_active_workout()

    def complete_set(self, reps_str: str, wt_str: str) -> None:
        """
        Mark the current set as completed and store the user's performance.

        Args:
            reps_str: User-entered reps string (may be empty).
            wt_str: User-entered weight string (may be empty).

        Behavior:
            - If input is empty, target values are used.
            - Values must be integers; otherwise an error dialog is shown.
            - After saving, progress advances to the next set.
        """
        cur = self.app.current_workout["progress"]
        cei = cur["exercise_idx"]
        csi = cur["set_idx"]
        exercises = self.app.current_workout["exercises"]

        set_info = exercises[cei]["sets"][csi]

        try:
            reps_i = int(reps_str) if reps_str != "" else int(set_info.get("target_reps", 0))
            wt_i = int(wt_str) if wt_str != "" else int(set_info.get("target_weight", 0))
        except ValueError:
            messagebox.showerror("Invalid input", "Reps and weight must be integers.")
            return

        set_info["completed"] = True
        set_info["reps_done"] = reps_i
        set_info["weight_done"] = wt_i

        self.next_set()

    def exit_workout(self) -> None:
        """
        Exit the active workout session after confirmation.

        This discards the in-progress session state without saving a log entry.
        """
        if messagebox.askyesno("Exit", "Exit workout? Unsaved progress will be lost."):
            self.app.current_workout = None
            self.refresh()

    def finish_and_save(self) -> None:
        """
        Finalize the current workout and write a log entry to disk.

        The log captures:
            - Plan metadata (name/index)
            - Start/end timestamps
            - Per-set targets and completion results
        """
        cw = self.app.current_workout
        if cw is None:
            return

        end_time = datetime.now()
        _start_time = parse_dt(cw["start_time"])  # parsed for potential extension/validation

        exercise_log = []
        for ex in cw["exercises"]:
            ex_log = {"name": ex["name"], "sets": []}
            for s in ex["sets"]:
                ex_log["sets"].append(
                    {
                        "target_reps": s.get("target_reps"),
                        "target_weight": s.get("target_weight"),
                        "completed": s.get("completed"),
                        "reps_done": s.get("reps_done"),
                        "weight_done": s.get("weight_done"),
                    }
                )
            exercise_log.append(ex_log)

        log_entry = {
            "plan_name": cw.get("plan_name"),
            "plan_index": cw.get("plan_index"),
            "date": end_time.strftime("%Y-%m-%d"),
            "start_time": cw.get("start_time"),
            "end_time": end_time.isoformat(),
            "exercises": exercise_log,
        }

        self.app.workout_logs.append(log_entry)
        save_json(LOGS_FILE, self.app.workout_logs)

        self.app.current_workout = None
        messagebox.showinfo("Saved", "Workout saved to history.")
        self.refresh()


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    app = LiftUp()
    app.mainloop()
