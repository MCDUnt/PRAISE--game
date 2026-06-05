"""
Guarda estadísticas en stats.json entre sesiones.
Para resetear: correr con reset_stats() o borrar stats.json manualmente.
"""

import json
import os

STATS_FILE = "stats.json"


def load_stats() -> dict:
    """Carga las estadísticas del archivo, pero si no existe estadisticas cargadas, las arranca desde cero.
    if os.path.exists(STATS_FILE):"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {"atrapadas": 0, "escapes": 0, "partidas": 0}


def save_stats(stats: dict) -> None:
    """Guarda las estadísticas en el archivo."""
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def record_result(winner: str) -> dict:
    """
    Registra el resultado de una partida.
    winner: "player" → atrapada | "criminal" → escape
    Devuelve las estadísticas actualizadas.
    """
    stats = load_stats()
    stats["partidas"] += 1
    if winner == "player":
        stats["atrapadas"] += 1
    elif winner == "criminal":
        stats["escapes"] += 1
    save_stats(stats)
    return stats


def reset_stats() -> None:
    """Resetea todas las estadísticas a cero."""
    save_stats({"atrapadas": 0, "escapes": 0, "partidas": 0})
    print("[Stats] Contador reseteado.")


def print_stats() -> None:
    """Imprime las estadísticas actuales."""
    stats = load_stats()
    print("\n" + "═" * 35)
    print("  📊  ESTADÍSTICAS GLOBALES")
    print(f"  Partidas jugadas : {stats['partidas']}")
    print(f"  🏆  Atrapadas    : {stats['atrapadas']}")
    print(f"  💀  Escapes      : {stats['escapes']}")
    if stats["partidas"] > 0:
        pct = (stats["atrapadas"] / stats["partidas"]) * 100
        print(f"  Win rate         : {pct:.1f}%")
    print("═" * 35)