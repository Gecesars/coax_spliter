import customtkinter as ctk
import pyvista as pv
import numpy as np
import matplotlib.pyplot as plt
import threading, queue, math, os, traceback, json, tempfile
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.filedialog as fd
from tkinter import messagebox
import skrf as rf
from skrf.network import Network
from skrf.frequency import Frequency
from skrf.plotting import plot_s_smith
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image as RLImage, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from skrf.media import DistributedCircuit

# --------------------------------------------------------------------
# 1. Imports HFSS/AEDT
# --------------------------------------------------------------------
try:
    from ansys.aedt.core import Hfss

    HFSS_AVAILABLE = True
except ImportError:
    HFSS_AVAILABLE = False
    print("ansys-aedt-core não encontrado. Funcionalidades HFSS desativadas.")

# --------------------------------------------------------------------
# 2. Configuração CTk
# --------------------------------------------------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# --------------------------------------------------------------------
# 3. Topologia
# --------------------------------------------------------------------
class Topology(Enum):
    COAXIAL = "Coaxial"


# --------------------------------------------------------------------
# 4. Materiais
# --------------------------------------------------------------------
SUBSTRATE_MATERIALS = {
    "Ar": (1.0006, 0.0),
    "Teflon (PTFE)": (2.1, 0.0002),
    "FR-4": (4.4, 0.02),
    "Rogers RO4003C": (3.55, 0.0027),
}


# --------------------------------------------------------------------
# 5. Classe Base de Cálculo
# --------------------------------------------------------------------
class RFCalculator(ABC):
    """Classe base abstrata para todos os tipos de cálculos de RF."""

    def __init__(self, params):
        self.params = params
        self.results = {}
        self.s_params_th = None
        self.s_params_sim = None
        self.project_path = ""
        self.frequencies = np.linspace(params['f_start'], params['f_stop'], 201)

    @abstractmethod
    def calculate(self):
        """Executa os cálculos geométricos e elétricos."""
        pass

    @abstractmethod
    def calculate_s_parameters(self):
        """Calcula os parâmetros S teóricos."""
        pass

    def get_geometry_for_viewer(self):
        """Retorna um dicionário combinado de parâmetros e resultados para visualização."""
        return {**self.params, **self.results}

    def _get_wavelength_mm(self, f_mhz, er):
        """Calcula o comprimento de onda em mm para uma dada frequência e permissividade."""
        return 299792.458 / (f_mhz * math.sqrt(er))

    def get_theoretical_network(self):
        """Cria um objeto skrf.Network a partir dos parâmetros S teóricos."""
        if self.s_params_th is None: return None
        freq = Frequency.from_f(self.frequencies * 1e6, unit='Hz')
        num_ports = self.params['n_outputs'] + 1
        s_matrix = np.zeros((len(self.frequencies), num_ports, num_ports), dtype=complex)
        s_matrix[:, 0, 0] = self.s_params_th.get('S11', 0)
        s_matrix[:, 1, 1] = self.s_params_th.get('S22', 0)
        s_matrix[:, 2, 1] = self.s_params_th.get('S32', 0)
        for i in range(self.params['n_outputs']):
            s_matrix[:, i + 1, 0] = self.s_params_th.get(f'S{i + 2}1', 0)
            s_matrix[:, 0, i + 1] = self.s_params_th.get(f'S{i + 2}1', 0)
        return Network(frequency=freq, s=s_matrix)

    def plot_performance(self):
        """
        Gera 3 gráficos de desempenho teórico: S11 (dB), S(n,1) (dB), e Carta de Smith para S11.
        """
        fig = plt.figure(figsize=(18, 5))
        gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8])
        fig.suptitle("Análise de Desempenho Teórico", fontsize=16)

        # --- Gráfico 1: S11 (Return Loss) ---
        ax1 = fig.add_subplot(gs[0, 0])
        if self.s_params_th:
            s11_db_th = 20 * np.log10(np.abs(self.s_params_th['S11']))
            ax1.plot(self.frequencies, s11_db_th, 'b-', label='S11 Teórico')
        if self.s_params_sim:
            s11_db_sim = 20 * np.log10(np.abs(self.s_params_sim.s[:, 0, 0]))
            ax1.plot(self.s_params_sim.f / 1e6, s11_db_sim, 'b--', label="S11 Simulado")
        ax1.set_title("Return Loss (S11)")
        ax1.set_xlabel("Frequência (MHz)")
        ax1.set_ylabel("Magnitude (dB)")
        ax1.grid(True);
        ax1.legend()

        # --- Gráfico 2: S(n,1) (Insertion Loss) ---
        ax2 = fig.add_subplot(gs[0, 1])
        num_outputs = self.params['n_outputs']
        colors = plt.cm.viridis(np.linspace(0, 1, num_outputs))
        if self.s_params_th:
            for i in range(num_outputs):
                port_name = f'S{i + 2}1'
                s_db_th = 20 * np.log10(np.abs(self.s_params_th[port_name]))
                ax2.plot(self.frequencies, s_db_th, color=colors[i], linestyle='-', label=f'{port_name} Teórico')
        if self.s_params_sim:
            for i in range(num_outputs):
                if self.s_params_sim.s.shape[1] > i + 1:
                    port_name = f'S{i + 2}1'
                    s_db_sim = 20 * np.log10(np.abs(self.s_params_sim.s[:, i + 1, 0]))
                    ax2.plot(self.s_params_sim.f / 1e6, s_db_sim, color=colors[i], linestyle='--',
                             label=f'{port_name} Simulado')
        ax2.set_title("Insertion Loss (S(n,1))")
        ax2.set_xlabel("Frequência (MHz)")
        ax2.grid(True);
        ax2.legend()

        # --- Gráfico 3: Smith Chart ---
        ax3 = fig.add_subplot(gs[0, 2])
        if self.s_params_th:
            ntw_th = self.get_theoretical_network()
            ntw_th.plot_s_smith(m=0, n=0, ax=ax3, show_legend=False, chart_style='fancy', color='blue')
        if self.s_params_sim:
            self.s_params_sim.plot_s_smith(m=0, n=0, ax=ax3, show_legend=False, chart_style='fancy', color='red',
                                           linestyle='--')
        ax3.set_title("Carta de Smith (S11)")

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        return fig


