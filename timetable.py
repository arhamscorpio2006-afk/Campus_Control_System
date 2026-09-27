"""Timetable conflict detection engine and terminal display helpers."""

from models import DAYS

RESET = "\033[0m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"

CONFLICT_TAGS = {
    "student": "!STUDENT",
    "instructor": "!INSTRUCTOR",
    "room": "!ROOM",
    "capacity": "!CAPACITY",
    "section": "!SECTION",
}


class Conflict:
  

    def __init__(self, conflict_type, section_a, section_b, day, interval):
        self.conflict_type = conflict_type
        self.section_a = section_a
        self.section_b = section_b
        self.day = day
        self.interval = interval

    def __str__(self):
        tag = CONFLICT_TAGS.get(self.conflict_type, "!CONFLICT")
        return f"{tag} {self.section_a.section_id} <-> {self.section_b.section_id} on {self.day} {self.interval}"


class ConflictEngine:
  

    def __init__(self, sections):
        self.sections = sections

    def compare_sections(self, section_a, section_b):
        found = []
        if not section_a.timeslot.overlaps(section_b.timeslot):
            return found
        day = section_a.timeslot.day
        interval = (
            max(section_a.timeslot.start_minutes, section_b.timeslot.start_minutes),
            min(section_a.timeslot.end_minutes, section_b.timeslot.end_minutes),
        )
        shared_students = section_a.enrolled_students & section_b.enrolled_students
        if shared_students:
            found.append(Conflict("student", section_a, section_b, day, interval))
        if section_a.instructor_id == section_b.instructor_id:
            found.append(Conflict("instructor", section_a, section_b, day, interval))
        if section_a.room == section_b.room:
            found.append(Conflict("room", section_a, section_b, day, interval))
        if section_a.course_code == section_b.course_code and section_a.section != section_b.section:
            found.append(Conflict("section", section_a, section_b, day, interval))
        return found

    def scan_timetable(self):
        all_conflicts = []
        for section in self.sections:
            if section.is_over_capacity():
                all_conflicts.append(Conflict("capacity", section, section, section.timeslot.day, section.timeslot.interval()))
        for i in range(len(self.sections)):
            for j in range(i + 1, len(self.sections)):
                all_conflicts.extend(self.compare_sections(self.sections[i], self.sections[j]))
        return all_conflicts

    def group_by_category(self, conflicts):
        grouped = {}
        for conflict in conflicts:
            grouped.setdefault(conflict.conflict_type, []).append(conflict)
        return grouped

    def student_schedule(self, student_id):
        return [section for section in self.sections if student_id in section.enrolled_students]

    def sorted_sections(self):
        return sorted(self.sections, key=lambda section: (section.timeslot.day, section.timeslot.start_minutes))

    def build_report(self, conflicts, formatter=str, title="Conflict Report", show_counts=True, limit=None):
        def format_lines(items):
            lines = [formatter(item) for item in items]
            return lines if limit is None else lines[:limit]

        lines = [f"=== {title} ==="]
        lines.extend(format_lines(conflicts))
        if show_counts:
            lines.append(f"Total: {len(conflicts)}")
        return "\n".join(lines)

    def summary_report(self, conflicts):
        def counter(conflict):
            return f"{conflict.conflict_type}: {conflict.section_a.section_id} vs {conflict.section_b.section_id}"
        return self.build_report(conflicts, formatter=counter, title="Summary", show_counts=True)

    def detailed_report(self, conflicts):
        return self.build_report(conflicts, formatter=str, title="Detailed", show_counts=False, limit=None)


def colorize(tag):
    if tag == "!STUDENT":
        return RED
    if tag == "!ROOM":
        return YELLOW
    if tag == "!INSTRUCTOR":
        return CYAN
    return GREEN


def print_conflict_stats(conflicts, engine):
    grouped = engine.group_by_category(conflicts)
    print("CONFLICT SUMMARY")
    print(" ".join(f"{key.capitalize()}: {len(value)}" for key, value in grouped.items()) or "No conflicts")


def print_timetable_grid(sections, conflicts, focus_id=None, focus_type="student"):
    hours = range(8, 18)
    conflicted_pairs = {}
    for conflict in conflicts:
        conflicted_pairs.setdefault(conflict.section_a.section_id, []).append(conflict.conflict_type)
        conflicted_pairs.setdefault(conflict.section_b.section_id, []).append(conflict.conflict_type)

    if focus_id:
        if focus_type == "student":
            sections = [s for s in sections if focus_id in s.enrolled_students]
        elif focus_type == "instructor":
            sections = [s for s in sections if s.instructor_id == focus_id]
        elif focus_type == "room":
            sections = [s for s in sections if s.room == focus_id]
        else:
            print(f"Unknown lookup type '{focus_type}'; showing the full timetable instead.")
        if not sections:
            print(f"No sections found for {focus_type} '{focus_id}'. Check the id and try again.")
            return

    header = " " * 9 + " ".join(f"{day[:9]:<12}" for day in DAYS)
    print(header)
    for hour in hours:
        row = f"{hour:02d}:00    "
        for day in DAYS:
            label = ""
            tag_text = ""
            for section in sections:
                if section.timeslot.day == day and section.timeslot.start_minutes // 60 == hour:
                    tags = conflicted_pairs.get(section.section_id, [])
                    tag_text = CONFLICT_TAGS.get(tags[0], "") if tags else ""
                    label = f"{section.section_id} {tag_text}".strip()
            visible = f"[{label}]" if label else "[ ]"
            color = colorize(tag_text) if tag_text else (GREEN if label else RESET)
            padding = " " * max(0, 20 - len(visible))
            row += f"{color}{visible}{RESET}{padding}"
        print(row)