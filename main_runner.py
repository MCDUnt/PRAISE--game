"""
main_runner.py — Modo local del juego Runner Chase

Uso:
  python main_runner.py           → jugar
  python main_runner.py --reset   → resetear estadísticas
  python main_runner.py --stats   → ver estadísticas sin jugar
"""

import sys
import threading
import time
from runnerworld import RunnerChaseEnvironment, SPEED_INITIAL_DELAY
from runneragents import CriminalAgent, PlayerAgent
from runnerbuffer import RunnerStateBuffer
from runnerrenderers import PyGameRunnerRenderer, NullRunnerRenderer
from runnerstats import record_result, print_stats, reset_stats


# ---------------------Flags de sincronización---------------------

game_finished      = False
event_render_ready = threading.Event()


# ---------------------Hilo del agente DELINCUENTE (IA)---------------------

def criminal_thread(agent: CriminalAgent, env: RunnerChaseEnvironment, max_turns: int = 500):
    global game_finished
    for _ in range(max_turns):
        if game_finished:
            break
        event_render_ready.wait(timeout=env._current_delay)
        agent.behave()
        event_render_ready.clear()
        time.sleep(env._current_delay)
    game_finished = True



# ---------------------Hilo del agente JUGADOR (humano)---------------------

def player_thread(agent: PlayerAgent, max_turns: int = 500):
    global game_finished
    key_map = {
        "":  "run",
        "w": "jump",
        "s": "slide",
        "a": "go_left",
        "d": "go_right",
    }
    for _ in range(max_turns):
        if game_finished:
            break
        try:
            key = input("Acción [ENTER=correr | w=saltar | s=deslizar | a=izq | d=der | q=salir]: ").strip().lower()
        except EOFError:
            break
        if key == "q":
            print("Saliendo...")
            game_finished = True
            break
        action = key_map.get(key, "run")
        agent.set_action(action)
        agent.behave()
    game_finished = True



# ---------------------Hilo del renderer---------------------
def pygame_render_thread(renderer: PyGameRunnerRenderer,agent: PlayerAgent, max_turns: int = 500):
    global game_finished
    for _ in range(max_turns):
        if game_finished:
            break
        renderer.render()
        agent.behave()
        event_render_ready.set()
    game_finished = True

#---------------------Renderizado en consola---------------------
def console_render_thread(renderer_criminal, renderer_player):
    while not game_finished:
        renderer_criminal.render()
        renderer_player.render()
        event_render_ready.set()


# --------------------Entry point-------------------------

if __name__ == "__main__":

    # Comandos especiales
    if "--reset" in sys.argv:
        reset_stats()
        print_stats()
        sys.exit(0)

    if "--stats" in sys.argv:
        print_stats()
        sys.exit(0)

    use_console = "--console" in sys.argv

    print("=" * 55)
    print("  RUNNER CHASE — Modo Local")
    print(" Modo:", "Consola" if use_console else "PyGame")
    print("=" * 55)
    print_stats()

    # Crear entorno y agentes
    env     = RunnerChaseEnvironment()
    criminal = CriminalAgent(env, base_mistake_rate=0.15)
    player   = PlayerAgent(env)

    # Buffers y renderers
    buf_c = RunnerStateBuffer(criminal.id, env)
    buf_p = RunnerStateBuffer(player.id,   env)
    if use_console:
        rend_c = NullRunnerRenderer()
        rend_p = NullRunnerRenderer()
        rend_c.observe(buf_c)
        rend_p.observe(buf_p)
    # Lanzar hilos
        t_criminal = threading.Thread(target=criminal_thread, args=(criminal, env), daemon=True)
        t_renderer = threading.Thread(target=render_thread,   args=(rend_c, rend_p), daemon=True)
        t_criminal.start()
        t_renderer.start()
        player_thread_console(player)
    else:
        renderer = PyGameRunnerRenderer(player_agent=player)
        renderer.observe(buf_p)

        t_criminal = threading.Thread(target=criminal_thread, args=(criminal, env), daemon=True)
        t_criminal.start()
        pygame_render_thread(renderer, player)
    t_criminal.join(timeout=2)
    

    # Registrar resultado
    if env._winner:
        stats = record_result(env._winner)
        print(f"\n  Resultado registrado.")
        print_stats()

    criminal.print_state()
    player.print_state()
    print("\nPartida finalizada.")