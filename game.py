"""Turn-based space survival game reusing the Spacecraft/Planet/Mission model."""

import random
import json

from models import Spacecraft, Planet, Mission, EventRecord
from exceptions import InvalidActionError

PLANET_ORDER = ["Earth", "Kepler-1", "Kepler-2", "Nexus", "Finale"]

PLANET_MAP = {
    "Earth": {"neighbors": {"Kepler-1": 2}, "resources": {"fuel_cell": 3, "metal": 2}, "danger": 1},
    "Kepler-1": {"neighbors": {"Earth": 2, "Kepler-2": 3}, "resources": {"metal": 4, "water": 2}, "danger": 2},
    "Kepler-2": {"neighbors": {"Kepler-1": 3, "Nexus": 2}, "resources": {"water": 3, "crystal": 1}, "danger": 3},
    "Nexus": {"neighbors": {"Kepler-2": 2, "Finale": 4}, "resources": {"crystal": 3, "fuel_cell": 2}, "danger": 4},
    "Finale": {"neighbors": {"Nexus": 4}, "resources": {"crystal": 5}, "danger": 5},
}


class Auditable:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_trail = []

    def record_event(self, event_type, turn, description, effect):
        entry = EventRecord(event_type, turn, description, effect)
        self.audit_trail.append(entry)
        return entry

    def show_audit_trail(self):
        return [str(entry) for entry in self.audit_trail]


class ExplorerCraft(Spacecraft, Auditable):
    """A scouting craft that is efficient with fuel but fragile."""

    def __init__(self, name, location):
        super().__init__(name, location)
        self.cargo_capacity = 10

    def travel(self, destination, distance):
        cheaper_distance = max(1, distance - 1)
        return super().travel(destination, cheaper_distance)

    def scan(self, planet):
        data = super().scan(planet)
        self.energy = max(0, self.energy - 2)
        return data


class DefenderCraft(Spacecraft, Auditable):

    def __init__(self, name, location):
        super().__init__(name, location)
        self.max_health = 130
        self.health = self.max_health

    def take_damage(self, amount):
        reduced = max(0, amount - 5)
        super().take_damage(reduced)

    def travel(self, destination, distance):
        return super().travel(destination, distance + 1)


def event_resource_gain(craft, rng):
    resource = rng.choice(["metal", "water", "crystal"])
    craft.cargo.append(resource)
    return f"Found {resource} in deep space", f"cargo +1 ({resource})"


def event_fuel_loss(craft, rng):
    loss = rng.randint(5, 15)
    craft.fuel = max(0, craft.fuel - loss)
    return "Fuel leak detected", f"fuel -{loss}"


def event_oxygen_loss(craft, rng):
    loss = rng.randint(5, 12)
    craft.oxygen = max(0, craft.oxygen - loss)
    return "Oxygen seal failure", f"oxygen -{loss}"


def event_hull_damage(craft, rng):
    damage = rng.randint(5, 20)
    craft.take_damage(damage)
    return "Micrometeorite impact", f"hull -{damage}"


def event_system_malfunction(craft, rng):
    loss = rng.randint(5, 15)
    craft.energy = max(0, craft.energy - loss)
    return "System malfunction", f"energy -{loss}"


def event_beneficial_repair(craft, rng):
    gain = rng.randint(5, 15)
    craft.health = min(craft.max_health, craft.health + gain)
    return "Friendly drone patched the hull", f"hull +{gain}"


def event_energy_surge(craft, rng):
    gain = rng.randint(5, 15)
    craft.energy = min(60, craft.energy + gain)
    return "Solar flare recharged the batteries", f"energy +{gain}"


def event_solar_storm(craft, rng):
    craft.energy = max(0, craft.energy - 15)
    craft.take_damage(7)
    return "Solar storm", "energy -15, hull -7"


EVENTS = {
    "resource_gain": event_resource_gain,
    "fuel_loss": event_fuel_loss,
    "oxygen_loss": event_oxygen_loss,
    "hull_damage": event_hull_damage,
    "system_malfunction": event_system_malfunction,
    "beneficial_repair": event_beneficial_repair,
    "energy_surge": event_energy_surge,
    "solar_storm": event_solar_storm,
}


