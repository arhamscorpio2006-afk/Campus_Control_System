"""Domain model: people, sections, time slots, planets, missions, spacecraft, events."""

from exceptions import InvalidTimeError, DuplicateIdentifierError, InvalidRecordError, InvalidActionError

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


class Person:
   

    def __init__(self, name, identifier):
        self.name = name
        self._identifier = identifier
        self.__contact_info = {"email": f"{identifier.lower()}@campus.edu", "phone": None}

    @property
    def identifier(self):
        return self._identifier

    def contact(self):
        return dict(self.__contact_info)

    def role_summary(self):
        return f"{self.name} is a person on campus."

    def summary(self):
        return self.role_summary()

    def __str__(self):
        return f"{self.name} ({self._identifier})"


class Student(Person):
   

    def __init__(self, name, identifier, major="Undecided"):
        super().__init__(name, identifier)
        self.major = major
        self.enrolled_sections = set()

    def enroll(self, section_code):
        self.enrolled_sections.add(section_code)

    def role_summary(self):
        return f"Student {self.name} ({self._identifier}) majoring in {self.major}, enrolled in {len(self.enrolled_sections)} section(s)."


class Instructor(Person):
   

    def __init__(self, name, identifier, department="General"):
        super().__init__(name, identifier)
        self.department = department
        self.sections_taught = []

    def assign_section(self, section_code):
        self.sections_taught.append(section_code)

    def role_summary(self):
        return f"Instructor {self.name} ({self._identifier}) of {self.department}, teaching {len(self.sections_taught)} section(s)."


class TimeSlot:

    def __init__(self, day, start, end):
        if day not in DAYS:
            raise InvalidTimeError(f"Unknown day: {day}")
        self.day = day
        self.start_minutes = self._to_minutes(start)
        self.end_minutes = self._to_minutes(end)
        if self.end_minutes <= self.start_minutes:
            raise InvalidTimeError(f"End time must be later than start time for {day} {start}-{end}")

    @staticmethod
    def _to_minutes(value):
        try:
            hour, minute = value.split(":")
            return int(hour) * 60 + int(minute)
        except (ValueError, AttributeError) as exc:
            raise InvalidTimeError(f"Bad time format: {value}") from exc

    def interval(self):
        return (self.start_minutes, self.end_minutes)

    def overlaps(self, other):
        if self.day != other.day:
            return False
        return self.start_minutes < other.end_minutes and other.start_minutes < self.end_minutes

    def __str__(self):
        return f"{self.day} {self.start_minutes // 60:02d}:{self.start_minutes % 60:02d}-{self.end_minutes // 60:02d}:{self.end_minutes % 60:02d}"


class CourseSection:

    def __init__(self, course_code, title, section, instructor_id, room, timeslot, capacity=30):
        self.course_code = course_code
        self.title = title
        self.section = section
        self.instructor_id = instructor_id
        self.room = room
        self.timeslot = timeslot
        self.capacity = capacity
        self.enrolled_students = set()
        self.meta = {"tags": [], "history": {}}

    @property
    def section_id(self):
        return f"{self.course_code}-{self.section}"

    def enroll_student(self, student_id):
        self.enrolled_students.add(student_id)

    def is_over_capacity(self):
        return len(self.enrolled_students) > self.capacity

    def summary(self):
        return f"Section {self.section_id}: {len(self.enrolled_students)}/{self.capacity} enrolled at {self.room}"

    def __str__(self):
        return f"{self.section_id} {self.title} @ {self.room} [{self.timeslot}] ({len(self.enrolled_students)}/{self.capacity})"


