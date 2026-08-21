import os, random, re
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import database
from resources import Resources, COLORS, FONTS
from auth_ui import AuthUI

from mixin_dashboard import MixinDashboard
from mixin_estudiantes import MixinEstudiantes
from mixin_estudiantes_dlg import MixinEstudiantesDlg
from mixin_profesores import MixinProfesores
from mixin_notas import MixinNotas
from mixin_notas_dlg import MixinNotasDlg
from mixin_horarios import MixinHorarios
from mixin_constancias import MixinConstancias
from mixin_perfil import MixinPerfil
from mixin_configuracion import MixinConfiguracion
from mixin_estadistica import MixinEstadistica

class AplicacionEscolar(MixinDashboard, MixinEstudiantes, MixinEstudiantesDlg, 
                        MixinProfesores, MixinNotas, MixinNotasDlg, 
                        MixinHorarios, MixinConstancias, MixinPerfil, MixinConfiguracion, MixinEstadistica):
    def __init__(self, root):
        self.root = root
        self.root.title("Nexus")
        self.root.state('zoomed')
        self.VERSION = "8.9.6"
        self.res = Resources()
        # Configurar icono de la ventana (Usar Nexus para iconos de ventana)
        icon_img = self.res.get_image("logo_nexus", (64, 64))
        if icon_img:
            self.root.iconphoto(True, icon_img)
        self._side_imgs = []
        self._dlg_imgs = []
        self.is_pro = False  # Estado de la versión PRO
        database.conectar()
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.cc_ids = []
        self.cc_wgts = []
        
        # Variables para controlar la navegación
        self.ultimos_resultados = []  # Guardar últimos resultados de búsqueda
        self.modo_actual = "dashboard"  # dashboard, resultados, detalle

        # Variables persistentes para filtros y búsqueda (para poder limpiarlas centralmente)
        self._filtro_nivel     = tk.StringVar(value="")
        self._filtro_grado     = tk.StringVar(value="")
        self._filtro_seccion   = tk.StringVar(value="")
        self._busqueda_estudiantes = tk.StringVar(value="")
        
        # Definición de grados por nivel
        self._grados_media    = ["1er Año", "2do Año", "3er Año", "4to Año", "5to Año"]
        self._grados_primaria = ["1er Grado", "2do Grado", "3er Grado", "4to Grado", "5to Grado", "6to Grado"]

        self.auth = AuthUI(self)
        
        # Iniciar siempre desde la pantalla de carga
        self.usuario_actual = None
        self.sistema_bloqueado = False
        self.pantalla_carga()

    def limpiar_pantalla(self):
        self.canvas.delete("all")
        for widget in self.root.winfo_children():
            if widget != self.canvas and not isinstance(widget, tk.Toplevel):
                widget.destroy()

    def cerrar_sesion(self):
        self.usuario_actual = None
        self.pantalla_login()

    def pantalla_login(self):
        self.auth.pantalla_login()

    def abrir_registro(self):
        self.auth.abrir_registro()

    def pantalla_carga(self):
        self.limpiar_pantalla()
        
        # Dimensions
        ancho, alto = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        
        # Background: School background slightly blurred with dark overlay (Optimized)
        # We load a downscaled version (1/6th of resolution) to apply the Gaussian blur instantly.
        # Then, we stretch it back up using bilinear filtering, which runs in milliseconds.
        low_w, low_h = max(100, ancho // 6), max(100, alto // 6)
        fondo_name = self.res.config.get("fondo_carga_filename", "fondo") if hasattr(self.res, 'config') else "fondo"
        # If it's custom_fondo, we use it. If not, use the original "fondo" for the loading screen.
        if fondo_name == "custom_fondo_carga":
            fondo_pil = self.res.get_pil_image(fondo_name, (low_w, low_h))
        else:
            fondo_pil = self.res.get_pil_image(fondo_name, (low_w, low_h))
            if not fondo_pil:
                fondo_pil = self.res.get_pil_image("fondo", (low_w, low_h))
        if fondo_pil:
            # Dark overlay to keep white text legible
            dark_overlay = Image.new("RGBA", (low_w, low_h), (15, 23, 42, 170))
            fondo_composite = Image.alpha_composite(fondo_pil.convert("RGBA"), dark_overlay)
            # Blur the small image (radius=2 here is equivalent to a large blur on full-res)
            fondo_blurred = fondo_composite.filter(ImageFilter.GaussianBlur(radius=2))
            # Resize back up to full screen
            fondo_stretched = fondo_blurred.resize((ancho, alto), Image.Resampling.BILINEAR)
            self._fondo_carga_tk = ImageTk.PhotoImage(fondo_stretched)
            self.canvas.create_image(0, 0, image=self._fondo_carga_tk, anchor="nw")
        else:
            self.canvas.create_rectangle(0, 0, ancho, alto, fill="#0f172a", outline="")
        
        # Center Logo
        logo = self.res.get_image("logo_nexus", (180, 180))
        self._logo_id = None
        if logo:
            self._logo_id = self.canvas.create_image(ancho // 2, alto // 2 - 80, image=logo, anchor="center")
            
        # Program Name
        self.canvas.create_text(ancho // 2, alto // 2 + 50, text="NEXUS", 
                                font=("Segoe UI", 36, "bold"), fill="#ffffff", anchor="center")
        # Subtitle
        self.canvas.create_text(ancho // 2, alto // 2 + 90, text="SISTEMA DE GESTIÓN ACADÉMICA", 
                                font=("Segoe UI", 11, "bold"), fill="#94a3b8", anchor="center")
                                
        # Loading Bar Track
        bar_w, bar_h = 320, 8
        bar_x = (ancho - bar_w) // 2
        bar_y = alto // 2 + 130
        
        # Draw track background
        self.canvas.create_line(bar_x, bar_y, bar_x + bar_w, bar_y, fill="#334155", width=bar_h, capstyle="round")
        
        # Progress line ID
        progress_line = self.canvas.create_line(bar_x, bar_y, bar_x, bar_y, fill="#f59e0b", width=bar_h, capstyle="round")
        
        # Loading percentage text
        pct_text = self.canvas.create_text(ancho // 2, bar_y + 25, text="Cargando... 0%", 
                                          font=("Segoe UI", 10, "bold"), fill="#94a3b8", anchor="center")
                                          
        # Variables for animation state
        self._loading_pct = 0
        self._active_notebook_ids = {}
        self._active_notebook_imgs = {}
        self._notebook_index = 0
        
        # Load the notebook and school tool images into a dictionary
        self._notebook_images = {}
        for name in ["cuaderno_rojo", "cuaderno_amarillo", "regla", "regla2", "colores", "borrador", "sacapuntas", "boligrafo", "compas", "bloc"]:
            pil_img = self.res.get_pil_image(name, (110, 110))
            if pil_img:
                self._notebook_images[name] = pil_img
                
        # Sequence of objects to display
        self._tool_sequence = ["cuaderno_rojo", "bloc", "regla", "cuaderno_amarillo", "sacapuntas", "colores", "boligrafo", "regla2", "compas", "borrador"]
                
        # Start loading bar progress simulation
        import math
        self._pencil_ids = []
        self._particles = []
        self._particle_loop_running = True
        
        def draw_pencil(x, y):
            for pid in self._pencil_ids:
                try:
                    self.canvas.delete(pid)
                except:
                    pass
            self._pencil_ids = []
            
            # Wiggle calculation (oscillate angle slightly to look like writing)
            wiggle = 8 * math.sin(self._loading_pct * 0.7)
            angle_rad = math.radians(45 + wiggle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            
            # Helper to convert local coordinates with dynamic angle
            def to_canvas(p, q):
                cx = x - p * cos_a - q * sin_a
                cy = y - p * sin_a + q * cos_a
                return (cx, cy)
                
            p_lead = [to_canvas(0, 0), to_canvas(4, -2), to_canvas(4, 2)]
            p_wood = [to_canvas(4, -2), to_canvas(4, 2), to_canvas(10, 4), to_canvas(10, -4)]
            p_body = [to_canvas(10, -4), to_canvas(10, 4), to_canvas(32, 4), to_canvas(32, -4)]
            p_metal = [to_canvas(32, -4), to_canvas(32, 4), to_canvas(35, 4), to_canvas(35, -4)]
            p_eraser = [to_canvas(35, -4), to_canvas(35, 4), to_canvas(41, 4), to_canvas(41, -4)]
            
            f_lead = [coord for pt in p_lead for coord in pt]
            f_wood = [coord for pt in p_wood for coord in pt]
            f_body = [coord for pt in p_body for coord in pt]
            f_metal = [coord for pt in p_metal for coord in pt]
            f_eraser = [coord for pt in p_eraser for coord in pt]
            
            self._pencil_ids.append(self.canvas.create_polygon(f_wood, fill="#e5c19d", outline=""))
            self._pencil_ids.append(self.canvas.create_polygon(f_lead, fill="#1e293b", outline=""))
            self._pencil_ids.append(self.canvas.create_polygon(f_body, fill="#f59e0b", outline=""))
            self._pencil_ids.append(self.canvas.create_polygon(f_metal, fill="#94a3b8", outline=""))
            self._pencil_ids.append(self.canvas.create_polygon(f_eraser, fill="#f43f5e", outline=""))

        def update_particles():
            if not getattr(self, '_particle_loop_running', False):
                return
            next_particles = []
            for p_id, px, py, pvx, pvy, life in self._particles:
                life -= 0.05
                if life > 0:
                    px += pvx
                    py += pvy
                    pvy += 0.08  # small gravity
                    try:
                        self.canvas.coords(p_id, px - 1.5, py - 1.5, px + 1.5, py + 1.5)
                        if life < 0.3:
                            self.canvas.itemconfig(p_id, fill="#334155")
                        elif life < 0.6:
                            self.canvas.itemconfig(p_id, fill="#64748b")
                        next_particles.append((p_id, px, py, pvx, pvy, life))
                    except:
                        pass
                else:
                    try:
                        self.canvas.delete(p_id)
                    except:
                        pass
            self._particles = next_particles
            self.root.after(20, update_particles)

        def update_progress():
            if not hasattr(self, '_loading_pct'):
                return
            self._loading_pct += 1
            if self._loading_pct <= 100:
                current_w = (bar_w * self._loading_pct) / 100
                self.canvas.coords(progress_line, bar_x, bar_y, bar_x + current_w, bar_y)
                self.canvas.itemconfig(pct_text, text=f"Cargando... {self._loading_pct}%")
                draw_pencil(bar_x + current_w, bar_y)
                
                # Spawn graphite dust particles
                for _ in range(random.randint(1, 3)):
                    px = bar_x + current_w
                    py = bar_y + random.randint(-1, 1)
                    pvx = random.uniform(-2.5, -0.5)
                    pvy = random.uniform(-1.2, 0.8)
                    p_id = self.canvas.create_oval(px - 1.5, py - 1.5, px + 1.5, py + 1.5, fill="#94a3b8", outline="")
                    if self._pencil_ids:
                        self.canvas.tag_lower(p_id, self._pencil_ids[0])
                    self._particles.append((p_id, px, py, pvx, pvy, 1.0))
                    
                self.root.after(90, update_progress)
            else:
                self.iniciar_transicion_login()
                
        # floating notebook animation logic
        self._notebook_anim_running = True
        
        def animate_notebook(loop_id):
            if not getattr(self, '_notebook_anim_running', False) or not self._notebook_images:
                return
                
            # Get next tool name in sequence, retrieve its PIL image
            tool_name = self._tool_sequence[self._notebook_index]
            self._notebook_index = (self._notebook_index + 1) % len(self._tool_sequence)
            pil_img = self._notebook_images.get(tool_name)
            if not pil_img:
                self.root.after(100, lambda: animate_notebook(loop_id))
                return
            
            # Start position and end position (keep them outside the center area or let them float around)
            side = random.choice(["left", "right", "top", "bottom"])
            if side == "left":
                x_start = -110
                y_start = random.randint(100, alto - 200)
                x_end = ancho + 110
                y_end = y_start + random.randint(-150, 150)
            elif side == "right":
                x_start = ancho + 110
                y_start = random.randint(100, alto - 200)
                x_end = -110
                y_end = y_start + random.randint(-150, 150)
            elif side == "top":
                x_start = random.randint(150, ancho - 150)
                y_start = -110
                x_end = x_start + random.randint(-200, 200)
                y_end = alto + 110
            else:
                x_start = random.randint(150, ancho - 150)
                y_start = alto + 110
                x_end = x_start + random.randint(-200, 200)
                y_end = -110
            
            angle_start = random.randint(-45, 45)
            angle_end = angle_start + random.choice([-1, 1]) * random.randint(60, 180)
            
            steps = 85
            current_step = 0
            
            def set_opacity_and_rotation(img, op, angle):
                # Rotate image (expand=True ensures corners are not cut)
                rotated = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
                alpha = rotated.split()[3]
                alpha = alpha.point(lambda p: int(p * op))
                new_img = rotated.copy()
                new_img.putalpha(alpha)
                return ImageTk.PhotoImage(new_img)
                
            def step_anim():
                nonlocal current_step
                if not getattr(self, '_notebook_anim_running', False):
                    return
                if current_step < steps:
                    progress = current_step / steps
                    curr_x = x_start + (x_end - x_start) * progress
                    curr_y = y_start + (y_end - y_start) * progress
                    curr_angle = angle_start + (angle_end - angle_start) * progress
                    
                    if progress < 0.25:
                        opacity = progress / 0.25
                    elif progress > 0.75:
                        opacity = (1.0 - progress) / 0.25
                    else:
                        opacity = 1.0
                        
                    try:
                        tk_img = set_opacity_and_rotation(pil_img, opacity, curr_angle)
                        self._active_notebook_imgs[loop_id] = tk_img
                        
                        if loop_id in self._active_notebook_ids:
                            self.canvas.delete(self._active_notebook_ids[loop_id])
                        
                        new_id = self.canvas.create_image(curr_x, curr_y, image=tk_img, anchor="center")
                        self._active_notebook_ids[loop_id] = new_id
                        
                        if self._logo_id:
                            self.canvas.tag_lower(new_id, self._logo_id)
                    except Exception as e:
                        print(f"Error drawing notebook: {e}")
                        
                    current_step += 1
                    self.root.after(22, step_anim)
                else:
                    if loop_id in self._active_notebook_ids:
                        self.canvas.delete(self._active_notebook_ids[loop_id])
                        del self._active_notebook_ids[loop_id]
                    if loop_id in self._active_notebook_imgs:
                        del self._active_notebook_imgs[loop_id]
                    self.root.after(200, lambda: animate_notebook(loop_id))
                    
            step_anim()
            
        update_progress()
        update_particles()
        # Start two concurrent animation loops with an offset of 1.2 seconds
        animate_notebook(1)
        self.root.after(1200, lambda: animate_notebook(2))

    def _cleanup_loading_screen(self):
        self._notebook_anim_running = False
        if hasattr(self, '_loading_pct'):
            del self._loading_pct
        if hasattr(self, '_active_notebook_ids'):
            for lid, nid in self._active_notebook_ids.items():
                try:
                    self.canvas.delete(nid)
                except:
                    pass
            self._active_notebook_ids.clear()
        if hasattr(self, '_active_notebook_imgs'):
            self._active_notebook_imgs.clear()
        if hasattr(self, '_pencil_ids'):
            for pid in self._pencil_ids:
                try:
                    self.canvas.delete(pid)
                except:
                    pass
            del self._pencil_ids

    def iniciar_transicion_login(self):
        ancho, alto = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        
        # Tema azul oscuro
        base_color = (15, 23, 42)
        fade_steps = 15
        fade_delay = 20  # 300ms total fade-out, 300ms fade-in
        
        def set_overlay_alpha(alpha_val):
            overlay_img = Image.new("RGBA", (ancho, alto), base_color + (alpha_val,))
            tk_overlay = ImageTk.PhotoImage(overlay_img)
            self._fade_overlay_tk = tk_overlay
            
            if hasattr(self, '_fade_overlay_id') and self._fade_overlay_id:
                try:
                    self.canvas.delete(self._fade_overlay_id)
                except:
                    pass
            self._fade_overlay_id = self.canvas.create_image(0, 0, image=tk_overlay, anchor="nw")
            
        def fade_out(step=0):
            if step <= fade_steps:
                alpha = int((step / fade_steps) * 255)
                set_overlay_alpha(alpha)
                self.root.after(fade_delay, lambda: fade_out(step + 1))
            else:
                self._cleanup_loading_screen()
                self.auth.pantalla_login()
                fade_in(fade_steps)
                
        def fade_in(step=fade_steps):
            if step >= 0:
                alpha = int((step / fade_steps) * 255)
                set_overlay_alpha(alpha)
                self.root.after(fade_delay, lambda: fade_in(step - 1))
            else:
                if hasattr(self, '_fade_overlay_id') and self._fade_overlay_id:
                    try:
                        self.canvas.delete(self._fade_overlay_id)
                    except:
                        pass
                    self._fade_overlay_id = None
                if hasattr(self, '_fade_overlay_tk'):
                    del self._fade_overlay_tk

        fade_out(0)

    # ------------- PANEL PRINCIPAL -------------

    # ── constantes de color / tipografía ────────────────────────────────────
    C_BLUE   = "#1a73e8"
    C_GREEN  = "#34a853"
    C_RED    = "#ea4335"
    C_DARK   = "#202124"
    C_GRAY   = "#5f6368"
    C_SEP    = "#dadce0"
    C_HOVER  = "#e8f0fe"
    FONT_TTL = ("Segoe UI", 19, "bold")
    FONT_NAV = ("Segoe UI", 11)
    FONT_SM  = ("Segoe UI", 9)

    def verificar_bloqueo(self):
        if self.sistema_bloqueado:
            messagebox.showwarning("Sistema Bloqueado", "El período de prueba ha finalizado. Por favor, active el sistema en la pestaña de Configuración para usar esta función.")
            return True
        return False

    def abrir_menu_principal(self, start_module="dashboard"):
        self.limpiar_pantalla()
        
        ancho, alto = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        sw = 260 # Sidebar width
        hh = 85  # Header height
        
        is_pro = getattr(self, "is_pro", False)
        
        # Fondo general (el pergamino con el escudo)
        fondo_name = self.res.config.get("fondo_filename", "custom_fondo")
        w_img, h_img = ancho - sw, alto - hh
        fondo_pil = self.res.get_pil_image(fondo_name, (w_img, h_img))
        
        if fondo_pil:
            if is_pro:
                # Dibujar fondo base del canvas para que la imagen se difumine hacia este color
                self.canvas.create_rectangle(sw, hh, ancho, alto, fill="#334155", outline="")
                
                # Crear máscara para un degradado perfecto en los bordes superior e izquierdo
                mask = Image.new('L', (w_img, h_img), 255)
                grad_size = 250 # Transición muy larga y suave
                import math
                
                # Degradado Izquierdo
                if w_img > grad_size:
                    left_fade = Image.new('L', (grad_size, 1))
                    for x in range(grad_size):
                        val = int(255 * math.sin((x / grad_size) * (math.pi / 2)))
                        left_fade.putpixel((x, 0), val)
                    left_fade = left_fade.resize((grad_size, h_img))
                    mask.paste(left_fade, (0, 0))
                
                # Degradado Superior
                if h_img > grad_size:
                    top_fade = Image.new('L', (1, grad_size))
                    for y in range(grad_size):
                        val = int(255 * math.sin((y / grad_size) * (math.pi / 2)))
                        top_fade.putpixel((0, y), val)
                    top_fade = top_fade.resize((w_img, grad_size))
                    
                    top_mask = Image.new('L', (w_img, h_img), 255)
                    top_mask.paste(top_fade, (0, 0))
                    from PIL import ImageChops
                    mask = ImageChops.multiply(mask, top_mask)
                
                fondo_pil.putalpha(mask)
            else:
                # Volvemos al método de overlay para evitar cuadros duros en la esquina
                grad_x = 300 # Un poco más amplio en el lado izquierdo
                grad_y = 150 # Superior
                
                def hex_to_rgba(hex_color, alpha=255):
                    hex_color = hex_color.lstrip('#')
                    if len(hex_color) == 6:
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
                    return (0, 0, 0, alpha)
                
                c_side_hex = self.res.config.get("color_sidebar", "#0d315f")
                c_head_hex = self.res.config.get("color_header", "#06101c")
                
                c_sidebar = hex_to_rgba(c_side_hex)
                c_header = hex_to_rgba(c_head_hex)
                
                shadow = Image.new('RGBA', (w_img, h_img), (0,0,0,0))
                import math
                
                # Degradado Izquierdo (hacia la barra lateral)
                if w_img > grad_x:
                    left_shadow = Image.new('RGBA', (grad_x, 1))
                    for x in range(grad_x):
                        # Curva cuadrática para que el color caiga rápido y no deje efecto de "sombra pesada"
                        factor = 1 - (x / grad_x)
                        alpha = int(255 * (factor ** 2))
                        left_shadow.putpixel((x, 0), c_sidebar[:3] + (alpha,))
                    left_shadow = left_shadow.resize((grad_x, h_img))
                    shadow.paste(left_shadow, (0, 0))
                
                # Degradado Superior (hacia la cabecera)
                if h_img > grad_y:
                    top_shadow = Image.new('RGBA', (1, grad_y))
                    for y in range(grad_y):
                        factor = 1 - (y / grad_y)
                        alpha = int(255 * (factor ** 2))
                        top_shadow.putpixel((0, y), c_header[:3] + (alpha,))
                    top_shadow = top_shadow.resize((w_img, grad_y))
                    shadow.alpha_composite(top_shadow, (0, 0))
                
                fondo_pil = fondo_pil.convert("RGBA")
                fondo_pil = Image.alpha_composite(fondo_pil, shadow)
                
            self._fondo_tk = ImageTk.PhotoImage(fondo_pil)
            self.canvas.create_image(sw, hh, image=self._fondo_tk, anchor="nw")

        # ── SIDEBAR & HEADER ──
        is_pro = getattr(self, "is_pro", False)
        
        if is_pro:
            theme_color = "#334155" # Nuevo color unificado, más claro y elegante (Slate)
            
            # Dibujar el sidebar y el header como una sola pieza (del mismo color)
            self.canvas.create_rectangle(0, 0, sw, alto, fill=theme_color, outline="")
            self.canvas.create_rectangle(sw, 0, ancho, hh, fill=theme_color, outline="")
            
            # Curva interior perfecta y suavizada usando PIL
            r = 40 # Radio de la curva
            scale = 4
            r_hq = r * scale
            
            # Crear un bloque del color del tema
            img_corner = Image.new('RGBA', (r_hq, r_hq), theme_color)
            
            # Máscara para recortar el círculo y hacer la curva interior
            mask = Image.new('L', (r_hq, r_hq), 255)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse([0, 0, 2*r_hq, 2*r_hq], fill=0)
            
            img_corner.putalpha(mask)
            
            # Antialiasing perfecto al reducir el tamaño
            img_corner = img_corner.resize((r, r), Image.Resampling.LANCZOS)
            
            self._tk_corner = ImageTk.PhotoImage(img_corner)
            self.canvas.create_image(sw, hh, image=self._tk_corner, anchor="nw")
            
            header_text_color = "#cda434"
            header_sub_color = "#fcd34d"
        else:
            sidebar_bg = COLORS["DARK_BLUE"]
            self.canvas.create_rectangle(0, 0, sw, alto, fill=sidebar_bg, outline="")
            self.canvas.create_rectangle(sw, 0, ancho, hh, fill=COLORS["HEADER_BLUE"], outline="")
            
            header_text_color = "white"
            header_sub_color = "#bbd6ff"
        
        # Texto Institucional (Movido a la esquina, sin logo)
        margin_x = 25
        self.canvas.create_text(sw + margin_x + (15 if is_pro else 0), 10, anchor="nw",
            text=self.res.config.get("school_name", "COMPLEJO EDUCATIVO ARISMENDI"),
            font=("Segoe UI", 16, "bold"), fill=header_text_color)
        self.canvas.create_text(sw + margin_x + (15 if is_pro else 0), 42, anchor="nw",
            text="SISTEMA DE GESTIÓN ACADÉMICA" + (" [VERSIÓN PRO]" if getattr(self, "is_pro", False) else ""),
            font=("Segoe UI", 11, "bold"), fill=header_sub_color)
        self.canvas.create_text(sw + margin_x + (15 if is_pro else 0), 62, anchor="nw",
            text=f"Bienvenido(a) Prof. {self.usuario_actual}",
            font=("Segoe UI", 10), fill="#cce0ff" if not getattr(self, "is_pro", False) else "#fde68a")
        
        # Área de Perfil del Usuario (Derecha)
        self.canvas.create_text(ancho - 80, hh // 2 - 10, text=f"{self.usuario_actual}", 
                                font=("Segoe UI", 13, "bold"), fill="white", anchor="e")
        self.canvas.create_text(ancho - 80, hh // 2 + 12, text="Admin", 
                                font=("Segoe UI", 10), fill="#bbd6ff", anchor="e")
        
        # Icono de usuario Circular (Alta resolución con Anti-Aliasing)
        sz = 46
        sz_hq = sz * 4
        img_usr_hq = Image.new('RGBA', (sz_hq, sz_hq), (0,0,0,0))
        draw_usr = ImageDraw.Draw(img_usr_hq)
        
        # 1. Fondo gris oscuro
        draw_usr.ellipse([4, 4, sz_hq-4, sz_hq-4], fill="#353740")
        
        # 2. Silueta blanca de usuario (completamente dentro, centrada)
        # Cabeza
        draw_usr.ellipse([74, 34, 110, 70], fill="white") 
        # Hombros (la base plana ahora queda totalmente dentro del círculo)
        draw_usr.chord([47, 76, 137, 224], 180, 360, fill="white")
        
        # 3. Borde dorado dibujado ENCIMA para contener perfectamente los hombros
        draw_usr.ellipse([4, 4, sz_hq-4, sz_hq-4], outline="#c0a97b", width=10)
        
        # Redimensionar con filtro Lanczos para bordes ultralisos
        img_usr = img_usr_hq.resize((sz, sz), Image.Resampling.LANCZOS)
        tk_usr = ImageTk.PhotoImage(img_usr)
        
        if not hasattr(self, '_usr_imgs'):
            self._usr_imgs = []
        self._usr_imgs.append(tk_usr)
        
        self.canvas.create_image(ancho - 45, hh // 2, image=tk_usr)

        # área de contenido
        self._cx  = sw + 40
        self._cy  = hh + 40
        self._cw  = ancho - sw - 80
        self._ch  = alto - hh - 80
        self._sw  = sw

        self.dibujar_sidebar()
        
        # Iniciar en módulo correspondiente
        if start_module == "dashboard":
            self.modo_actual = "dashboard"
            self.modulo_dashboard()
            # Tareas en segundo plano al iniciar
            self.verificar_actualizaciones_inicio()
            self.verificar_respaldo_automatico()
            self.verificar_configuracion_inicial_copias()
        elif start_module == "configuracion":
            self.modo_actual = "configuracion"
            self.modulo_configuracion()

    # ── utilidades de contenido ──────────────────────────────────────────────
    def _cp(self, widget, x, y, w=None, h=None):
        if w and h:
            shad = self.canvas.create_rectangle(
                self._cx + x + 2, self._cy + y + 2, self._cx + x + w + 3, self._cy + y + h + 3,
                fill="#eeeeee", outline="")
            self.cc_ids.append(shad)

        win_id = self.canvas.create_window(
            self._cx + x, self._cy + y, window=widget, anchor="nw",
            width=w, height=h)
        self.cc_ids.append(win_id)
        self.cc_wgts.append(widget)
        return win_id

    def _ct(self, txt, x, y, **kw):
        cid = self.canvas.create_text(
            self._cx + x, self._cy + y, text=txt, **kw)
        self.cc_ids.append(cid)
        return cid

    def _crect(self, x1, y1, x2, y2, **kw):
        cid = self.canvas.create_rectangle(
            self._cx+x1, self._cy+y1, self._cx+x2, self._cy+y2, **kw)
        self.cc_ids.append(cid)
        return cid

    def limpiar_contenido(self):
        # Limpiar SOLO el contenido, NO el sidebar ni header
        for cid in self.cc_ids:
            try: 
                self.canvas.delete(cid)
            except: 
                pass
        self.cc_ids = []
        
        for widget in self.cc_wgts:
            try:
                widget.destroy()
            except:
                pass
        self.cc_wgts = []
        
        # Limpiar también los elementos del módulo de estadísticas (pestaña abierta,
        # menú de círculos, widgets de tkinter embebidos) que se guardan en listas propias
        # y NO forman parte de cc_ids/cc_wgts
        if hasattr(self, '_limpiar_pestana'):
            try:
                self._limpiar_pestana()
            except Exception:
                pass
        
        # Nota: No limpiamos variables de búsqueda/filtros aquí para preservar el estado de navegación
        pass

    # ── sidebar ──────────────────────────────────────────────────────────────
    def dibujar_sidebar(self):
        sw = self._sw

        # Logo de la Escuela (Flotante)
        lx, ly = sw // 2, 95
        logo_name = self.res.config.get("logo_filename", "logo")
        logo_esc = self.res.get_image(logo_name, (180, 180))
        if logo_esc:
            self.canvas.create_image(lx, ly, image=logo_esc, anchor="center")

        # Iconos y Nombres
        nav = [
            ("iconos del panel/inicio", "Inicio",         self.modulo_dashboard, "⌂"),
            ("iconos del panel/estudiantes", "Estudiantes",           self.modulo_estudiantes, "👥"),
            ("iconos del panel/profesores",  "Profesores",        self.modulo_profesores, "🧑‍🏫"),
            ("iconos del panel/notas",  "Notas",             self.modulo_notas, "★"),
            ("iconos del panel/horarios",    "Horarios",          self.modulo_horarios, "🗓"),
            ("iconos del panel/constancias", "Constancias",         self.modulo_constancias, "🗎"),
            ("iconos del panel/estadistica", "Estadísticas",       self.modulo_estadistica, "📊"),

            ("iconos del panel/equipo_desarrollo",  "Configuración",self.modulo_configuracion, "⚙"),
        ]

        self._btn_info = {}
        y_base = 195
        btn_h  = 42
        btn_w  = sw - 50
        x_btn  = 25
        
        is_pro = getattr(self, "is_pro", False)
        
        if is_pro:
            C_BTN    = "#1e293b" # Slate oscuro para los botones
            C_ICON_BG = "#cda434" # Gold 
            C_ICON_FG = "#ffffff"
            hover_color = "#fcd34d" # Gold for text hover
        else:
            C_BTN    = "#1e293b"
            C_ICON_BG = "#f59e0b"
            C_ICON_FG = "#0f172a"
            hover_color = "#00e5ff"

        for i, (ic_type, name, cmd, ic_text) in enumerate(nav):
            if name == "Configuración":
                # Posicionarlo justo encima del botón de cerrar sesión
                by = (y_base + 5 * (btn_h + 8) + 230) - (btn_h + 10)
            else:
                by = y_base + i * (btn_h + 8)
            
            radius = btn_h // 2
            
            def create_btn_img(is_hover=False):
                scale = 4
                sw, sh = btn_w * scale, btn_h * scale
                srad = radius * scale
                img = Image.new('RGBA', (sw, sh), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                
                fill_color = "#334155" if is_hover else C_BTN
                
                if is_pro:
                    outline_color = hover_color if is_hover else "#cda434"
                    border_w = (2 * scale) if is_hover else (1 * scale)
                    
                    # Rectángulo principal con antialiasing
                    draw.rounded_rectangle([(border_w//2, border_w//2), (sw - border_w//2 - 1, sh - border_w//2 - 1)],
                                         radius=srad, fill=fill_color, outline=outline_color, width=border_w)
                else:
                    draw.rounded_rectangle([(0,0),(sw-1,sh-1)], radius=srad, fill=fill_color)
                    
                    ix_c, iy_c, isz_c = 6, 6, btn_h - 12
                    six_c, siy_c, sisz_c = ix_c * scale, iy_c * scale, isz_c * scale
                    icon_bg = hover_color if is_hover else C_ICON_BG
                    draw.rounded_rectangle([(six_c, siy_c), (six_c+sisz_c-1, siy_c+sisz_c-1)], radius=6*scale, fill=icon_bg)
                
                # Resize con antialiasing para bordes perfectos
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = Image.LANCZOS
                    
                res_img = img.resize((btn_w, btn_h), resample_filter)
                
                if not is_pro:
                    isz_i = 22
                    off = (isz_c - isz_i) // 2
                    ix_i, iy_i = ix_c + off, iy_c + off
                    ic_img = self.res.get_pil_image(ic_type, (isz_i, isz_i))
                    if ic_img:
                        res_img.alpha_composite(ic_img, (ix_i, iy_i))
                return ImageTk.PhotoImage(res_img)

            tk_normal = create_btn_img(False)
            tk_hover = create_btn_img(True)
            self._side_imgs.extend([tk_normal, tk_hover])
            
            bg_id = self.canvas.create_image(x_btn, by, image=tk_normal, anchor="nw")
            
            sel_color = "#cda434" if is_pro else "#f59e0b"
            sel_id = self.canvas.create_rectangle(x_btn-8, by+12, x_btn-5, by+btn_h-12, 
                                                   fill=sel_color, outline="", state="hidden")

            btn_bg_color = C_BTN
            btn_fg_color = "#e2e8f0" if is_pro else "white"
            font_style = ("Segoe UI", 11) if is_pro else ("Segoe UI", 11, "bold")
            
            li = None
            if is_pro:
                lbl_icon = tk.Label(self.root, text=ic_text, font=("Segoe UI Emoji", 14), bg=btn_bg_color, fg="#cda434", cursor="hand2")
                self.canvas.create_window(x_btn + 20, by + btn_h//2, window=lbl_icon, anchor="center")
                li = lbl_icon

            lbl_text = tk.Label(self.root, text=name, font=font_style,
                                bg=btn_bg_color, fg=btn_fg_color, cursor="hand2")
            tx_id = self.canvas.create_window(x_btn + btn_h + (10 if is_pro else 2), by + btn_h//2, window=lbl_text, anchor="w")

            def make_fn(c, n):
                def fn(e=None): 
                    self._highlight(n)
                    # Resetear modo al navegar a otro módulo
                    self.modo_actual = "dashboard"
                    c()
                return fn

            f_click = make_fn(cmd, name)
            lbl_text.bind("<1>", f_click)
            self.canvas.tag_bind(bg_id, "<1>", f_click)
            if is_pro:
                lbl_icon.bind("<1>", f_click)

            def on_e(e, n=name, l2=lbl_text, hc=hover_color, bg_i=bg_id, tk_h=tk_hover, l1=li):
                l2.configure(fg=hc, bg="#334155")
                if l1: l1.configure(bg="#334155", fg=hc)
                self.canvas.itemconfig(bg_i, image=tk_h)

            def on_l(e, n=name, l2=lbl_text, fc=btn_fg_color, bg_i=bg_id, tk_n=tk_normal, l1=li):
                if getattr(self, "_active_name", "") and n != self._active_name: 
                    l2.configure(fg=fc)
                l2.configure(bg=btn_bg_color)
                if l1: l1.configure(bg=btn_bg_color, fg="#cda434")
                self.canvas.itemconfig(bg_i, image=tk_n)

            self.canvas.tag_bind(bg_id, "<Enter>", on_e)
            self.canvas.tag_bind(bg_id, "<Leave>", on_l)
            lbl_text.bind("<Enter>", on_e)
            lbl_text.bind("<Leave>", on_l)
            if is_pro:
                lbl_icon.bind("<Enter>", on_e)
                lbl_icon.bind("<Leave>", on_l)
            
            self._btn_info[name] = (lbl_text, bg_id, sel_id)

        # Botón Cerrar Sesión
        last_y = y_base + 5 * (btn_h + 8) + 230
        
        if is_pro:
            C_OUT_BTN = "#1e293b" # Mismo fondo de boton para salir
            C_OUT_IC  = "#ef4444"
            C_OUT_TX  = "#fca5a5"
        else:
            C_OUT_BTN = "#450a0a"
            C_OUT_IC  = "#dc2626"
            C_OUT_TX  = "#fecaca"

        def create_out_img(is_hover=False):
            scale = 4
            sw, sh = btn_w * scale, btn_h * scale
            srad = (btn_h//2) * scale
            img = Image.new('RGBA', (sw, sh), (0,0,0,0))
            draw_o = ImageDraw.Draw(img)
            
            fill_color = "#334155" if is_hover and is_pro else ("#7f1d1d" if is_hover else C_OUT_BTN)
            
            if is_pro:
                out_color = "#f87171" if is_hover else "#ef4444"
                border_w = 2 * scale if is_hover else 1 * scale
                draw_o.rounded_rectangle([(border_w//2, border_w//2), (sw - border_w//2 - 1, sh - border_w//2 - 1)], 
                                         radius=srad, fill=fill_color, outline=out_color, width=border_w)
            else:
                draw_o.rounded_rectangle([(0,0),(sw-1,sh-1)], radius=srad, fill=fill_color)
                
                isz_c = btn_h - 12
                six_c, siy_c, sisz_c = 6 * scale, 6 * scale, isz_c * scale
                bg_c = "#f87171" if is_hover else C_OUT_IC
                draw_o.rounded_rectangle([(six_c, siy_c), (six_c+sisz_c-1, siy_c+sisz_c-1)], radius=6*scale, fill=bg_c)
            
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.LANCZOS
            res_img = img.resize((btn_w, btn_h), resample_filter)
            
            if not is_pro:
                isz_i = 22
                off = (isz_c - isz_i) // 2
                ic_out = self.res.get_pil_image("iconos del panel/cerrar_sesion", (isz_i, isz_i))
                if ic_out:
                    res_img.alpha_composite(ic_out, (6 + off, 6 + off))
            return ImageTk.PhotoImage(res_img)

        tk_out_normal = create_out_img(False)
        tk_out_hover = create_out_img(True)
        self._side_imgs.extend([tk_out_normal, tk_out_hover])
        
        out_id = self.canvas.create_image(x_btn, last_y, image=tk_out_normal, anchor="nw")
        
        li_out = None
        if is_pro:
            lbl_out_icon = tk.Label(self.root, text="⏻", font=("Segoe UI Emoji", 14), bg=C_OUT_BTN, fg="#ef4444", cursor="hand2")
            self.canvas.create_window(x_btn + 20, last_y + btn_h//2, window=lbl_out_icon, anchor="center")
            li_out = lbl_out_icon
            
        l_out_tx = tk.Label(self.root, text="SALIR DEL SISTEMA", font=("Segoe UI", 10, "bold"), bg=C_OUT_BTN, fg=C_OUT_TX, cursor="hand2")
        self.canvas.create_window(x_btn + btn_h + (10 if is_pro else 2), last_y + btn_h//2, window=l_out_tx, anchor="w")

        def do_close(e=None): self.cerrar_sesion()
        self.canvas.tag_bind(out_id, "<1>", do_close)
        l_out_tx.bind("<1>", do_close)
        if is_pro:
            lbl_out_icon.bind("<1>", do_close)

        def out_on_e(e, bg_i=out_id, tk_h=tk_out_hover, l2=l_out_tx, l1=li_out):
            bg_hover = "#334155" if is_pro else "#7f1d1d"
            l2.configure(fg="white", bg=bg_hover)
            if l1: l1.configure(bg=bg_hover, fg="#f87171")
            self.canvas.itemconfig(bg_i, image=tk_h)

        def out_on_l(e, bg_i=out_id, tk_n=tk_out_normal, l2=l_out_tx, l1=li_out):
            l2.configure(fg=C_OUT_TX, bg=C_OUT_BTN)
            if l1: l1.configure(bg=C_OUT_BTN, fg="#ef4444")
            self.canvas.itemconfig(bg_i, image=tk_n)

        self.canvas.tag_bind(out_id, "<Enter>", out_on_e)
        self.canvas.tag_bind(out_id, "<Leave>", out_on_l)
        l_out_tx.bind("<Enter>", out_on_e)
        l_out_tx.bind("<Leave>", out_on_l)
        if is_pro:
            lbl_out_icon.bind("<Enter>", out_on_e)
            lbl_out_icon.bind("<Leave>", out_on_l)

        self._active_name = "Inicio"
        self._highlight("Inicio")

    def custom_error(self, titulo, mensaje):
        dlg = tk.Toplevel(self.root)
        dlg.geometry("400x220")
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        dlg.geometry(f"+{rx + (rw-400)//2}+{ry + (rh-220)//2}")
        
        c = tk.Canvas(dlg, bg="white", highlightthickness=1, highlightbackground="#dddddd")
        c.pack(fill="both", expand=True)

        c.create_rectangle(0, 0, 400, 45, fill="#b71c1c", outline="")
        c.create_text(20, 22, text=titulo.upper(), font=("Segoe UI", 11, "bold"), fill="white", anchor="w")
        c.create_oval(180, 55, 220, 95, fill="#fdeded", outline="#f5c2c2", width=1)
        c.create_text(200, 75, text="✕", font=("Segoe UI", 20, "bold"), fill="#d32f2f")
        c.create_text(200, 125, text=mensaje, font=("Segoe UI", 10), fill="#333", width=340, justify="center")
        
        def close(): dlg.destroy()
        btn = tk.Button(dlg, text="ENTENDIDO", font=("Segoe UI", 9, "bold"), bg="#b71c1c", fg="white", 
                        bd=0, cursor="hand2", padx=20, command=close)
        c.create_window(200, 180, window=btn, height=35)

    def _highlight(self, nombre):
        self._active_name = nombre
        for name, info in self._btn_info.items():
            l_text, bid, sid = info
            if name == nombre:
                self.canvas.itemconfig(sid, state="normal")
            else:
                self.canvas.itemconfig(sid, state="hidden")

    def mostrar_en_construccion(self):
        """Muestra un mensaje de que el módulo está en construcción"""
        messagebox.showinfo("🚧 En Construcción", 
            "Este módulo se encuentra en desarrollo.\n\nPróximamente estará disponible con nuevas funcionalidades.\n\n¡Gracias por tu paciencia!")

    def toggle_pro_mode(self):
        """Alterna la interfaz entre la versión normal y la versión PRO."""
        messagebox.showinfo("Próximamente", "Esta función estará disponible pronto.\nPor favor, contacte con su proveedor.")
        return
        
        # Redibujar la interfaz entera
        self.canvas.delete("all")
        for i in self.cc_ids:
            try: self.canvas.delete(i)
            except: pass
        self.cc_ids.clear()
        
        for w in self.cc_wgts:
            try: w.destroy()
            except: pass
        self.cc_wgts.clear()
        
        self._side_imgs.clear()
        if hasattr(self, '_usr_imgs'):
            self._usr_imgs.clear()
            
        self.abrir_menu_principal(start_module="configuracion")

if __name__ == "__main__":
    database.conectar()
    root = tk.Tk()

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", font=("Segoe UI", 10), rowheight=28,
                    background="#f8fbff", fieldbackground="#f8fbff",
                    foreground="#202124")
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                    background="#dde8ff", foreground="#1a73e8", relief="flat")
    style.map("Treeview",
        background=[("selected", "#c2d9ff")],
        foreground=[("selected", "#1a73e8")])

    app = AplicacionEscolar(root)
    root.mainloop()