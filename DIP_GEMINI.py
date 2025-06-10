import customtkinter as ctk
import pyvista as pv
import numpy as np
import threading, queue, math, os, traceback, json, tempfile
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import tkinter.filedialog as fd
from tkinter import messagebox
import skrf as rf
from skrf.network import Network
from skrf.frequency import Frequency
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Image as RLImage, Spacer
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from skrf.media import DistributedCircuit

# --------------------------------------------------------------------
# 1. Imports HFSS/AEDT
# --------------------------------------------------------------------
try:
    from ansys.aedt.core import Hfss, Desktop

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
    def __init__(self, params):
        self.params = params
        self.results = {}
        self.s_params_th = None
        self.s_params_sim = None
        self.project_path = ""
        self.frequencies = np.linspace(params['f_start'], params['f_stop'], 201)

    @abstractmethod
    def calculate(self):
        pass

    @abstractmethod
    def calculate_s_parameters(self):
        pass

    def get_geometry_for_viewer(self):
        return {**self.params, **self.results}

    def _get_wavelength_mm(self, f_mhz, er):
        return 299792.458 / (f_mhz * math.sqrt(er))

    def get_theoretical_network(self):
        """Cria e retorna o objeto skrf.Network para os parâmetros S teóricos."""
        if self.s_params_th is None:
            return None

        freq = Frequency.from_f(self.frequencies * 1e6, unit='Hz')
        num_ports = self.params['n_outputs'] + 1
        s_matrix = np.zeros((len(self.frequencies), num_ports, num_ports), dtype=complex)

        s_matrix[:, 0, 0] = self.s_params_th.get('S11', 0)
        s_matrix[:, 1, 1] = self.s_params_th.get('S22', 0)
        s_matrix[:, 2, 1] = self.s_params_th.get('S32', 0)

        for i in range(self.params['n_outputs']):
            s_matrix[:, i + 1, 0] = self.s_params_th.get(f'S{i + 2}1', 0)
            s_matrix[:, 0, i + 1] = self.s_params_th.get(f'S{i + 2}1', 0)  # Reciprocidade

        return Network(frequency=freq, s=s_matrix)

    def plot_performance(self):
        """
        Plota os gráficos de desempenho comparativos (Teórico vs. Simulado).
        """
        fig, axs = plt.subplots(2, 1, figsize=(10, 8))
        fig.suptitle("Análise de Desempenho", fontsize=16)

        # Gráfico 1: S11 e S21
        ax1 = axs[0]
        if self.s_params_th:
            s11_db_th = 20 * np.log10(np.abs(self.s_params_th['S11']))
            s21_db_th = 20 * np.log10(np.abs(self.s_params_th['S21']))
            ax1.plot(self.frequencies, s11_db_th, 'b-', label='S11 Teórico')
            ax1.plot(self.frequencies, s21_db_th, 'g-', label='S21 Teórico')

        if self.s_params_sim:
            s11_db_sim = 20 * np.log10(np.abs(self.s_params_sim.s[:, 0, 0]))
            s21_db_sim = 20 * np.log10(np.abs(self.s_params_sim.s[:, 1, 0]))
            ax1.plot(self.s_params_sim.f / 1e6, s11_db_sim, 'b--', label='S11 Simulado')
            ax1.plot(self.s_params_sim.f / 1e6, s21_db_sim, 'g--', label='S21 Simulado')

        ax1.set_title("Return Loss (S11) e Insertion Loss (S21)")
        ax1.set_xlabel("Frequência (MHz)")
        ax1.set_ylabel("Magnitude (dB)")
        ax1.set_ylim(-40, 0)
        ax1.grid(True)
        ax1.legend()

        # Gráfico 2: S32 (Isolação) e S22 (RL Saída)
        ax2 = axs[1]
        if self.s_params_th:
            s32_db_th = 20 * np.log10(np.abs(self.s_params_th['S32']))
            s22_db_th = 20 * np.log10(np.abs(self.s_params_th['S22']))
            ax2.plot(self.frequencies, s32_db_th, 'r-', label='Isolação (S32) Teórica')
            ax2.plot(self.frequencies, s22_db_th, 'm-', label='RL Saída (S22) Teórico')

        if self.s_params_sim and self.s_params_sim.s.shape[1] > 2:
            s32_db_sim = 20 * np.log10(np.abs(self.s_params_sim.s[:, 2, 1]))
            s22_db_sim = 20 * np.log10(np.abs(self.s_params_sim.s[:, 1, 1]))
            ax2.plot(self.s_params_sim.f / 1e6, s32_db_sim, 'r--', label='Isolação (S32) Simulada')
            ax2.plot(self.s_params_sim.f / 1e6, s22_db_sim, 'm--', label='RL Saída (S22) Simulada')

        ax2.set_title("Isolação (S32) e Return Loss da Saída (S22)")
        ax2.set_xlabel("Frequência (MHz)")
        ax2.set_ylabel("Magnitude (dB)")
        ax2.set_ylim(-40, 0)
        ax2.grid(True)
        ax2.legend()

        plt.tight_layout(rect=[0, 0, 1, 0.96])
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

        # Para saídas coaxiais, a impedância de saída é 50 Ohm.
        # A relação D/d para 50 Ohm em um dielétrico er é exp(50 * sqrt(er) / 60)
        d_out_50 = d_int_tube / math.exp(50 * math.sqrt(er) / 59.952)

        z0 = 50.0
        z_eff = 50.0 / p['n_outputs']
        z_sects = [z0 * (z_eff / z0) ** ((2 * i - 1) / (2 * p['n_sections'])) for i in range(1, p['n_sections'] + 1)]
        main_diams = [d_int_tube / math.exp(z_i * math.sqrt(er) / 59.952) for z_i in z_sects]

        self.results = {
            'sec_len_mm': sec_len,
            'len_inner_mm': len_inner,
            'len_outer_mm': len_outer,
            'd_int_tube': d_int_tube,
            'main_diams': main_diams,
            'd_out_50ohm': d_out_50,
            'z_sects': z_sects
        }
        self.calculate_s_parameters()
        return True

    def calculate_s_parameters(self):
        p = self.params
        N_freq = len(self.frequencies)
        freqs_hz = self.frequencies * 1e6
        fr = Frequency.from_f(freqs_hz, unit='Hz')
        num_ports = p['n_outputs'] + 1

        # 1.1. S11 (Return Loss de Entrada)
        media = DistributedCircuit(frequency=fr, z0=50)
        ntw_cascade = media.line(0, 'm')  # Inicia com uma linha de comprimento zero
        for z_val in self.results['z_sects']:
            sec_media = DistributedCircuit(frequency=fr, z0=z_val)
            sec_ntw = sec_media.line(self.results['sec_len_mm'] / 1000.0, 'm')
            ntw_cascade = ntw_cascade ** sec_ntw

        load_ntw = media.resistor(p['n_outputs'] * 50)  # Carga efetiva
        final_ntw = ntw_cascade ** load_ntw
        s11 = final_ntw.s[:, 0, 0]

        # 1.2. S21 (Insertion Loss)
        Gamma = s11
        mismatch_loss_db = -10 * np.log10(1 - np.abs(Gamma) ** 2)
        ideal_split_loss_db = 10 * np.log10(p['n_outputs'])
        s21_db = -(mismatch_loss_db + ideal_split_loss_db)
        s21 = 10 ** (s21_db / 20) * np.exp(
            -1j * 2 * np.pi * freqs_hz * (self.results['len_inner_mm'] / 1000) / (299792458 / np.sqrt(p['d_ext'])))

        # 1.3. S22 (Return Loss de Saída)
        # Modelo simplificado: a impedância vista para trás é complexa.
        # Por simplicidade inicial, vamos modelar como se visse o transformador ao contrário
        # terminando na fonte de 50 Ohm. Esta é uma aproximação.
        s22 = s11

        # 1.4. S32 (Isolação)
        # Modelo ideal: potência entrando na porta 2 se divide entre a porta 1 e as outras N-1 saídas.
        # A potência indo para outra porta de saída (ex: 3) é P_in / (N-1)
        # Isso é uma grande simplificação. Para divisores reativos, a isolação é baixa.
        # Vamos assumir um valor fixo baixo, pois a teoria é complexa.
        isolation_db = -6  # Valor típico para um T-junction reativo
        s32 = 10 ** (isolation_db / 20) * np.ones(N_freq)

        self.s_params_th = {f'S{i + 2}1': s21 for i in range(p['n_outputs'])}
        self.s_params_th['S11'] = s11
        self.s_params_th['S22'] = s22
        self.s_params_th['S32'] = s32

        return True


