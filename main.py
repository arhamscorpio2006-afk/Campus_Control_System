"""MissionControl coordinator: loads data, runs conflict analysis, and starts the game."""

import os

from models import build_sections_from_records, Student, Instructor
from timetable import ConflictEngine, print_timetable_grid, print_conflict_stats
from game import Game, ExplorerCraft, DefenderCraft
from exceptions import InvalidActionError

DEFAULT_SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_state.json")

SAMPLE_RECORDS = [
    {"course_code": "IDS", "title": "Intro to Data Science", "section": "A", "day": "Monday", "start": "09:00", "end": "10:30", "room": "R-201", "instructor": "I-07", "students": ["25I-101", "25I-115"], "capacity": 2},
    {"course_code": "AI", "title": "Artificial Intelligence", "section": "A", "day": "Monday", "start": "09:00", "end": "10:00", "room": "R-305", "instructor": "I-11", "students": ["25I-101"], "capacity": 30},
    {"course_code": "DB", "title": "Databases", "section": "B", "day": "Tuesday", "start": "10:00", "end": "11:00", "room": "R-201", "instructor": "I-07", "students": ["25I-101", "25I-116"], "capacity": 25},
    {"course_code": "DB", "title": "Databases", "section": "A", "day": "Tuesday", "start": "10:00", "end": "11:30", "room": "R-102", "instructor": "I-09", "students": ["25I-120"], "capacity": 25},
    {"course_code": "AI", "title": "Artificial Intelligence", "section": "B", "day": "Wednesday", "start": "09:00", "end": "10:30", "room": "R-306", "instructor": "I-12", "students": ["25I-118"], "capacity": 30},
    {"course_code": "OS", "title": "Operating Systems", "section": "A", "day": "Wednesday", "start": "11:00", "end": "12:30", "room": "R-204", "instructor": "I-03", "students": ["25I-102"], "capacity": 30},
    {"course_code": "OOP", "title": "Object Oriented Programming", "section": "A", "day": "Thursday", "start": "09:00", "end": "10:30", "room": "R-101", "instructor": "I-02", "students": ["25I-103", "25I-104"], "capacity": 35},
    {"course_code": "OOP", "title": "Object Oriented Programming", "section": "B", "day": "Thursday", "start": "10:30", "end": "12:00", "room": "R-101", "instructor": "I-02", "students": ["25I-105"], "capacity": 35},
    {"course_code": "CN", "title": "Computer Networks", "section": "A", "day": "Friday", "start": "09:00", "end": "10:30", "room": "R-210", "instructor": "I-05", "students": ["25I-106"], "capacity": 30},
    {"course_code": "SE", "title": "Software Engineering", "section": "A", "day": "Friday", "start": "10:30", "end": "12:00", "room": "R-210", "instructor": "I-05", "students": ["25I-107"], "capacity": 30},
    {"course_code": "MATH", "title": "Linear Algebra", "section": "A", "day": "Monday", "start": "13:00", "end": "14:30", "room": "R-110", "instructor": "I-08", "students": ["25I-108"], "capacity": 40},
]

INVALID_RECORD = {"course_code": "BAD", "section": "Z", "day": "Someday", "start": "09:00", "end": "08:00", "room": "R-1", "instructor": "I-99", "students": []}


