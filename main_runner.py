"""
main_runner.py — Solo llama y inicializa todo. Sin lógica controlable.
El entorno vive toda la lógica; el agente percibe/actúa; el renderer solo dibuja.
"""

import sys
import threading
import time
from runnerworld import RunnerChaseEnvironment
from runneragents import CriminalAgent, PlayerAgent, CaptorAgent
from runnerbuffer import RunnerStateBuffer
from runnerrenderers import PyGameRunnerRenderer, ConsoleRunnerRenderer
from Runnerstats import record_result, print_stats, reset_stats
print_lock = threading.Lock()  # candado global
# ---------------------------------------------------------------------------
# Flags de sincronización
# ---------------------------------------------------------------------------
game_finished      = False
event_render_ready = threading.Event()

# ---------------------------------------------------------------------------
# Hilo genérico del agente — solo perceive -> function -> act
# ---------------------------------------------------------------------------
def agent_thread(agent, env=None, max_turns: int = 500):
    global game_finished
    for _ in range(max_turns):
        if game_finished:
            break
        # Criminal fijo 1.0s (fila 6), mistake_rate sigue subiendo por tiempo en get_mistake_rate_for_tick
        # Player solo actúa si tiene pending (no spam de "run")
        is_player = hasattr(agent, "has_pending_action")
        if is_player and not agent.has_pending_action():
            time.sleep(0.05)
            continue
        #delay = 0.2 if not is_player else 0.1 #Delay no depende del tipo de player, debe ser un valor chico para que agente sea libre de hacer las acciones que quiera, solo penalizar por el choque con obstaculo, 
        # --------Delay nuevo--------
        delay = 0.05  # antes 0.2/0.1, ahora único 0.05s para que agente sea libre, solo penalizar por choque
        # --------Delay nuevo--------
        event_render_ready.wait(timeout=delay)
        agent.behave()
        event_render_ready.clear()
        time.sleep(delay)
    game_finished = True

def render_thread(renderer):
    while not game_finished:
        with print_lock:
            renderer.render()
        event_render_ready.set()
        time.sleep(0.2)

# ---------------------------------------------------------------------------
# Hilo de input consola — TEMPORAL, próximo paso mover al entorno
# Hoy lo saque del renderer (C) y pero lo dejo acá para no romper.
# TODO(A completo): mover key_map y validación a RunnerChaseEnvironment
# ---------------------------------------------------------------------------
def input_thread_console(player: PlayerAgent):
    global game_finished
    import queue
    key_map = {
        "":  "run",
        "w": "jump",
        "s": "slide",
        "a": "go_left",
        "d": "go_right",
    }
    def _input_with_timeout(prompt, timeout):
        q = queue.Queue()
        def _w():
            try:
                q.put(input(prompt))
            except Exception:
                q.put(None)
        t = threading.Thread(target=_w, daemon=True)
        t.start()
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    while not game_finished:
        with print_lock:
            raw = _input_with_timeout("Acción [W|A|S|D] (2s): ", 2.0)
        if raw is None:
            if game_finished:
                break
            print("  ⏰ Tiempo! El escenario avanza (+3)")
            player._actuators["runner"].act(None)
            continue
        try:
            key = raw.strip().lower()
        except Exception:
            continue
        if key == "q":
            print("Saliendo...")
            game_finished = True
            break
        player.set_action(key_map.get(key, None))

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
            player.set_action(None)
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
    player   = CaptorAgent(env, base_mistake_rate=0.10)  # PlayerAgent(env)

    # Buffers — solo guardan lo visible (B)
    buf_c = RunnerStateBuffer(criminal.id, env)
    buf_p = RunnerStateBuffer(player.id,   env)

    if use_console:
        renderer = ConsoleRunnerRenderer()
        renderer.observe(buf_p)#Un unico estado (state en environment) permite que distintos statebuffer muestren la misma realidad.

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
        record_result(env._winner)  # player->atrapadas, criminal->escapes
        print_stats()

    criminal.print_state()
    player.print_state()
    print("\nPartida finalizada.")
#a medida de que el player se mueva su tiempo de limite tambien sera mas corto