# --------------------------------------------------------------------
# 7. Funções de Visualização e Automação (PyVista, HFSS, PDF)
# --------------------------------------------------------------------
def add_cota(plotter, p1, p2, txt, off_dir=np.array([0, 1, 0])):
    p1, p2 = np.array(p1), np.array(p2)
    d = np.linalg.norm(p2 - p1)
    if d < 1e-6: return
    mid = (p1 + p2) / 2
    off = 0.15 * d + 5
    e1, e2 = p1 + off * off_dir, p2 + off * off_dir
    plotter.add_lines(np.vstack((p1, e1)), color='white', width=2)
    plotter.add_lines(np.vstack((p2, e2)), color='white', width=2)
    plotter.add_lines(np.vstack((e1, e2)), color='yellow', width=3)
    plotter.add_point_labels([mid + off_dir * (off + 3)], [txt], font_size=16, text_color='cyan', always_visible=True)


def create_coaxial_geometry(p):
    plotter = pv.Plotter(window_size=(900, 600), title="Visualização 3D do Divisor Coaxial")
    diel = pv.Cylinder(center=(0, 0, p['len_outer_mm'] / 2), direction=(0, 0, 1), radius=p['d_int_tube'] / 2,
                       height=p['len_outer_mm'])
    plotter.add_mesh(diel, color='#788cb4', opacity=0.15)

    current_z = 0
    for i, di in enumerate(p['main_diams']):
        cyl = pv.Cylinder(center=(0, 0, current_z + p['sec_len_mm'] / 2), direction=(0, 0, 1), radius=di / 2,
                          height=p['sec_len_mm'])
        plotter.add_mesh(cyl, color='gold', opacity=1.0, name=f"section_{i}")
        current_z += p['sec_len_mm']

    out_len = p['d_int_tube'] * 1.5
    z0 = p['len_inner_mm']
    for k in range(p['n_outputs']):
        ang = math.radians(360 * k / p['n_outputs'])
        x, y = math.cos(ang), math.sin(ang)
        ori = (x * out_len / 4, y * out_len / 4, z0)
        od = pv.Cylinder(center=ori, direction=(x, y, 0), radius=p['d_int_tube'] / 2, height=out_len / 2)
        oi = pv.Cylinder(center=ori, direction=(x, y, 0), radius=p['d_out_50ohm'] / 2, height=out_len / 2)
        plotter.add_mesh(od, color='#1f77b4', opacity=0.6)
        plotter.add_mesh(oi, color='gold', opacity=1.0)

    # Cotas
    add_cota(plotter, [0, 0, 0], [0, 0, p['len_outer_mm']], f"L_ext={p['len_outer_mm']:.2f} mm")
    return plotter