class MissionControl:

    def __init__(self):
        self.sections = []
        self.rejected = []
        self.engine = None
        self.game = None
        self.commands = {
            "load": self.load_data,
            "schedules": self.inspect_schedules_interactive,
            "conflicts": self.run_conflict_analysis,
            "startgame": self.start_and_play_interactive,
            "logs": self.view_logs,
            "save": self.save_game,
            "resume": self.resume_game,
            "status": self.status,
            "exit": self.exit_program,
        }
        self._running = True

    def status(self):
        section_count = len(self.sections)
        game_state = self.game.summary() if self.game else "no game started"
        return f"MissionControl: {section_count} section(s) loaded, {game_state}"

    def load_data(self, records=None):
        records = records if records is not None else SAMPLE_RECORDS + [INVALID_RECORD]
        self.sections, self.rejected = build_sections_from_records(records)
        self.engine = ConflictEngine(self.sections)
        print(f"Loaded {len(self.sections)} section(s), rejected {len(self.rejected)} record(s).")
        for record, reason in self.rejected:
            print(f"  rejected {record.get('course_code', '?')}: {reason}")

    def inspect_schedules(self, kind="student", identifier="24I-101"):
        if self.engine is None:
            print("Load data first.")
            return
        conflicts = self.engine.scan_timetable()
        print_timetable_grid(self.engine.sorted_sections(), conflicts, focus_id=identifier, focus_type=kind)

    def inspect_schedules_interactive(self):
        if self.engine is None:
            print("Load data first.")
            return
        kind = input("View by (student/instructor/room): ").strip().lower()
        if kind not in {"student", "instructor", "room"}:
            print("Unknown type, defaulting to student.")
            kind = "student"
        identifier = input(f"Enter the {kind} id: ").strip()
        self.inspect_schedules(kind=kind, identifier=identifier)

    def run_conflict_analysis(self):
        if self.engine is None:
            print("Load data first.")
            return
        conflicts = self.engine.scan_timetable()
        print(self.engine.summary_report(conflicts))
        print_conflict_stats(conflicts, self.engine)
        return conflicts

    def start_seeded_game(self, craft_type="explorer", seed=7):
        craft_cls = ExplorerCraft if craft_type == "explorer" else DefenderCraft
        craft = craft_cls("Odyssey", "Earth")
        self.game = Game(craft, seed=seed)
        print(f"Game started with {craft_cls.__name__} seed={seed}")

    def start_and_play_interactive(self):
        craft_type = input("Craft type (explorer/defender) [explorer]: ").strip().lower() or "explorer"
        if craft_type not in {"explorer", "defender"}:
            print("Unknown craft type, defaulting to explorer.")
            craft_type = "explorer"
        seed_text = input("Random seed (whole number) [7]: ").strip() or "7"
        try:
            seed = int(seed_text)
        except ValueError:
            print("Invalid seed, defaulting to 7.")
            seed = 7
        self.start_seeded_game(craft_type=craft_type, seed=seed)
        self.game.play()

    def run_game_actions(self, actions):
        if self.game is None:
            print("Start a game first.")
            return
        self.game.show_hud()
        won, lost = self.game.run_scripted(list(actions))
        self.game.show_hud()
        print("Result:", "WON" if won else ("LOST" if lost else "IN PROGRESS"))

    def view_logs(self):
        if self.game is None:
            print("No game logs yet.")
            return
        for line in self.game.craft.show_audit_trail():
            print(line)

    def save_game(self, path=None):
        path = path or DEFAULT_SAVE_PATH
        if self.game is None:
            print("No game to save.")
            return
        self.game.save(path)
        print(f"Saved to {path}")

    def resume_game(self, path=None):
        path = path or DEFAULT_SAVE_PATH
        if not os.path.exists(path):
            print(f"No save file found at {path}.")
            return
        self.game = Game.load(path)
        print(f"Resumed game at turn {self.game.turn}, location {self.game.craft.location}")
        resume_play = input("Resume playing now? (y/n): ").strip().lower()
        if resume_play == "y":
            self.game.play()

    def exit_program(self):
        self._running = False
        print("Exiting MissionControl.")

    def run_menu(self):
        print("Commands:", ", ".join(self.commands.keys()))
        while self._running:
            choice = input("Command: ").strip().lower()
            handler = self.commands.get(choice)
            if handler is None:
                print("Unknown command. Available:", ", ".join(self.commands.keys()))
                continue
            handler()


if __name__ == "__main__":
    MissionControl().run_menu()