# --------------------------------------------------------------------
# 6. CoaxialCalculator
# --------------------------------------------------------------------
class CoaxialCalculator(RFCalculator):
    def calculate(self):
        p = self.params
        f0 = (p['f_start'] + p['f_stop']) / 2
        er = SUBSTRATE_MATERIALS[p['diel_material']][0]
        sec_len = self._get_wavelength_mm(f0, er) / 4
        len_inner = p['n_sections'] * sec_len
        len_outer = len_inner * 1.05
        d_int_tube = p['d_ext'] - 2 * p['wall_thick']
        d_out_50 = d_int_tube / math.exp(50 * math.sqrt(er) / 59.952)
        z0 = 50.0
        z_eff = 50.0 / p['n_outputs']
        z_sects = [z0 * (z_eff / z0) ** ((2 * i - 1) / (2 * p['n_sections'])) for i in range(1, p['n_sections'] + 1)]
        main_diams = [d_int_tube / math.exp(z_i * math.sqrt(er) / 59.952) for z_i in z_sects]
        self.results = {'sec_len_mm': sec_len, 'len_inner_mm': len_inner, 'len_outer_mm': len_outer,
                        'd_int_tube': d_int_tube, 'main_diams': main_diams, 'd_out_50ohm': d_out_50, 'z_sects': z_sects}
        self.calculate_s_parameters()
        return True

    def calculate_s_parameters(self):
        p = self.params
        er = SUBSTRATE_MATERIALS[p['diel_material']][0]
        N_freq = len(self.frequencies)
        freqs_hz = self.frequencies * 1e6
        s11 = self.theoretical_return_loss()
        Gamma = s11
        mismatch_loss_db = -10 * np.log10(1 - np.abs(Gamma) ** 2)
        ideal_split_loss_db = 10 * np.log10(p['n_outputs'])
        s21_db = -(mismatch_loss_db + ideal_split_loss_db)
        phase_velocity = 299792458 / np.sqrt(er)
        physical_length_m = self.results['len_inner_mm'] / 1000.0
        electrical_length = 2 * np.pi * freqs_hz * physical_length_m / phase_velocity
        s21 = 10 ** (s21_db / 20) * np.exp(-1j * electrical_length)
        s22 = s11
        isolation_db = -6
        s32 = 10 ** (isolation_db / 20) * np.ones(N_freq)
        self.s_params_th = {f'S{i + 2}1': s21 for i in range(p['n_outputs'])}
        self.s_params_th['S11'] = s11
        self.s_params_th['S22'] = s22
        self.s_params_th['S32'] = s32
        return True