def launch_pyvista(params, q):
    try:
        plotter = create_coaxial_geometry(params)
        plotter.show()
        q.put("Visualização 3D fechada.")
    except Exception as e:
        q.put(f"Erro na visualização 3D: {e}")
        traceback.print_exc()


def generate_hfss_model(params, status_queue):
    if not HFSS_AVAILABLE:
        status_queue.put("ERRO: Módulo ansys-aedt-core não disponível.")
        return None
    try:
        status_queue.put("Iniciando geração do script HFSS...")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        proj_name = f"Divisor_Coaxial_{ts}"

        # Usar um diretório temporário ou um diretório de projetos
        project_dir = os.path.join(os.getcwd(), "HFSS_Projects")
        os.makedirs(project_dir, exist_ok=True)
        project_path = os.path.join(project_dir, f"{proj_name}.aedt")

        with Hfss(projectname=project_path, designname="DivisorCoaxial", solution_type="DrivenModal",
                  new_desktop_session=True, close_on_exit=False) as hfss:
            vm = hfss.variable_manager
            mdl = hfss.modeler
            mdl.model_units = "mm"

            # Parametrização
            vm["d_int_tube"] = f"{params['d_int_tube']}mm"
            vm["sec_len"] = f"{params['sec_len_mm']}mm"
            vm["n_sec"] = f"{params['n_sections']}"
            vm["len_inner"] = f"n_sec * sec_len"
            vm["d_out_50"] = f"{params['d_out_50ohm']}mm"
            for i, d in enumerate(params['main_diams']):
                vm[f"d_sec{i + 1}"] = f"{d}mm"

            # Geometria
            diel = mdl.create_cylinder("Z", [0, 0, 0], "d_int_tube/2", "len_inner * 1.05", name="Dielétrico")

            inner_parts = []
            for i in range(params['n_sections']):
                part = mdl.create_cylinder("Z", [0, 0, f"{i}*sec_len"], f"d_sec{i + 1}/2", "sec_len",
                                           name=f"Sec_{i + 1}")
                inner_parts.append(part.name)

            mdl.unite(inner_parts, name="Condutor_Central")

            # Materiais
            er, tand = SUBSTRATE_MATERIALS[params['diel_material']]
            mat_name = params['diel_material'].replace(' ', '_').replace('(', '').replace(')', '')
            if not hfss.materials.does_material_exist(mat_name):
                hfss.materials.add_material(mat_name, permittivity=er, dielectric_loss_tangent=tand)
            diel.material_name = mat_name
            mdl["Condutor_Central"].material_name = "pec"

            # Portas
            # (Simplificado - uma implementação real necessitaria de mais detalhes)
            face_in = mdl.get_object_faces(diel.name)[0]  # Suposição
            hfss.create_wave_port_from_sheet(face_in, port_name="P1")

            # Setup & Sweep
            setup = hfss.create_setup("Setup1")
            setup.props["Frequency"] = f"{(params['f_start'] + params['f_stop']) / 2000}GHz"
            setup.props["MaximumPasses"] = 10
            setup.props["MaxDeltaS"] = 0.02

            sweep = setup.create_linear_count_sweep(
                unit="MHz",
                freqstart=params['f_start'],
                freqstop=params['f_stop'],
                num_points=101,
                sweepname="Sweep1",
                save_fields=False,
                sweep_type="Interpolating"
            )

            hfss.save_project()
            status_queue.put(f"Projeto HFSS salvo em: {project_path}")
            return project_path
    except Exception as e:
        status_queue.put(f"ERRO na geração HFSS: {e}")
        traceback.print_exc()
        return None