def build_sections_from_records(records):
    required_keys = ("course_code", "section", "day", "start", "end", "room", "instructor", "students")
    sections = {}
    rejected = []
    for record in records:
        missing = [key for key in required_keys if key not in record]
        if missing:
            rejected.append((record, f"missing fields: {missing}"))
            continue
        try:
            timeslot = TimeSlot(record["day"], record["start"], record["end"])
            section = CourseSection(
                course_code=record["course_code"],
                title=record.get("title", record["course_code"]),
                section=record["section"],
                instructor_id=record["instructor"],
                room=record["room"],
                timeslot=timeslot,
                capacity=record.get("capacity", 30),
            )
            if section.section_id in sections:
                raise DuplicateIdentifierError(f"Duplicate section id: {section.section_id}")
            for student_id in record["students"]:
                section.enroll_student(student_id)
            sections[section.section_id] = section
        except (InvalidTimeError, DuplicateIdentifierError) as exc:
            rejected.append((record, str(exc)))
    return list(sections.values()), rejected


class Planet:
 

    def __init__(self, name, resources, danger_level=1):
        self.name = name
        self.resources = dict(resources)
        self.danger_level = danger_level
        self.visited = False

    def harvest(self, resource_name, amount):
        available = self.resources.get(resource_name, 0)
        taken = min(available, amount)
        self.resources[resource_name] = available - taken
        return taken

    def __str__(self):
        return f"Planet {self.name} (danger {self.danger_level})"


class Mission:


    def __init__(self, mission_id, description, planet_name, reward):
        self.mission_id = mission_id
        self.description = description
        self.planet_name = planet_name
        self.reward = reward
        self.completed = False
        self.accepted = False

    def accept(self):
        self.accepted = True

    def complete(self):
        self.completed = True

    def summary(self):
        state = "done" if self.completed else ("active" if self.accepted else "available")
        return f"Mission {self.mission_id} ({state}): {self.description}"

    def __str__(self):
        state = "done" if self.completed else ("active" if self.accepted else "available")
        return f"[{self.mission_id}] {self.description} @ {self.planet_name} -> {self.reward} ({state})"


class EventRecord:
  

    def __init__(self, event_type, turn, description, effect):
        self.event_type = event_type
        self.turn = turn
        self.description = description
        self.effect = effect

    def __str__(self):
        return f"Turn {self.turn}: [{self.event_type}] {self.description} -> {self.effect}"


class Spacecraft:


    def __init__(self, name, location, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.max_health = 100
        self.health = self.max_health
        self.fuel = 80
        self.oxygen = 100
        self.energy = 60
        self.cargo_capacity = 8
        self.cargo = []
        self.location = location
        self.mission_log = []
        self.discovered = {location}

    def status(self):
        return (f"{self.name} @ {self.location} | Hull {self.health}/{self.max_health} Fuel {self.fuel}/80 "
                f"Oxygen {self.oxygen}/100 Energy {self.energy}/60 Cargo {len(self.cargo)}/{self.cargo_capacity}")

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)

    def scan(self, planet):
        self.discovered.add(planet.name)
        return dict(planet.resources)

    def travel(self, destination, distance):
        fuel_cost = distance * 2
        oxygen_cost = distance
        try:
            if fuel_cost > self.fuel:
                raise InvalidActionError(f"Not enough fuel to reach {destination}")
            if oxygen_cost > self.oxygen:
                raise InvalidActionError(f"Not enough oxygen to reach {destination}")
        except InvalidActionError:
            raise
        else:
            self.fuel -= fuel_cost
            self.oxygen -= oxygen_cost
            self.location = destination
            self.discovered.add(destination)
            return True
        finally:
            self.mission_log.append(f"Attempted travel to {destination}")

    def repair(self, amount):
        try:
            if amount <= 0:
                raise InvalidActionError("Repair amount must be positive")
            if amount > self.energy:
                raise InvalidActionError("Not enough energy to repair that much")
        except InvalidActionError:
            raise
        else:
            self.energy -= amount
            self.health = min(self.max_health, self.health + amount)
            return True
        finally:
            self.mission_log.append(f"Attempted repair of {amount}")

    def __str__(self):
        return self.status()