# --------------------------------------------------------------------
# 7. Funções de Visualização e Relatório APRIMORADAS
# --------------------------------------------------------------------
def add_dimension_2d(plotter, p1, p2, label, offset_dir, text_size=12, precision=2):
    """Função auxiliar para adicionar cotas limpas a uma vista 2D."""
    p1, p2, offset_dir = np.array(p1), np.array(p2), np.array(offset_dir)
    dist = np.linalg.norm(p1 - p2)
    if dist < 1e-6: return
    mid_point = (p1 + p2) / 2
    offset_vec = offset_dir / np.linalg.norm(offset_dir)
    offset_dist = 12
    ext_p1 = p1 + offset_vec * (offset_dist * 0.5)
    ext_p2 = p2 + offset_vec * (offset_dist * 0.5)
    plotter.add_lines(np.vstack((p1, ext_p1)), color='dimgray', width=1)
    plotter.add_lines(np.vstack((p2, ext_p2)), color='dimgray', width=1)
    plotter.add_lines(np.vstack((ext_p1, ext_p2)), color='black', width=2)
    label_text = f"{dist:.{precision}f}" if isinstance(dist, (int, float)) else label
    label_pos = mid_point + offset_vec * (offset_dist)
    plotter.add_point_labels([label_pos], [label_text], font_size=text_size, text_color='black', shape=None,
                             show_points=False, always_visible=True)


def create_coaxial_geometry(p, for_report=False):
    """Gera a geometria 3D com iluminação e materiais aprimorados."""
    plotter_opts = {"window_size": (1200, 1000), "title": "Divisor Coaxial 3D"}
    if for_report: plotter_opts['off_screen'] = True
    plotter = pv.Plotter(**plotter_opts)
    plotter.set_background('white' if for_report else 'darkgrey', top='grey' if not for_report else 'white')
    plotter.add_light(pv.Light(position=(1, 1, 1), intensity=1.0))
    plotter.add_light(pv.Light(position=(-1, -1, 1), intensity=0.5))
    diel_principal = pv.Cylinder(center=(0, 0, p['len_outer_mm'] / 2), radius=p['d_int_tube'] / 2,
                                 height=p['len_outer_mm'])
    plotter.add_mesh(diel_principal, color='#D3D3D3', opacity=0.15)
    z_pos = 0
    for di in p['main_diams']:
        sec = pv.Cylinder(center=(0, 0, z_pos + p['sec_len_mm'] / 2), radius=di / 2, height=p['sec_len_mm'])
        plotter.add_mesh(sec, color='gold', pbr=True, metallic=0.85, roughness=0.3)
        z_pos += p['sec_len_mm']
    num_saidas = int(p['n_outputs'])
    output_len = p['len_inner_mm'] * 0.15
    if num_saidas > 6:
        dia_saida_diel = p['d_int_tube'] / 3.0
    elif num_saidas > 4:
        dia_saida_diel = p['d_int_tube'] / 2.2
    else:
        dia_saida_diel = p['d_int_tube']
    dia_saida_cond = dia_saida_diel / 2.3
    for k in range(num_saidas):
        angle_rad = math.radians(360 * k / num_saidas)
        x, y = math.cos(angle_rad), math.sin(angle_rad)
        center_pos = [x * output_len / 2, y * output_len / 2, p['len_inner_mm']]
        od = pv.Cylinder(center=center_pos, direction=(x, y, 0), radius=dia_saida_diel / 2, height=output_len)
        oi = pv.Cylinder(center=center_pos, direction=(x, y, 0), radius=dia_saida_cond / 2, height=output_len)
        plotter.add_mesh(od, color='#4682B4', opacity=0.3)
        plotter.add_mesh(oi, color='gold', pbr=True, metallic=0.85, roughness=0.2)
    plotter.camera_position = 'iso'
    plotter.camera.zoom(1.4)
    plotter.enable_parallel_projection()
    return plotter


def create_coaxial_geometry_2d_side_view(p):
    """Gera uma vista lateral 2D (corte) do transformador com dimensionamento técnico."""
    plotter = pv.Plotter(off_screen=True, window_size=(1600, 900))
    plotter.set_background('white')
    plotter.add_title("Vista Lateral (Corte 2D) - Dimensionamento", font_size=16)
    diel_height = p['len_outer_mm']
    diel_radius = p['d_int_tube'] / 2
    diel_outline_points = np.array(
        [[0, -diel_radius, 0], [diel_height, -diel_radius, 0], [diel_height, diel_radius, 0], [0, diel_radius, 0],
         [0, -diel_radius, 0]])
    plotter.add_mesh(pv.lines_from_points(diel_outline_points), color='lightgrey', line_width=3)
    z_pos = 0
    for di in p['main_diams']:
        sec_len = p['sec_len_mm']
        sec_radius = di / 2
        vertices = np.array(
            [[z_pos, -sec_radius, 0], [z_pos + sec_len, -sec_radius, 0], [z_pos + sec_len, sec_radius, 0],
             [z_pos, sec_radius, 0]])
        faces = np.hstack([[4, 0, 1, 2, 3]])
        plotter.add_mesh(pv.PolyData(vertices, faces), color='gold')
        z_pos += sec_len
    add_dimension_2d(plotter, [0, -diel_radius, 0], [diel_height, -diel_radius, 0], "", [0, -1, 0], text_size=14)
    plotter.add_point_labels([diel_height / 2, -diel_radius - 15, 0], [f"L Total: {diel_height:.2f} mm"],
                             text_color='black', font_size=14)
    add_dimension_2d(plotter, [0, -diel_radius, 0], [0, diel_radius, 0], f"{p['d_int_tube']:.2f}", [-1, 0, 0],
                     text_size=14)
    z_pos = 0
    for i, di in enumerate(p['main_diams']):
        sec_len = p['sec_len_mm']
        add_dimension_2d(plotter, [z_pos, diel_radius, 0], [z_pos + sec_len, diel_radius, 0],
                         f"L{i + 1}: {sec_len:.2f}", [0, 1, 0])
        add_dimension_2d(plotter, [z_pos + sec_len / 2, -di / 2, 0], [z_pos + sec_len / 2, di / 2, 0],
                         f"d{i + 1}: {di:.2f}", [1, 0.5, 0] if i % 2 == 0 else [-1, 0.5, 0])
        z_pos += sec_len
    plotter.view_zy()
    plotter.enable_parallel_projection()
    plotter.camera.zoom(1.2)
    return plotter