def run_hfss_simulation(project_path, queue):
    if not HFSS_AVAILABLE or not project_path:
        queue.put("ERRO: Simulação HFSS não pode ser iniciada.")
        return
    try:
        queue.put("Iniciando simulação HFSS...")
        with Hfss(projectname=project_path, new_desktop_session=False) as hfss:
            queue.put("Analisando o setup 'Setup1'...")
            hfss.analyze_setup("Setup1")
            queue.put("Simulação HFSS concluída.")
            # Exportar resultados automaticamente
            export_dir = os.path.dirname(project_path)
            hfss.export_touchstone("Setup1", "Sweep1", export_dir)
            queue.put(f"Resultados exportados para: {export_dir}")
    except Exception as e:
        queue.put(f"ERRO na simulação HFSS: {e}")
        traceback.print_exc()


def export_full_pdf(calc: RFCalculator, queue: queue.Queue):
    pdf_path = fd.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
    if not pdf_path:
        queue.put("Exportação de PDF cancelada.")
        return

    queue.put("Gerando PDF...")
    with tempfile.TemporaryDirectory() as tempdir:
        # Imagem 3D
        img3d_path = os.path.join(tempdir, "view3d.png")
        pv_plot = create_coaxial_geometry(calc.get_geometry_for_viewer())
        pv_plot.screenshot(img3d_path, window_size=(1200, 800), off_screen=True)
        pv_plot.close()

        # Gráfico de Performance
        img_perf_path = os.path.join(tempdir, "performance.png")
        fig = calc.plot_performance()
        fig.savefig(img_perf_path, dpi=150)
        plt.close(fig)

        # Tabela de parâmetros
        p, r = calc.params, calc.results
        data = [["Parâmetro", "Valor"]]
        data.extend([
            ["Frequência Inicial (MHz)", f"{p['f_start']:.2f}"],
            ["Frequência Final (MHz)", f"{p['f_stop']:.2f}"],
            ["Diâmetro Externo (mm)", f"{p['d_ext']:.3f}"],
            ["Espessura da Parede (mm)", f"{p['wall_thick']:.3f}"],
            ["Número de Seções", f"{p['n_sections']}"],
            ["Número de Saídas", f"{p['n_outputs']}"],
            ["Material Dielétrico", p['diel_material']],
            ["Comprimento de Seção (mm)", f"{r['sec_len_mm']:.3f}"],
            ["Comprimento Interno (mm)", f"{r['len_inner_mm']:.3f}"],
        ])
        for i, (diam, z) in enumerate(zip(r['main_diams'], r['z_sects']), start=1):
            data.append([f"Diâmetro Seção {i} (mm)", f"{diam:.3f}"])
            data.append([f"Impedância Seção {i} (Ohm)", f"{z:.3f}"])

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = [Paragraph("Relatório de Análise - Divisor Coaxial Chebyshev", styles['Title']), Spacer(1, 12)]
        elements.append(RLImage(img3d_path, width=400, height=267))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Gráficos de Desempenho", styles['h2']))
        elements.append(RLImage(img_perf_path, width=500, height=400))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Parâmetros Geométricos e Elétricos", styles['h2']))

        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)

        doc.build(elements)
        queue.put(f"PDF salvo em: {pdf_path}")


