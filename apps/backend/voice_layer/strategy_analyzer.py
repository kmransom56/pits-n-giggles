# MIT License

"""F1 Race strategy analyzer for intelligent voice responses."""

import logging
from typing import Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StrategyAdvice:
    """Strategic recommendation based on current race state."""

    priority: str  # "critical", "warning", "info"
    category: str  # "pit_window", "tyre_management", "fuel", "pace", "strategy"
    advice: str  # Human-readable recommendation
    reasoning: str  # Why this advice is given
    data_point: Optional[str] = None  # Relevant stat (e.g., "45% wear")


class RaceStrategyAnalyzer:
    """Analyzes race state and generates strategic advice for voice responses."""

    # Tyre wear thresholds (%)
    TYRE_CRITICAL_WEAR = 90
    TYRE_HIGH_WEAR = 70
    TYRE_MEDIUM_WEAR = 50

    # Fuel thresholds
    FUEL_CRITICAL_LAPS = 1.5
    FUEL_WARNING_LAPS = 2.5
    FUEL_SAFE_LAPS = 3.5

    # Pace analysis thresholds
    GAP_CLOSING_THRESHOLD = 0.3  # seconds per lap
    GAP_EXTENDING_THRESHOLD = 0.3

    @staticmethod
    def analyze_tyre_wear(tyre_data: dict) -> Optional[StrategyAdvice]:
        """Analyze tyre wear and recommend pit window."""
        if not tyre_data or "wear" not in tyre_data:
            return None

        wear_values = tyre_data.get("wear", [])
        if not wear_values:
            return None

        avg_wear = sum(wear_values) / len(wear_values)
        max_wear = max(wear_values)

        if max_wear >= RaceStrategyAnalyzer.TYRE_CRITICAL_WEAR:
            return StrategyAdvice(
                priority="critical",
                category="pit_window",
                advice="Pit immediately — tyres critically worn",
                reasoning=f"Maximum tyre wear at {max_wear:.0f}% — risk of failure",
                data_point=f"{max_wear:.0f}% wear",
            )

        if avg_wear >= RaceStrategyAnalyzer.TYRE_HIGH_WEAR:
            return StrategyAdvice(
                priority="warning",
                category="pit_window",
                advice="Plan pit stop soon — tyres wearing quickly",
                reasoning=f"Average wear {avg_wear:.0f}% — approaching degradation cliff",
                data_point=f"{avg_wear:.0f}% avg wear",
            )

        # Check for uneven wear (setup issue?)
        wear_variance = max_wear - min(wear_values)
        if wear_variance > 15:
            return StrategyAdvice(
                priority="warning",
                category="tyre_management",
                advice=f"Uneven tyre wear detected — check setup",
                reasoning=f"Front/rear wear variance {wear_variance:.0f}% suggests brake balance or wing angle issue",
                data_point=f"{wear_variance:.0f}% variance",
            )

        return None

    @staticmethod
    def analyze_fuel(fuel_data: dict, lap_number: int = 0) -> Optional[StrategyAdvice]:
        """Analyze fuel and recommend pit timing."""
        if not fuel_data or "remaining_laps" not in fuel_data:
            return None

        remaining_laps = fuel_data.get("remaining_laps", 0)
        burn_rate = fuel_data.get("burn_rate", 0)

        if remaining_laps <= RaceStrategyAnalyzer.FUEL_CRITICAL_LAPS:
            return StrategyAdvice(
                priority="critical",
                category="fuel",
                advice="Pit for fuel immediately",
                reasoning=f"Only {remaining_laps:.1f} laps of fuel remaining",
                data_point=f"{remaining_laps:.1f} laps",
            )

        if remaining_laps <= RaceStrategyAnalyzer.FUEL_WARNING_LAPS:
            return StrategyAdvice(
                priority="warning",
                category="fuel",
                advice="Pit soon for fuel — plan pit window",
                reasoning=f"{remaining_laps:.1f} laps remaining at {burn_rate:.2f}kg/lap",
                data_point=f"{remaining_laps:.1f} laps left",
            )

        return None

    @staticmethod
    def analyze_pace(standings_data: dict, player_data: dict) -> Optional[StrategyAdvice]:
        """Analyze pace relative to leaders."""
        if not standings_data or "standings" not in standings_data:
            return None

        standings = standings_data.get("standings", [])
        if not standings or len(standings) < 2:
            return None

        # Get player position
        player_pos = player_data.get("position", 0)
        player_gap = standings[0].get("gap_to_leader", 0) if player_pos == 1 else 0

        if player_pos > 1 and len(standings) > player_pos - 1:
            gap_to_leader = standings[player_pos - 1].get("gap_to_leader", 0)

            if gap_to_leader < 0.5:
                return StrategyAdvice(
                    priority="info",
                    category="pace",
                    advice="You're on pace with the leader — maintain current strategy",
                    reasoning=f"Gap of {gap_to_leader:.2f}s is competitive",
                    data_point=f"{gap_to_leader:.2f}s gap",
                )

            if gap_to_leader > 3.0:
                return StrategyAdvice(
                    priority="warning",
                    category="pace",
                    advice="Leader is pulling away — review strategy or push harder",
                    reasoning=f"Gap has grown to {gap_to_leader:.2f}s",
                    data_point=f"{gap_to_leader:.2f}s behind",
                )

        if player_pos == 1:
            if len(standings) > 1:
                gap_to_p2 = standings[1].get("gap_to_leader", 0)
                if gap_to_p2 < 2.0:
                    return StrategyAdvice(
                        priority="warning",
                        category="pace",
                        advice="P2 is closing in — be careful on errors",
                        reasoning=f"Gap to second place only {gap_to_p2:.2f}s",
                        data_point=f"+{gap_to_p2:.2f}s lead",
                    )

        return None

    @staticmethod
    def analyze_damage(damage_data: dict) -> Optional[StrategyAdvice]:
        """Analyze car damage and recommend action."""
        if not damage_data:
            return None

        wing_damage = damage_data.get("wing_damage")
        engine_damage = damage_data.get("engine_damage")
        brake_damage = damage_data.get("brake_damage")

        if engine_damage and engine_damage > 50:
            return StrategyAdvice(
                priority="critical",
                category="strategy",
                advice="Serious engine damage — pit for inspection",
                reasoning=f"Engine damage at {engine_damage}% — risk of failure",
                data_point=f"{engine_damage}% engine damage",
            )

        if wing_damage:
            return StrategyAdvice(
                priority="warning",
                category="strategy",
                advice="Wing damage detected — performance impacted",
                reasoning="Aerodynamic damage will increase drag and reduce downforce",
                data_point="Wing damage",
            )

        return None

    @staticmethod
    def generate_context_summary(session_state_dict: dict) -> str:
        """Generate a summary of current race context for LLM."""
        lines = []

        # Session info
        if "session_info" in session_state_dict:
            info = session_state_dict["session_info"]
            lines.append(f"Session: {info.get('session_type')} at {info.get('circuit')}")
            lines.append(
                f"Conditions: {info.get('weather')} (Track {info.get('track_temp')}°C, Air {info.get('air_temp')}°C)"
            )

        # Player position
        if "player_driver_info" in session_state_dict:
            player = session_state_dict["player_driver_info"]
            lines.append(f"You: P{player.get('position')} ({player.get('name')} - {player.get('team')})")

        # Critical stats
        if "tyre_wear" in session_state_dict:
            tyre = session_state_dict["tyre_wear"]
            if tyre.get("wear"):
                avg = sum(tyre["wear"]) / len(tyre["wear"])
                lines.append(f"Tyre wear: {avg:.0f}% avg ({tyre.get('compound')})")

        if "fuel_info" in session_state_dict:
            fuel = session_state_dict["fuel_info"]
            lines.append(f"Fuel: {fuel.get('remaining_laps'):.1f} laps ({fuel.get('remaining_kg'):.1f}kg)")

        return "\n".join(lines)