def export_full_pdf(calc: RFCalculator, queue: queue.Queue):
    """Gera um relatório PDF profissional com múltiplas vistas, gráficos e tabelas detalhadas."""
    pdf_path = fd.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
    if not pdf_path:
        queue.put("Exportação de PDF cancelada.")
        return
    queue.put("Gerando imagens para o relatório PDF...")
    params = calc.get_geometry_for_viewer()
    with tempfile.TemporaryDirectory() as tempdir:
        img3d_path = os.path.join(tempdir, "view3d_iso.png")
        plotter_3d = create_coaxial_geometry(params, for_report=True)
        plotter_3d.screenshot(img3d_path, scale=2)
        plotter_3d.close()
        img2d_path = os.path.join(tempdir, "view2d_side.png")
        plotter_2d = create_coaxial_geometry_2d_side_view(params)
        plotter_2d.screenshot(img2d_path, scale=2)
        plotter_2d.close()
        img_perf_path = os.path.join(tempdir, "performance.png")
        fig = calc.plot_performance()
        fig.savefig(img_perf_path, dpi=200, bbox_inches='tight')
        plt.close(fig)
        queue.put("Montando o PDF...")
        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter), topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        styles = getSampleStyleSheet()
        story = [Paragraph("Relatório de Análise de Divisor de Potência Coaxial", styles['Title']), Spacer(1, 12)]
        story.append(Paragraph("Visualização da Geometria", styles['h2']))
        data_imgs = [[RLImage(img3d_path, width=4.8 * inch, height=4 * inch),
                      RLImage(img2d_path, width=4.8 * inch, height=2.7 * inch)]]
        story.append(Table(data_imgs, colWidths=[5 * inch, 5 * inch], style=[('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Análise de Desempenho Teórico", styles['h2']))
        story.append(RLImage(img_perf_path, width=9.8 * inch, height=3.2 * inch))
        story.append(PageBreak())
        story.append(Paragraph("Parâmetros de Projeto e Resultados Calculados", styles['h2']))
        story.append(Spacer(1, 12))
        p, r = calc.params, calc.results
        param_data = [["Parâmetro de Entrada", "Valor"], ["Frequência", f"{p['f_start']} - {p['f_stop']} MHz"],
                      ["Nº de Seções", f"{p['n_sections']}"], ["Nº de Saídas", f"{p['n_outputs']}"],
                      ["Material Dielétrico", p['diel_material']]]
        mech_data = [["Parâmetros Mecânicos (mm)", "Valor"], ["Diâmetro Externo Tubo", f"{p['d_ext']:.3f}"],
                     ["Espessura Parede", f"{p['wall_thick']:.3f}"],
                     ["Diâmetro Interno Tubo", f"{r['d_int_tube']:.3f}"],
                     ["Comprimento Seção", f"{r['sec_len_mm']:.3f}"],
                     ["Comprimento Transformador", f"{r['len_inner_mm']:.3f}"],
                     ["Comprimento Total", f"{r['len_outer_mm']:.3f}"]]
        for i, diam in enumerate(r['main_diams'], 1): mech_data.append([f"d{i} (Diâmetro Seção {i})", f"{diam:.3f}"])
        elec_data = [["Parâmetros Elétricos (Ω)", "Valor"]]
        for i, z in enumerate(r['z_sects'], 1): elec_data.append([f"Z{i} (Impedância Seção {i})", f"{z:.2f}"])
        tbl_style = TableStyle(
            [('BACKGROUND', (0, 0), (-1, 0), colors.darkblue), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 1, colors.black),
             ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue)])
        t1 = Table(param_data, colWidths=[3 * inch, 2 * inch], hAlign='LEFT');
        t1.setStyle(tbl_style)
        t2 = Table(mech_data, colWidths=[3 * inch, 2 * inch], hAlign='LEFT');
        t2.setStyle(tbl_style)
        t3 = Table(elec_data, colWidths=[3 * inch, 2 * inch], hAlign='LEFT');
        t3.setStyle(tbl_style)
        story.append(Table([[t1, t2, t3]], colWidths=[3.4 * inch, 3.4 * inch, 3.4 * inch],
                           style=[('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        doc.build(story)
        queue.put(f"PDF salvo com sucesso em: {pdf_path}")


def launch_pyvista(params, q):
    try:
        plotter = create_coaxial_geometry(params, for_report=False)
        plotter.show()
        q.put("Visualização 3D fechada.")
    except Exception as e:
        q.put(f"Erro na visualização 3D: {e}")
        traceback.print_exc()


def generate_hfss_model(params, status_queue):
    if not HFSS_AVAILABLE:
        status_queue.put("ERRO: módulo HFSS não disponível.")
        return None
    project_path = None
    try:
        status_queue.put("Iniciando geração HFSS (lógica final e aprimorada)...")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        proj_name = f"Divisor_Coaxial_{ts}"
        project_dir = os.path.join(os.getcwd(), "HFSS_Projects")
        os.makedirs(project_dir, exist_ok=True)
        project_path = os.path.join(project_dir, f"{proj_name}.aedt")
        with Hfss(projectname=project_path, designname="DivisorCoaxial", solution_type="Modal", new_desktop=True,
                  close_on_exit=False) as hfss:
            mdl = hfss.modeler
            p = params
            f0_ghz = (p['f_start'] + p['f_stop']) / 2000.0
            vm = hfss.variable_manager
            vm["comp_total"] = f"{p['len_outer_mm']}mm"
            vm["comp_secoes"] = f"{p['len_inner_mm']}mm"
            vm["dia_int_tubo"] = f"{p['d_int_tube']}mm"
            output_port_len_float = p['len_inner_mm'] * 0.15
            vm["comp_saida"] = f"{output_port_len_float}mm"
            num_saidas = int(p['n_outputs'])
            if num_saidas > 6:
                vm["dia_saida_diel"] = "dia_int_tubo / 3"
                vm["dia_saida_cond"] = "(dia_int_tubo / 3) / 2.3"
            elif num_saidas > 4:
                vm["dia_saida_diel"] = "dia_int_tubo / 2.2"
                vm["dia_saida_cond"] = "(dia_int_tubo / 2.2) / 2.3"
            else:
                vm["dia_saida_diel"] = "dia_int_tubo"
                vm["dia_saida_cond"] = f"{p['d_out_50ohm']}mm"
            for i, d in enumerate(p['main_diams']): vm[f"dia_sc{i + 1}"] = f"{d}mm"
            diel_principal = mdl.create_cylinder("Z", [0, 0, 0], "dia_int_tubo/2", "comp_total", name="Diel_Principal",
                                                 num_sides=0)
            inner_parts = [
                mdl.create_cylinder("Z", [0, 0, f"{p['sec_len_mm'] * i}"], f"dia_sc{i + 1}/2", f"{p['sec_len_mm']}mm",
                                    name=f"Cond_Sec{i + 1}", num_sides=0) for i in range(p['n_sections'])]
            output_outer_1 = mdl.create_cylinder("X", [0, 0, "comp_secoes"], "dia_saida_diel/2", "comp_saida",
                                                 num_sides=0, name="Output_Outer_1")
            output_inner_1 = mdl.create_cylinder("X", [0, 0, "comp_secoes"], "dia_saida_cond/2", "comp_saida",
                                                 num_sides=0, name="Output_Inner_1")
            if p['n_outputs'] > 1:
                mdl.duplicate_around_axis([output_outer_1.name, output_inner_1.name], axis="Z",
                                          angle=f"360deg/{p['n_outputs']}", clones=p['n_outputs'])
            all_outers_names = [diel_principal.name] + [name for name in mdl.object_names if
                                                        name.startswith("Output_Outer_")]
            united_diel_name = mdl.unite(all_outers_names)
            final_diel_obj = mdl[united_diel_name]
            final_diel_obj.name = "Volume_Diel"
            inner_parts_names = [part.name for part in inner_parts]
            output_inners_names = [name for name in mdl.object_names if
                                   name.startswith("Cond_Saida_") or name.startswith("Output_Inner_")]
            all_inners_to_unite = inner_parts_names + output_inners_names
            united_cond_name = mdl.unite(all_inners_to_unite)
            final_cond_obj = mdl[united_cond_name]
            final_cond_obj.name = "Condutor_Unico"
            er_val, tand = SUBSTRATE_MATERIALS[p['diel_material']]
            mat_name = p['diel_material'].replace(' ', '_').replace('(', '').replace(')', '')
            if mat_name not in hfss.materials:
                new_mat = hfss.materials.add_material(mat_name)
                new_mat.permittivity = er_val
                new_mat.dielectric_loss_tangent = tand
            final_diel_obj.material_name = mat_name
            final_cond_obj.material_name = "pec"
            for face in final_diel_obj.faces:
                if abs(face.center[2]) < 1e-6:
                    hfss.wave_port(assignment=face.id, name="P1", renormalize=True, impedance="50ohm")
                    break
            for k in range(p['n_outputs']):
                angle_rad = math.radians(360 * k / p['n_outputs'])
                pos_x = output_port_len_float * math.cos(angle_rad)
                pos_y = output_port_len_float * math.sin(angle_rad)
                pos_z = p['len_inner_mm']
                for face in final_diel_obj.faces:
                    center = face.center
                    if np.linalg.norm(np.array(center) - np.array([pos_x, pos_y, pos_z])) < 1e-3:
                        hfss.wave_port(assignment=face.id, name=f"P{k + 2}", renormalize=True, impedance="50ohm")
                        break
            setup = hfss.create_setup("Setup1")
            setup.props["Frequency"] = f"{f0_ghz}GHz"
            setup.props["MaximumPasses"] = 8
            setup.props["MaxDeltaS"] = 0.02
            setup.create_frequency_sweep(unit="MHz", name="Sweep1", start_frequency=p['f_start'],
                                         stop_frequency=p['f_stop'], num_of_points=201, sweep_type="Fast",
                                         save_fields=False)
            hfss.save_project()
            status_queue.put(f"HFSS salvo em: {project_path}")
            return project_path
    except Exception as e:
        status_queue.put(f"ERRO HFSS: {e}")
        traceback.print_exc()
        return project_path


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ferramenta de Design de Divisor de Potência RF")
        self.geometry("1400x900")
        self.queue = queue.Queue()
        self.calc = None
        self.project_path = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.param_frame = ParameterFrame(self, self)
        self.param_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")

        self.result_frame = ResultFrame(self, self)
        self.result_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.status_bar = ctk.CTkLabel(self, text="Pronto. Insira os parâmetros e clique em 'Calcular'.", anchor="w")
        self.status_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.after(100, self.process_queue)
        self.update_button_states()

    def process_queue(self):
        try:
            msg = self.queue.get_nowait()
            self.status_bar.configure(text=str(msg))
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def calculate_and_display(self, params):
        self.calc = CoaxialCalculator(params)
        self.queue.put("Calculando parâmetros geométricos e teóricos...")
        if self.calc.calculate():
            self.queue.put("Cálculo concluído. Gerando visualizações...")
            self.result_frame.display_results(self.calc)
            self.update_button_states()
        else:
            self.queue.put("Erro no cálculo. Verifique os parâmetros.")
            messagebox.showerror("Erro de Cálculo", "Não foi possível calcular o divisor com os parâmetros fornecidos.")
            self.calc = None
            self.update_button_states()

    def export_hfss(self):
        if self.calc:
            thread = threading.Thread(target=self._export_hfss_thread, daemon=True)
            thread.start()

    def _export_hfss_thread(self):
        path = generate_hfss_model(self.calc.get_geometry_for_viewer(), self.queue)
        if path:
            self.project_path = path
            self.after(0, self.update_button_states)

    def _run_hfss_simulation_thread(self, project_path, queue):
        """Método interno para ser executado em uma thread."""
        if not HFSS_AVAILABLE or not project_path:
            queue.put("ERRO: Simulação HFSS não pode ser iniciada.")
            return
        try:
            queue.put("Iniciando simulação HFSS...")
            with Hfss(project=project_path, new_desktop=False, close_on_exit=True) as hfss:
                queue.put("Analisando o setup 'Setup1'...")
                hfss.analyze_setup("Setup1")
                queue.put("Simulação HFSS concluída.")
                export_dir = os.path.dirname(project_path)
                hfss.export_touchstone("Setup1", "Sweep1", export_dir)
                queue.put(f"Resultados exportados para: {export_dir}")
        except Exception as e:
            queue.put(f"ERRO na simulação HFSS: {e}")
            traceback.print_exc()

    def run_simulation(self):
        if self.project_path:
            thread = threading.Thread(target=self._run_hfss_simulation_thread, args=(self.project_path, self.queue),
                                      daemon=True)
            thread.start()

    def import_hfss_results(self):
        if not self.calc:
            messagebox.showwarning("Aviso", "Calcule um projeto primeiro antes de importar resultados.")
            return

        proj_dir = os.path.dirname(self.project_path) if self.project_path else None
        touchstone_file = ""

        if proj_dir and os.path.exists(proj_dir):
            proj_name = os.path.splitext(os.path.basename(self.project_path))[0]
            num_ports = self.calc.params['n_outputs'] + 1
            expected_file = os.path.join(proj_dir, f"{proj_name}.s{num_ports}p")
            if os.path.exists(expected_file):
                touchstone_file = expected_file

        if not touchstone_file:
            touchstone_file = fd.askopenfilename(
                title="Selecione o arquivo Touchstone (.sNp)",
                filetypes=[("Touchstone files", "*.s*p"), ("All files", "*.*")]
            )

        if touchstone_file and os.path.exists(touchstone_file):
            try:
                self.queue.put(f"Importando resultados de {touchstone_file}...")
                sim_net = Network(touchstone_file)
                self.calc.s_params_sim = sim_net
                self.queue.put("Resultados importados. Atualizando gráficos...")
                self.result_frame.display_results(self.calc)
            except Exception as e:
                self.queue.put(f"Erro ao importar arquivo: {e}")
                messagebox.showerror("Erro de Importação", f"Não foi possível ler o arquivo Touchstone.\n{e}")

    def export_pdf(self):
        if self.calc:
            thread = threading.Thread(target=export_full_pdf, args=(self.calc, self.queue), daemon=True)
            thread.start()

    def save_project(self):
        if self.calc:
            filepath = fd.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Project Files", "*.json")])
            if filepath:
                try:
                    with open(filepath, 'w') as f:
                        json.dump(self.calc.params, f, indent=4)
                    self.queue.put(f"Projeto salvo em {filepath}")
                except Exception as e:
                    messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o projeto.\n{e}")

    def load_project(self):
        filepath = fd.askopenfilename(filetypes=[("JSON Project Files", "*.json")])
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    params = json.load(f)
                self.param_frame.load_params(params)
                self.queue.put(f"Projeto carregado de {filepath}")
            except Exception as e:
                messagebox.showerror("Erro ao Carregar", f"Não foi possível carregar o projeto.\n{e}")

    def update_button_states(self):
        calc_done = self.calc is not None
        hfss_exported = self.project_path is not None

        self.param_frame.export_hfss_btn.configure(state="normal" if calc_done else "disabled")
        self.param_frame.run_sim_btn.configure(state="normal" if hfss_exported else "disabled")
        self.param_frame.import_res_btn.configure(state="normal" if calc_done else "disabled")
        self.param_frame.export_pdf_btn.configure(state="normal" if calc_done else "disabled")


class ParameterFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Parâmetros de Entrada", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2,
                                                                                          pady=10)

        self.entries = {}
        params_layout = {
            "Freq. Inicial (MHz):": ("f_start", "800"), "Freq. Final (MHz):": ("f_stop", "1200"),
            "D_ext Coaxial (mm):": ("d_ext", "20.0"), "Espessura Parede (mm):": ("wall_thick", "1.5"),
            "Nº de Seções (N):": ("n_sections", "4"), "Nº de Saídas (N_out):": ("n_outputs", "4")
        }

        row = 1
        for label_text, (key, default_val) in params_layout.items():
            ctk.CTkLabel(self, text=label_text).grid(row=row, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self)
            entry.insert(0, default_val)
            entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            self.entries[key] = entry
            row += 1

        ctk.CTkLabel(self, text="Material Dielétrico:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.mat_var = ctk.StringVar(value=list(SUBSTRATE_MATERIALS.keys())[0])
        self.mat_menu = ctk.CTkOptionMenu(self, values=list(SUBSTRATE_MATERIALS.keys()), variable=self.mat_var)
        self.mat_menu.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        self.calc_btn = ctk.CTkButton(self, text="Calcular", command=self._validate_and_calc, fg_color="#2aa198",
                                      hover_color="#268c84")
        self.calc_btn.grid(row=row, column=0, columnspan=2, pady=10, sticky="ew");
        row += 1

        self.export_hfss_btn = ctk.CTkButton(self, text="Exportar Modelo HFSS", command=self.app.export_hfss)
        self.export_hfss_btn.grid(row=row, column=0, columnspan=2, pady=5, sticky="ew");
        row += 1

        self.run_sim_btn = ctk.CTkButton(self, text="Executar Simulação HFSS", command=self.app.run_simulation)
        self.run_sim_btn.grid(row=row, column=0, columnspan=2, pady=5, sticky="ew");
        row += 1

        self.import_res_btn = ctk.CTkButton(self, text="Importar Resultados HFSS (.sNp)",
                                            command=self.app.import_hfss_results)
        self.import_res_btn.grid(row=row, column=0, columnspan=2, pady=5, sticky="ew");
        row += 1

        self.export_pdf_btn = ctk.CTkButton(self, text="Exportar Relatório PDF", command=self.app.export_pdf)
        self.export_pdf_btn.grid(row=row, column=0, columnspan=2, pady=5, sticky="ew");
        row += 1

        proj_frame = ctk.CTkFrame(self, fg_color="transparent")
        proj_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="ew")
        proj_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(proj_frame, text="Salvar Projeto", command=self.app.save_project).grid(row=0, column=0, padx=5,
                                                                                             sticky="ew")
        ctk.CTkButton(proj_frame, text="Carregar Projeto", command=self.app.load_project).grid(row=0, column=1,
                                                                                               padx=5,
                                                                                               sticky="ew")

    def _validate_and_calc(self):
        try:
            params = {key: float(entry.get()) for key, entry in self.entries.items()}
            params['n_sections'] = int(params['n_sections'])
            params['n_outputs'] = int(params['n_outputs'])
            params['diel_material'] = self.mat_var.get()

            if params['f_stop'] <= params['f_start']:
                raise ValueError("Frequência final deve ser maior que a inicial.")
            if params['d_ext'] <= 2 * params['wall_thick']:
                raise ValueError("Diâmetro externo deve ser maior que o dobro da espessura da parede.")
            if params['n_sections'] <= 0 or params['n_outputs'] <= 0:
                raise ValueError("Número de seções e saídas devem ser inteiros positivos.")

            self.app.calculate_and_display(params)
        except ValueError as e:
            self.app.queue.put(f"Erro de Entrada: {e}")
            messagebox.showerror("Entrada Inválida", str(e))
        except Exception as e:
            self.app.queue.put(f"Erro inesperado: {e}")
            traceback.print_exc()

    def load_params(self, params):
        for key, value in params.items():
            if key in self.entries:
                self.entries[key].delete(0, 'end')
                self.entries[key].insert(0, str(value))
            elif key == 'diel_material':
                self.mat_var.set(value)


class ResultFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, sticky="nsew")

        self.tab_view.add("Gráficos de Desempenho")
        self.tab_view.add("Parâmetros Geométricos")
        self.tab_view.add("Visualização 3D")

        self.canvas_frame = self.tab_view.tab("Gráficos de Desempenho")
        self.geo_frame = self.tab_view.tab("Parâmetros Geométricos")
        self.vis_frame = self.tab_view.tab("Visualização 3D")

        ctk.CTkLabel(self.vis_frame,
                     text="A visualização 3D é iniciada em uma janela separada.\nUse este botão para reabri-la se necessário.").pack(
            pady=20)
        ctk.CTkButton(self.vis_frame, text="Atualizar Visualização 3D", command=self.launch_3d_viewer).pack(pady=10)

    def display_results(self, calc: RFCalculator):
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        fig = calc.plot_performance()
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=1)

        for widget in self.geo_frame.winfo_children():
            widget.destroy()
        text_area = ctk.CTkTextbox(self.geo_frame, font=("Courier New", 12))
        text_area.pack(fill="both", expand=True, padx=10, pady=10)

        p, r = calc.params, calc.results
        report = "--- Parâmetros Geométricos e Elétricos ---\n\n"
        report += f"{'Parâmetro':<30} | {'Valor'}\n"
        report += "-" * 50 + "\n"
        report += f"{'Comprimento de Seção (mm)':<30} | {r['sec_len_mm']:.3f}\n"
        report += f"{'Comprimento Interno Total (mm)':<30} | {r['len_inner_mm']:.3f}\n"
        report += f"{'Diâmetro Interno do Tubo (mm)':<30} | {r['d_int_tube']:.3f}\n"
        report += f"{'Diâmetro Saída 50 Ohm (mm)':<30} | {r['d_out_50ohm']:.3f}\n\n"

        for i, (diam, z) in enumerate(zip(r['main_diams'], r['z_sects']), start=1):
            report += f"{f'Diâmetro Seção {i} (mm)':<30} | {diam:.3f}\n"
            report += f"{f'Impedância Seção {i} (Ohm)':<30} | {z:.3f}\n"

        text_area.insert("1.0", report)
        text_area.configure(state="disabled")

    def launch_3d_viewer(self):
        if self.app.calc:
            params = self.app.calc.get_geometry_for_viewer()
            thread = threading.Thread(target=launch_pyvista, args=(params, self.app.queue), daemon=True)
            thread.start()
        else:
            messagebox.showwarning("Aviso", "Nenhum cálculo foi realizado ainda.")


if __name__ == "__main__":
    app = App()
    app.mainloop()