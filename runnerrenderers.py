"""
PyGameRunnerRenderer — Renderer visual para Runner Chase
Solo dibuja. No captura input ni conoce al agente.
La grilla viene del entorno vía StateBuffer (igual que Vacuum).
"""

import pygame
from renderers import IRenderer

# ---------------------------------------------------------------------------
# Colores
# ---------------------------------------------------------------------------
COLOR_BG         = (30, 30, 30)
COLOR_TRACK      = (80, 80, 80)
COLOR_CRIMINAL   = (220, 60, 60)
COLOR_PLAYER     = (60, 180, 220)
COLOR_OBSTACLE   = (200, 140, 40)
COLOR_TEXT       = (240, 240, 240)
COLOR_WIN        = (80, 200, 80)
COLOR_LOSE       = (200, 60, 60)

# ---------------------------------------------------------------------------
# Dimensiones
# ---------------------------------------------------------------------------
SCREEN_W         = 900
SCREEN_H         = 400
TRACK_Y          = 200
TRACK_H          = 60
AGENT_W          = 40
AGENT_H          = 60
OBSTACLE_W       = 30
OBSTACLE_H       = 40
FPS              = 60

CRIMINAL_X       = 600
PLAYER_X         = 200


class PyGameRunnerRenderer(IRenderer):
    """
    Lee la info del buffer y dibuja. Sin lógica de input.
    El input vive en el entorno/agente (feedback profesor).
    """

    def __init__(self):
        pygame.init()
        self._screen       = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Runner Chase")
        self._clock        = pygame.time.Clock()
        self._font         = pygame.font.SysFont("monospace", 18)
        self._font_big     = pygame.font.SysFont("monospace", 28, bold=True)
        self._statebuffer  = None
        self._running      = True
        self.array         = []  # grilla preparada para dibujar (como Vacuum)

    # ------------------------------------------------------------------
    # IRenderer interface
    # ------------------------------------------------------------------

    def observe(self, statebuffer) -> None:
        self._statebuffer = statebuffer

    def render(self) -> None:
        if not self._running:
            return

        # 1. Eventos del sistema (solo cerrar ventana)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                pygame.quit()
                return

        # 2. Leer estado del buffer (siempre el último, sin consumir)
        state = None
        if self._statebuffer:
            state = self._statebuffer.get_state()

        # 3. Limpiar pantalla
        self._screen.fill(COLOR_BG)

        # 4. Dibujar
        if state:
            self._prepare_data(state)
            self._draw_track()
            self._draw_agents(state)
            self._draw_hud(state)
            if state.get("game_over"):
                self._draw_game_over(state)

        # 5. Mostrar frame
        pygame.display.flip()
        self._clock.tick(FPS)

    # ------------------------------------------------------------------
    # Preparación de datos — transforma grid/state en array dibujable
    # (igual que Vacuum PyGameRenderer._prepare_data)
    # ------------------------------------------------------------------

    def _prepare_data(self, state: dict) -> None:
        """
        Convierte el estado del entorno en self.array.
        Si el entorno ya manda 'grid', lo usa directo.
        Si no (compatibilidad con runnerworld viejo), lo construye
        desde next_obstacle/role para no romper antes del refactor A.
        """
        grid = state.get("grid")
        if grid is not None:
            self.array = grid
            return

        # Fallback legacy: construir grilla mínima desde estado viejo
        # Fila 0: upcoming_track, Fila 1: posiciones relativas
        upcoming = state.get("upcoming_track", [])
        obstacle = state.get("next_obstacle", "none")
        role = state.get("role", "")
        # grid simple 2xN para debug visual
        self.array = [upcoming, [role, obstacle]]

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def _draw_track(self) -> None:
        pygame.draw.rect(
            self._screen, COLOR_TRACK,
            (0, TRACK_Y, SCREEN_W, TRACK_H)
        )

    def _draw_agents(self, s: dict) -> None:
        role = s.get("role", "")

        pygame.draw.rect(
            self._screen, COLOR_PLAYER,
            (PLAYER_X, TRACK_Y - AGENT_H, AGENT_W, AGENT_H)
        )
        label_p = self._font.render("CAPTOR", True, COLOR_TEXT)
        self._screen.blit(label_p, (PLAYER_X, TRACK_Y - AGENT_H - 20))

        pygame.draw.rect(
            self._screen, COLOR_CRIMINAL,
            (CRIMINAL_X, TRACK_Y - AGENT_H, AGENT_W, AGENT_H)
        )
        label_c = self._font.render("FUGITIVO", True, COLOR_TEXT)
        self._screen.blit(label_c, (CRIMINAL_X, TRACK_Y - AGENT_H - 20))

        obstacle = s.get("next_obstacle", "none")
        if obstacle != "none":
            obs_x = PLAYER_X + AGENT_W + 20 if role == "player" else CRIMINAL_X + AGENT_W + 20
            pygame.draw.rect(
                self._screen, COLOR_OBSTACLE,
                (obs_x, TRACK_Y - OBSTACLE_H, OBSTACLE_W, OBSTACLE_H)
            )
            obs_label = self._font.render(obstacle, True, COLOR_TEXT)
            self._screen.blit(obs_label, (obs_x, TRACK_Y - OBSTACLE_H - 20))

    def _draw_hud(self, s: dict) -> None:
        distance    = s.get("distance", 0)
        errors_self = s.get("errors_self", 0)
        errors_opp  = s.get("errors_opponent", 0)
        obstacle    = s.get("next_obstacle", "none")
        last_action = s.get("last_action", "-")
        last_ok     = s.get("last_correct", True)
        tick        = s.get("tick", 0)
        mistake     = s.get("mistake_rate", 0.0)

        result_icon = "OK" if last_ok else "ERROR"

        lines = [
            f"Distancia:     {distance} casillas",
            f"Errores propios: {errors_self}  |  Errores rival: {errors_opp}",
            f"Obstáculo:     {obstacle}",
            f"Última acción: {last_action} [{result_icon}]",
            f"Tick: {tick}  |  Dificultad IA: {mistake:.0%}",
            "",
            "W=saltar  S=deslizar  A=izq  D=der  ENTER=correr",
        ]

        y = 20
        for line in lines:
            surf = self._font.render(line, True, COLOR_TEXT)
            self._screen.blit(surf, (20, y))
            y += 24

    def _draw_game_over(self, s: dict) -> None:
        winner = s.get("winner")
        if winner == "player":
            msg   = "CAPTOR GANO"
            color = COLOR_WIN
        else:
            msg   = "FUGITIVO ESCAPO"
            color = COLOR_LOSE

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._screen.blit(overlay, (0, 0))

        text = self._font_big.render(msg, True, color)
        rect = text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
        self._screen.blit(text, rect)

        sub = self._font.render("Cerrá la ventana para salir", True, COLOR_TEXT)
        sub_rect = sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 40))
        self._screen.blit(sub, sub_rect)


class ConsoleRunnerRenderer(IRenderer):
    """
    Renderer de consola — solo imprime la grilla que viene del entorno.
    Paridad con Vacuum_version/vacuumrenderers.py ConsoleRenderer.
    Sin lógica.
    """

    def __init__(self):
        self._statebuffer = None

    def observe(self, statebuffer) -> None:
        self._statebuffer = statebuffer

    def render(self) -> None:
        state = None
        if self._statebuffer:
            state = self._statebuffer.get_state()
        if not state:
            return

        grid = state.get("grid")
        if grid is not None:
            for fila in grid:
                print(" | ".join(str(c) for c in fila))
        else:
            # Fallback legacy
            print(f"[Console] dist={state.get('distance')} obs={state.get('next_obstacle')} "
                  f"role={state.get('role')} over={state.get('game_over')}")

        if state.get("game_over"):
            print(f"*** Ganó: {state.get('winner')} ***")


class NullRunnerRenderer(IRenderer):
    """Renderer headless para tests."""
    def observe(self, statebuffer) -> None:
        pass
    def render(self) -> None:
        pass