# --------------------------------------------------------------------
# 10. GUI CTk
# --------------------------------------------------------------------
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

    def run_simulation(self):
        if self.project_path:
            thread = threading.Thread(target=run_hfss_simulation, args=(self.project_path, self.queue), daemon=True)
            thread.start()

    def import_hfss_results(self):
        if not self.calc:
            messagebox.showwarning("Aviso", "Calcule um projeto primeiro antes de importar resultados.")
            return

        filepath = fd.askopenfilename(
            title="Selecione o arquivo Touchstone (.sNp)",
            filetypes=[("Touchstone files", "*.s*p"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.queue.put(f"Importando resultados de {filepath}...")
                sim_net = Network(filepath)
                self.calc.s_params_sim = sim_net
                self.queue.put("Resultados importados. Atualizando gráficos...")
                self.result_frame.display_results(self.calc)  # Atualiza a exibição com os novos dados
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

        # Título
        ctk.CTkLabel(self, text="Parâmetros de Entrada", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2,
                                                                                          pady=10)

        # Entradas
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

        # Menu de Material
        ctk.CTkLabel(self, text="Material Dielétrico:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        self.mat_var = ctk.StringVar(value=list(SUBSTRATE_MATERIALS.keys())[0])
        self.mat_menu = ctk.CTkOptionMenu(self, values=list(SUBSTRATE_MATERIALS.keys()), variable=self.mat_var)
        self.mat_menu.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        # Botões de Ação
        self.calc_btn = ctk.CTkButton(self, text="Calcular", command=self._validate_and_calc, fg_color="#2aa198",
                                      hover_color="#268c84")
        self.calc_btn.grid(row=row, column=0, columnspan=2, pady=10, sticky="ew");
        row += 1

        self.export_hfss_btn = ctk.CTkButton(self, text="Exportar Script HFSS", command=self.app.export_hfss)
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

        # Salvar/Carregar Projeto
        proj_frame = ctk.CTkFrame(self, fg_color="transparent")
        proj_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="ew")
        proj_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(proj_frame, text="Salvar Projeto", command=self.app.save_project).grid(row=0, column=0, padx=5,
                                                                                             sticky="ew")
        ctk.CTkButton(proj_frame, text="Carregar Projeto", command=self.app.load_project).grid(row=0, column=1, padx=5,
                                                                                               sticky="ew")

    def _validate_and_calc(self):
        try:
            params = {key: float(entry.get()) for key, entry in self.entries.items()}
            params['n_sections'] = int(params['n_sections'])
            params['n_outputs'] = int(params['n_outputs'])
            params['diel_material'] = self.mat_var.get()

            # Validação
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
        # Aba de Gráficos
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        fig = calc.plot_performance()
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=1)

        # Aba de Geometria
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