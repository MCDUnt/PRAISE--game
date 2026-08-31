"""
main_runner.py — Modo local del juego Runner Chase
Solo orquesta. Sin lógica controlable (feedback profesor).
El entorno decide; el agente percibe/actúa; el renderer solo dibuja.
"""

import sys
import threading
import time
from runnerworld import RunnerChaseEnvironment
from runneragents import CriminalAgent, PlayerAgent
from runnerbuffer import RunnerStateBuffer
from runnerrenderers import PyGameRunnerRenderer, ConsoleRunnerRenderer
from Runnerstats import record_result, print_stats, reset_stats

# ---------------------------------------------------------------------------
# Flags de sincronización
# ---------------------------------------------------------------------------
game_finished      = False
event_render_ready = threading.Event()

# ---------------------------------------------------------------------------
# Hilo genérico del agente — solo perceive -> function -> act
# Igual que Vacuum_version/main.py:11
# ---------------------------------------------------------------------------
def agent_thread(agent, env=None, max_turns: int = 500):
    global game_finished
    for _ in range(max_turns):
        if game_finished:
            break
        delay = env._current_delay if env is not None and hasattr(env, "_current_delay") else 0.1
        event_render_ready.wait(timeout=delay)
        agent.behave()
        event_render_ready.clear()
        time.sleep(delay)
    game_finished = True

# ---------------------------------------------------------------------------
# Hilo genérico del renderer — solo dibuja (sin lógica)
# Igual que Vacuum_version/main.py:20
# ---------------------------------------------------------------------------
def render_thread(renderer):
    while not game_finished:
        renderer.render()
        event_render_ready.set()
        time.sleep(0.05)

# ---------------------------------------------------------------------------
# Hilo de input consola — TEMPORAL, próximo paso mover al entorno
# Hoy lo sacamos del renderer (C) y lo dejamos acá para no romper.
# TODO(A completo): mover key_map y validación a RunnerChaseEnvironment
# ---------------------------------------------------------------------------
def input_thread_console(player: PlayerAgent):
    global game_finished
    key_map = {
        "":  "run",
        "w": "jump",
        "s": "slide",
        "a": "go_left",
        "d": "go_right",
    }
    while not game_finished:
        try:
            key = input("Acción [ENTER=correr | w=saltar | s=deslizar | a=izq | d=der | q=salir]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            game_finished = True
            break
        if key == "q":
            print("Saliendo...")
            game_finished = True
            break
        player.set_action(key_map.get(key, "run"))

# ---------------------------------------------------------------------------
# Hilo de input PyGame — también temporal, sale del renderer
# ---------------------------------------------------------------------------
def input_thread_pygame(player: PlayerAgent):
    global game_finished
    import pygame
    while not game_finished:
        try:
            keys = pygame.key.get_pressed()
        except Exception:
            time.sleep(0.05)
            continue
        if keys[pygame.K_w]:
            player.set_action("jump")
        elif keys[pygame.K_s]:
            player.set_action("slide")
        elif keys[pygame.K_a]:
            player.set_action("go_left")
        elif keys[pygame.K_d]:
            player.set_action("go_right")
        elif keys[pygame.K_RETURN]:
            player.set_action("run")
        time.sleep(0.05)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    if "--reset" in sys.argv:
        reset_stats()
        print_stats()
        sys.exit(0)

    if "--stats" in sys.argv:
        print_stats()
        sys.exit(0)

    use_console = "--console" in sys.argv

    # Fix encoding Windows cp1252
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 55)
    print("  RUNNER CHASE")
    print("  Modo:", "Consola" if use_console else "PyGame")
    print("=" * 55)
    print_stats()

    # Crear entorno y agentes
    env      = RunnerChaseEnvironment()
    criminal = CriminalAgent(env, base_mistake_rate=0.15)
    player   = PlayerAgent(env)

    # Buffers — solo guardan lo visible (B)
    buf_c = RunnerStateBuffer(criminal.id, env)
    buf_p = RunnerStateBuffer(player.id,   env)

    if use_console:
        renderer = ConsoleRunnerRenderer()
        renderer.observe(buf_p)

        t_criminal = threading.Thread(target=agent_thread, args=(criminal, env), daemon=True)
        t_player   = threading.Thread(target=agent_thread, args=(player, env), daemon=True)
        t_renderer = threading.Thread(target=render_thread, args=(renderer,), daemon=True)
        t_input    = threading.Thread(target=input_thread_console, args=(player,), daemon=True)

        t_criminal.start()
        t_player.start()
        t_renderer.start()
        t_input.start()

        t_criminal.join(timeout=15)
        t_player.join(timeout=15)

    else:
        renderer = PyGameRunnerRenderer()
        renderer.observe(buf_p)

        t_criminal = threading.Thread(target=agent_thread, args=(criminal, env), daemon=True)
        t_player   = threading.Thread(target=agent_thread, args=(player, env), daemon=True)
        t_input    = threading.Thread(target=input_thread_pygame, args=(player,), daemon=True)

        t_criminal.start()
        t_player.start()
        t_input.start()

        # El renderer corre en el hilo principal (PyGame lo requiere)
        render_thread(renderer)

    game_finished = True

    if env._winner:
        record_result(env._winner)
        print_stats()

    criminal.print_state()
    player.print_state()
    print("\nPartida finalizada.")
