#pip install pygame
"""
PyGameRunnerRenderer — Renderer visual simple para Runner Chase
Versión inicial: ventana, pista, agentes como rectángulos, HUD básico
para probar funsionamiento del pygame y la comunicación con el PlayerAgent.
"""

import pygame
from renderers import IRenderer

# ---------------------------------------------------------------------------
# Colores
# ---------------------------------------------------------------------------
COLOR_BG         = (30, 30, 30)      # fondo oscuro
COLOR_TRACK      = (80, 80, 80)      # pista
COLOR_CRIMINAL   = (220, 60, 60)     # fugitivo — rojo
COLOR_PLAYER     = (60, 180, 220)    # captor — azul
COLOR_OBSTACLE   = (200, 140, 40)    # obstáculo — naranja
COLOR_TEXT       = (240, 240, 240)   # texto blanco
COLOR_WIN        = (80, 200, 80)     # verde victoria
COLOR_LOSE       = (200, 60, 60)     # rojo derrota

# ---------------------------------------------------------------------------
# Dimensiones
# ---------------------------------------------------------------------------
SCREEN_W         = 900
SCREEN_H         = 400
TRACK_Y          = 200    # altura de la pista en pantalla
TRACK_H          = 60     # grosor visual de la pista
AGENT_W          = 40
AGENT_H          = 60
OBSTACLE_W       = 30
OBSTACLE_H       = 40
FPS              = 60

# Posiciones fijas en pantalla (la pista hace scroll, los agentes no se mueven en X)
CRIMINAL_X       = 600    # fugitivo aparece más a la derecha
PLAYER_X         = 200    # captor aparece más a la izquierda


class PyGameRunnerRenderer(IRenderer):
    """
    Renderer visual con PyGame para Runner Chase.
    Lee el buffer y dibuja el estado en cada frame.
    Las teclas W/S/A/D/ENTER se capturan acá y se mandan al PlayerAgent.
    """

    def __init__(self, player_agent=None):
        pygame.init()
        self._screen       = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Runner Chase")
        self._clock        = pygame.time.Clock()
        self._font         = pygame.font.SysFont("monospace", 18)
        self._font_big     = pygame.font.SysFont("monospace", 28, bold=True)
        self._statebuffer  = None
        self._player_agent = player_agent   # referencia al PlayerAgent para mandar teclas
        self._running      = True

    # ------------------------------------------------------------------
    # IRenderer interface
    # ------------------------------------------------------------------

    def observe(self, statebuffer) -> None:
        self._statebuffer = statebuffer

    def render(self) -> None:
        if not self._running:
            return

        # 1. Capturar eventos del sistema (cerrar ventana, teclas)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                pygame.quit()
                return

        # 2. Capturar teclas y mandarlas al agente
        self._handle_keys()

        # 3. Leer estado del buffer
        state = None
        if self._statebuffer:
            state = self._statebuffer.get_state()

        # 4. Limpiar pantalla
        self._screen.fill(COLOR_BG)

        # 5. Dibujar
        if state:
            self._draw_track()
            self._draw_agents(state)
            self._draw_hud(state)
            if state.get("game_over"):
                self._draw_game_over(state)

        # 6. Mostrar frame
        pygame.display.flip()
        self._clock.tick(FPS)

    # ------------------------------------------------------------------
    # Input del jugador
    # ------------------------------------------------------------------

    def _handle_keys(self) -> None:
        if self._player_agent is None:
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            self._player_agent.set_action("jump")
        elif keys[pygame.K_s]:
            self._player_agent.set_action("slide")
        elif keys[pygame.K_a]:
            self._player_agent.set_action("go_left")
        elif keys[pygame.K_d]:
            self._player_agent.set_action("go_right")
        elif keys[pygame.K_RETURN]:
            self._player_agent.set_action("run")

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def _draw_track(self) -> None:
        """Dibuja la pista como una barra horizontal."""
        pygame.draw.rect(
            self._screen, COLOR_TRACK,
            (0, TRACK_Y, SCREEN_W, TRACK_H)
        )

    def _draw_agents(self, s: dict) -> None:
        """Dibuja los dos agentes como rectángulos sobre la pista."""
        role = s.get("role", "")

        # Captor — azul, abajo a la izquierda
        pygame.draw.rect(
            self._screen, COLOR_PLAYER,
            (PLAYER_X, TRACK_Y - AGENT_H, AGENT_W, AGENT_H)
        )
        label_p = self._font.render("CAPTOR", True, COLOR_TEXT)
        self._screen.blit(label_p, (PLAYER_X, TRACK_Y - AGENT_H - 20))

        # Fugitivo — rojo, más a la derecha según distancia
        pygame.draw.rect(
            self._screen, COLOR_CRIMINAL,
            (CRIMINAL_X, TRACK_Y - AGENT_H, AGENT_W, AGENT_H)
        )
        label_c = self._font.render("FUGITIVO", True, COLOR_TEXT)
        self._screen.blit(label_c, (CRIMINAL_X, TRACK_Y - AGENT_H - 20))

        # Obstáculo delante del agente activo
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
        """Dibuja el HUD: distancia, errores, obstáculo, última acción."""
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
        """Pantalla de fin de partida."""
        winner = s.get("winner")
        if winner == "player":
            msg   = "CAPTOR GANO"
            color = COLOR_WIN
        else:
            msg   = "FUGITIVO ESCAPO"
            color = COLOR_LOSE

        # Fondo semitransparente
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._screen.blit(overlay, (0, 0))

        # Texto central
        text = self._font_big.render(msg, True, color)
        rect = text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
        self._screen.blit(text, rect)

        sub = self._font.render("Cerrá la ventana para salir", True, COLOR_TEXT)
        sub_rect = sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 40))
        self._screen.blit(sub, sub_rect)


class NullRunnerRenderer(IRenderer):
    """Renderer headless para tests."""
    def observe(self, statebuffer) -> None:
        pass
    def render(self) -> None:
        pass