class Game:

    def __init__(self, craft, seed=42, turn_limit=20):
        self.craft = craft
        self.rng = random.Random(seed)
        self.turn_limit = turn_limit
        self.turn = 0
        self.planets = {name: Planet(name, data["resources"], data["danger"]) for name, data in PLANET_MAP.items()}
        self.missions = [
            Mission("M1", "Deliver crystal sample", "Kepler-2", "fuel"),
            Mission("M2", "Map Nexus resources", "Nexus", "energy"),
            Mission("M3", "Retrieve Finale core", "Finale", "hull"),
        ]
        self.won = False
        self.lost = False

    def summary(self):
        completed = sum(1 for mission in self.missions if mission.completed)
        return f"Game turn {self.turn}/{self.turn_limit}, craft at {self.craft.location}, {completed}/3 missions done"

    def show_hud(self):
        completed = sum(1 for mission in self.missions if mission.completed)
        print("================ SPACE SURVIVAL ================")
        print(f"Turn: {self.turn}/{self.turn_limit} Craft: {self.craft.name}")
        print(self.craft.status())
        print(f"Missions: {completed}/3")
        self.show_route_map()

    def show_route_map(self):
        pieces = []
        for name in PLANET_ORDER:
            marker = name
            if name == self.craft.location:
                marker = f"[{name}*]"
            elif name in self.craft.discovered:
                marker = f"[{name}]"
            else:
                marker = "[???]"
            pieces.append(marker)
        print(" -- ".join(pieces))

    def trigger_event(self, event_name=None):
        name = event_name or self.rng.choice(list(EVENTS.keys()))
        handler = EVENTS[name]
        description, effect = handler(self.craft, self.rng)
        record = self.craft.record_event(name, self.turn, description, effect)
        print(f"EVENT: {record.description} -> {record.effect}")
        return record

    def action_travel(self, destination):
        if destination not in PLANET_MAP.get(self.craft.location, {}).get("neighbors", {}):
            raise InvalidActionError(f"No direct route from {self.craft.location} to {destination}")
        distance = PLANET_MAP[self.craft.location]["neighbors"][destination]
        self.craft.travel(destination, distance)

    def action_scan(self):
        planet = self.planets[self.craft.location]
        return self.craft.scan(planet)

    def action_collect(self, resource_name, amount=1):
        if len(self.craft.cargo) + amount > self.craft.cargo_capacity:
            raise InvalidActionError("Cargo hold is full")
        planet = self.planets[self.craft.location]
        taken = planet.harvest(resource_name, amount)
        if taken <= 0:
            raise InvalidActionError(f"No {resource_name} left on {self.craft.location}")
        for _ in range(taken):
            self.craft.cargo.append(resource_name)

    def action_repair(self, amount):
        self.craft.repair(amount)

    def action_accept_mission(self, mission_id):
        for mission in self.missions:
            if mission.mission_id == mission_id and not mission.accepted:
                mission.accept()
                return
        raise InvalidActionError(f"Mission {mission_id} unavailable")

    def action_abandon_mission(self, mission_id):
        for mission in self.missions:
            if mission.mission_id == mission_id and mission.accepted and not mission.completed:
                mission.accepted = False
                return
        raise InvalidActionError(f"Mission {mission_id} cannot be abandoned")

    def show_actions_menu(self):
        print("1 Travel      2 Scan          3 Collect      4 Repair")
        print("5 Accept Msn  6 Abandon Msn   7 Upgrade      8 View Missions")
        print("9 Inventory   10 Event Log    11 Quit")

    def show_missions(self):
        print("--- Missions ---")
        for mission in self.missions:
            print(mission.summary())

    def show_inventory(self):
        print(f"--- Cargo ({len(self.craft.cargo)}/{self.craft.cargo_capacity}) ---")
        if not self.craft.cargo:
            print("(empty)")
        else:
            for item in self.craft.cargo:
                print("-", item)

    def show_event_log(self):
        print("--- Event Log ---")
        lines = self.craft.show_audit_trail()
        if not lines:
            print("(no events yet)")
        for line in lines:
            print(line)

    def show_available_routes(self):
        neighbors = PLANET_MAP.get(self.craft.location, {}).get("neighbors", {})
        print("Reachable from", self.craft.location, ":", ", ".join(neighbors) or "nowhere")

    def play(self):

        print("Welcome aboard! Enter the number for an action each turn.")
        while True:
            if self.won or self.lost:
                break
            self.show_hud()
            self.show_actions_menu()
            choice = input("Choose action (1-11): ").strip()

            if choice == "11":
                print("Quitting game.")
                break
            elif choice == "8":
                self.show_missions()
                continue
            elif choice == "9":
                self.show_inventory()
                continue
            elif choice == "10":
                self.show_event_log()
                continue
            elif choice not in {"1", "2", "3", "4", "5", "6", "7"}:
                print("Invalid choice, please enter a number from the menu.")
                continue

            turn_consuming = choice in {"1", "2", "3", "4"}
            try:
                if choice == "1":
                    self.show_available_routes()
                    destination = input("Destination planet: ").strip()
                    self.action_travel(destination)
                elif choice == "2":
                    data = self.action_scan()
                    print("Scan results:", data)
                elif choice == "3":
                    resource = input("Resource to collect: ").strip()
                    self.action_collect(resource, 1)
                elif choice == "4":
                    amount_text = input("Repair amount (uses energy): ").strip()
                    amount = int(amount_text)
                    self.action_repair(amount)
                elif choice == "5":
                    mission_id = input("Mission id to accept: ").strip()
                    self.action_accept_mission(mission_id)
                elif choice == "6":
                    mission_id = input("Mission id to abandon: ").strip()
                    self.action_abandon_mission(mission_id)
                elif choice == "7":
                    upgrade_name = input("Upgrade name (cargo_bay/reactor): ").strip()
                    self.install_upgrade(upgrade_name)
            except InvalidActionError as exc:
                print("Action failed:", exc)
                continue
            except ValueError:
                print("Please enter a valid whole number.")
                continue

            if turn_consuming:
                self.turn += 1
                self.trigger_event()
            self.check_mission_completion()
            self.check_end_conditions()

        self.show_hud()
        if self.won:
            print("MISSION SUCCESS - reached Finale with all missions complete!")
        elif self.lost:
            print("GAME OVER.")
        else:
            print("Game ended by player.")
        return self.won, self.lost

    def check_mission_completion(self):
        for mission in self.missions:
            if mission.accepted and not mission.completed and mission.planet_name == self.craft.location:
                mission.complete()
                print(f"Mission completed: {mission}")

    def install_upgrade(self, upgrade_name):
        upgrades = {"cargo_bay": ("cargo_capacity", 2), "reactor": ("energy", 10)}
        if upgrade_name not in upgrades:
            raise InvalidActionError(f"Unknown upgrade: {upgrade_name}")
        attribute, amount = upgrades[upgrade_name]
        setattr(self.craft, attribute, getattr(self.craft, attribute) + amount)

    def check_end_conditions(self):
        completed = sum(1 for mission in self.missions if mission.completed)
        if self.craft.location == "Finale" and completed >= 3:
            self.won = True
        if not self.won and (self.craft.health <= 0 or self.craft.oxygen <= 0):
            self.lost = True
        if not self.won and self.turn >= self.turn_limit:
            self.lost = True

    def run_scripted(self, actions):
        """Run the game loop with a pre-scripted list of actions, for automated testing/demos.

        Mirrors play()'s rules: travel/scan/collect/repair consume a turn and trigger an
        event; accept/abandon/upgrade/log are free administrative actions.
        """
        turn_consuming_kinds = {"travel", "scan", "collect", "repair"}
        for action in list(actions):
            if self.won or self.lost or self.turn >= self.turn_limit:
                break
            kind = action[0]
            if kind == "quit":
                break
            try:
                if kind == "travel":
                    self.action_travel(action[1])
                elif kind == "scan":
                    self.action_scan()
                elif kind == "collect":
                    self.action_collect(action[1], action[2] if len(action) > 2 else 1)
                elif kind == "repair":
                    self.action_repair(action[1])
                elif kind == "accept":
                    self.action_accept_mission(action[1])
                elif kind == "abandon":
                    self.action_abandon_mission(action[1])
                elif kind == "upgrade":
                    self.install_upgrade(action[1])
                elif kind == "log":
                    continue
                else:
                    continue
            except InvalidActionError as exc:
                print(f"Action failed: {exc}")
                continue
            if kind in turn_consuming_kinds:
                self.turn += 1
                self.trigger_event()
            self.check_mission_completion()
            self.check_end_conditions()
            if self.won or self.lost:
                break
        return self.won, self.lost

    def to_state(self):
        return {
            "craft_name": self.craft.name,
            "craft_type": type(self.craft).__name__,
            "health": self.craft.health,
            "max_health": self.craft.max_health,
            "fuel": self.craft.fuel,
            "oxygen": self.craft.oxygen,
            "energy": self.craft.energy,
            "cargo_capacity": self.craft.cargo_capacity,
            "cargo": list(self.craft.cargo),
            "location": self.craft.location,
            "discovered": list(self.craft.discovered),
            "turn": self.turn,
            "turn_limit": self.turn_limit,
            "seed_state": self.rng.getstate(),
            "won": self.won,
            "lost": self.lost,
            "missions": [
                {"id": m.mission_id, "accepted": m.accepted, "completed": m.completed}
                for m in self.missions
            ],
        }

    def save(self, path):
        with open(path, "w") as file:
            json.dump(self.to_state(), file, indent=2)

    @classmethod
    def load(cls, path):
        with open(path) as file:
            state = json.load(file)
        craft_cls = ExplorerCraft if state["craft_type"] == "ExplorerCraft" else DefenderCraft
        craft = craft_cls(state["craft_name"], state["location"])
        craft.max_health = state["max_health"]
        craft.health = state["health"]
        craft.fuel = state["fuel"]
        craft.oxygen = state["oxygen"]
        craft.energy = state["energy"]
        craft.cargo_capacity = state["cargo_capacity"]
        craft.cargo = state["cargo"]
        craft.discovered = set(state["discovered"])
        game = cls(craft, seed=0, turn_limit=state["turn_limit"])
        game.turn = state["turn"]
        game.won = state.get("won", False)
        game.lost = state.get("lost", False)
        seed_state = state["seed_state"]
        game.rng.setstate((seed_state[0], tuple(seed_state[1]), seed_state[2]))
        for mission_state in state["missions"]:
            for mission in game.missions:
                if mission.mission_id == mission_state["id"]:
                    mission.accepted = mission_state["accepted"]
                    mission.completed = mission_state["completed"]
        return game