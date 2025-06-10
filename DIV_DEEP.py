import customtkinter as ctk
import pyvista as pv
import numpy as np
import threading, queue, math, os, traceback, json
import tempfile
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import tkinter.filedialog as fd
import skrf as rf
from skrf.network import Network
from skrf.frequency import Frequency
from skrf.plotting import plot_s_smith
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Image as RLImage, Spacer
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from pyvistaqt import BackgroundPlotter

from skrf.media.distributedCircuit import DistributedCircuit

# --------------------------------------------------------------------
# 1. Imports HFSS/AEDT
# --------------------------------------------------------------------
try:
    from ansys.aedt.core import Hfss, Desktop

    HFSS_AVAILABLE = True
except ImportError:
    HFSS_AVAILABLE = False
    print("ansys-aedt-core não encontrado. HFSS desativado.")

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
COAX_CONNECTORS = ["SMA", "N-Type", "BNC"]


# --------------------------------------------------------------------
# 5. Classe Base de Cálculo
# --------------------------------------------------------------------
class RFCalculator(ABC):
    def __init__(self, params):
        self.params = params
        self.results = {}
        self.s_params = {}
        # Frequências em MHz
        self.frequencies = np.linspace(params['f_start'], params['f_stop'], 201)
        self.sim_ntw = None  # Armazenar resultados de simulação

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

    def theoretical_return_loss(self):
        """
        Calcula S11 teórico como cascata de seções λ/4 Chebyshev usando
        DistributedCircuit para cada impedância de seção.
        """
        p = self.params
        # Frequências em Hz
        freqs = self.frequencies * 1e6
        fr = Frequency.from_f(freqs, unit='Hz')

        # Comprimento de seção λ/4 em metros
        sec_len_m = self.results['sec_len_mm'] / 1000.0

        # Impedâncias de cada seção (Chebyshev)
        z0 = 50.0
        z_eff = 50.0 / p['n_outputs']
        Zs = [
            z0 * (z_eff / z0) ** ((2 * i - 1) / (2 * p['n_sections']))
            for i in range(1, p['n_sections'] + 1)
        ]

        # Monte a rede em cascata
        ntw = None
        for Z in Zs:
            # Use DistributedCircuit para criar um segmento de linha de comprimento λ/4
            media = DistributedCircuit(frequency=fr, z0=Z)
            seg = media.line(sec_len_m, unit='m')
            if ntw is None:
                ntw = seg
            else:
                ntw = ntw ** seg

        # S11 ante terminador de 50Ω
        return ntw.s[:, 0, 0]

    def import_simulation_results(self, filepath):
        """Carrega resultados de simulação de arquivo Touchstone"""
        try:
            self.sim_ntw = Network(filepath)
            return True
        except Exception as e:
            print(f"Erro ao importar resultados: {e}")
            return False

    def plot_performance(self, sim_data=False):
        n_ports = self.params['n_outputs'] + 1

        # Criar figura com 2 subplots
        fig, axs = plt.subplots(2, 1, figsize=(10, 10))
        fig.suptitle("Desempenho do Divisor", fontsize=16)

        # Plot 1: Return Loss e Insertion Loss
        ax = axs[0]

        # Dados teóricos
        s11_th = self.s_params['S11']
        ax.plot(self.frequencies, 20 * np.log10(np.abs(s11_th)),
                'b-', label='S11 Teórico')

        # Insertion Loss (S21, S31, ...)
        for port in range(2, n_ports + 1):
            s_param = self.s_params[f'S{port}1']
            ax.plot(self.frequencies, 20 * np.log10(np.abs(s_param)),
                    f'C{port - 1}-', label=f'S{port}1 Teórico')

        # Dados simulados se disponíveis
        if sim_data and self.sim_ntw:
            freq_ghz = self.frequencies / 1000  # Converter MHz para GHz

            # S11 simulado
            s11_sim = self.sim_ntw.s[:, 0, 0]
            ax.plot(freq_ghz, 20 * np.log10(np.abs(s11_sim)),
                    'b--', label='S11 Simulado')

            # Insertion Loss simulado
            for port in range(2, n_ports + 1):
                s_param_sim = self.sim_ntw.s[:, port - 1, 0]
                ax.plot(freq_ghz, 20 * np.log10(np.abs(s_param_sim)),
                        f'C{port - 1}--', label=f'S{port}1 Simulado')

        ax.set(title="Return Loss e Insertion Loss",
               xlabel="Frequência (MHz)",
               ylabel="Magnitude (dB)")
        ax.grid(True)
        ax.legend()

        # Plot 2: Isolação e Return Loss de Saída
        ax = axs[1]

        # Isolação teórica (S32)
        if n_ports >= 3:
            s32_th = self.s_params['S32']
            ax.plot(self.frequencies, 20 * np.log10(np.abs(s32_th)),
                    'r-', label='Isolação (S32) Teórica')

        # Return Loss de saída (S22)
        s22_th = self.s_params['S22']
        ax.plot(self.frequencies, 20 * np.log10(np.abs(s22_th)),
                'g-', label='S22 Teórico')

        # Dados simulados se disponíveis
        if sim_data and self.sim_ntw:
            # Isolação simulada
            if n_ports >= 3:
                s32_sim = self.sim_ntw.s[:, 2, 1]  # S32
                ax.plot(freq_ghz, 20 * np.log10(np.abs(s32_sim)),
                        'r--', label='Isolação (S32) Simulada')

            # Return Loss de saída simulado
            s22_sim = self.sim_ntw.s[:, 1, 1]  # S22
            ax.plot(freq_ghz, 20 * np.log10(np.abs(s22_sim)),
                    'g--', label='S22 Simulado')

        ax.set(title="Isolação e Return Loss de Saída",
               xlabel="Frequência (MHz)",
               ylabel="Magnitude (dB)")
        ax.grid(True)
        ax.legend()

        plt.tight_layout(rect=[0, 0, 1, 0.95])
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
        d_out_50 = d_int_tube / 2.3

        # impedâncias Chebyshev
        z0 = 50.0
        z_eff = 50.0 / p['n_outputs']
        z_sects = [
            z0 * (z_eff / z0) ** ((2 * i - 1) / (2 * p['n_sections']))
            for i in range(1, p['n_sections'] + 1)
        ]
        main_diams = [
            d_int_tube / math.exp(z_i * math.sqrt(er) / 59.952)
            for z_i in z_sects
        ]

        self.results = {
            'sec_len_mm': sec_len,
            'len_inner_mm': len_inner,
            'len_outer_mm': len_outer,
            'd_int_tube': d_int_tube,
            'main_diams': main_diams,
            'd_out_50ohm': d_out_50,
            'n_outputs': p['n_outputs']
        }
        self.calculate_s_parameters()
        return True

    def calculate_s_parameters(self):
        n_freq = len(self.frequencies)
        n_ports = self.params['n_outputs'] + 1

        # Calcular S11 teórico
        s11 = self.theoretical_return_loss()
        gamma = np.abs(s11)  # Magnitude do coeficiente de reflexão

        # Calcular Insertion Loss com mismatch
        ideal_loss = 10 * np.log10(self.params['n_outputs'])
        mismatch_loss = -10 * np.log10(1 - gamma ** 2)
        insertion_loss = ideal_loss + mismatch_loss

        # Converter para magnitude complexa (assumindo fase zero)
        s21_mag = 10 ** (insertion_loss / 20)

        # Inicializar matriz S
        self.s_params = {}
        s_matrix = np.zeros((n_freq, n_ports, n_ports), dtype=complex)

        # Preencher matriz S
        for i in range(n_freq):
            # Porta 1 (entrada)
            s_matrix[i, 0, 0] = s11[i]  # S11

            # Insertion Loss para portas de saída
            for port in range(2, n_ports + 1):
                s_matrix[i, port - 1, 0] = s21_mag[i]  # S21, S31, ...
                s_matrix[i, 0, port - 1] = s21_mag[i]  # Reciprocidade

            # Portas de saída
            for j in range(1, n_ports):
                # Return Loss de saída (modelo simplificado)
                s_matrix[i, j, j] = 0.01  # -40 dB aproximado

                # Isolação entre saídas
                for k in range(j + 1, n_ports):
                    s_matrix[i, j, k] = 0.001  # -60 dB aproximado
                    s_matrix[i, k, j] = 0.001  # Simetria

        # Popular dicionário de parâmetros S
        for i in range(n_ports):
            for j in range(n_ports):
                key = f'S{i + 1}{j + 1}'
                self.s_params[key] = s_matrix[:, i, j]

        return True


# --------------------------------------------------------------------
# 7. Visualização 3D com PyVistaQt
# --------------------------------------------------------------------
def create_coaxial_geometry(p):
    plotter = BackgroundPlotter(title="Coaxial 3D")
    # dielétrico interno
    diel = pv.Cylinder(center=(0, 0, p['len_outer_mm'] / 2),
                       direction=(0, 0, 1),
                       radius=p['d_int_tube'] / 2,
                       height=p['len_outer_mm'])
    plotter.add_mesh(diel, color='#788cb4', opacity=0.15)
    # seções
    for i, di in enumerate(p['main_diams']):
        cyl = pv.Cylinder(center=(0, 0, i * p['sec_len_mm'] + p['sec_len_mm'] / 2),
                          direction=(0, 0, 1),
                          radius=di / 2,
                          height=p['sec_len_mm'])
        plotter.add_mesh(cyl, color='gold', opacity=1.0)
    # saídas
    out_len = p['d_int_tube'] * 1.5
    z0 = p['len_inner_mm']
    for k in range(p['n_outputs']):
        ang = math.radians(360 * k / p['n_outputs'])
        x, y = math.cos(ang), math.sin(ang)
        ori = (x * out_len / 2, y * out_len / 2, z0)
        od = pv.Cylinder(center=ori, direction=(x, y, 0),
                         radius=p['d_int_tube'] / 2, height=out_len)
        oi = pv.Cylinder(center=ori, direction=(x, y, 0),
                         radius=p['d_out_50ohm'] / 2, height=out_len)
        plotter.add_mesh(od, color='#1f77b4', opacity=0.6)
        plotter.add_mesh(oi, color='gold', opacity=1.0)
    return plotter


# --------------------------------------------------------------------
# 8. Geração e Simulação HFSS
# --------------------------------------------------------------------
def generate_hfss_model(params, status_queue):
    if not HFSS_AVAILABLE:
        status_queue.put("ERRO: módulo HFSS não disponível.")
        return None

    try:
        status_queue.put("Iniciando geração HFSS...")

        # Projeto/Design
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        proj_name = f"Div_Coaxial_{ts}"
        desktop = Desktop(version="2022.2", new_desktop=True)
        hfss = Hfss(project=proj_name, design=proj_name, solution_type="Modal")

        # ... (código existente para geração do modelo) ...

        # Salva projeto
        os.makedirs("HFSS_Projects", exist_ok=True)
        path = os.path.abspath(f"HFSS_Projects/{proj_name}.aedt")
        hfss.save_project(path)

        status_queue.put(f"HFSS salvo em: {path}")
        return path  # Retorna caminho para execução

    except Exception as e:
        status_queue.put(f"ERRO HFSS: {e}")
        traceback.print_exc()
        return None


def run_hfss_simulation(project_path, status_queue):
    try:
        status_queue.put("Iniciando simulação HFSS...")
        desktop = Desktop(version="2022.2")
        hfss = Hfss(project=project_path)
        hfss.analyze_setup("Setup1")

        # Exportar resultados S-parameters
        touchstone_path = project_path.replace(".aedt", ".s{}p".format(hfss.odesign.GetNumPorts()))
        hfss.export_touchstone(solution_name="Setup1 : Sweep1",
                               file_name=touchstone_path,
                               variations=[],
                               variation_prefix="")

        status_queue.put(f"Simulação completa! Resultados em: {touchstone_path}")
        return touchstone_path

    except Exception as e:
        status_queue.put(f"ERRO simulação HFSS: {e}")
        traceback.print_exc()
        return None


# --------------------------------------------------------------------
# 9. Exportação PDF com arquivos temporários
# --------------------------------------------------------------------
def export_full_pdf(calc: RFCalculator, queue: queue.Queue):
    pdf_path = fd.asksaveasfilename(defaultextension=".pdf",
                                    filetypes=[("PDF", "*.pdf")])
    if not pdf_path: return

    # Criar arquivos temporários seguros
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp3d, \
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpplt, \
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpsmith:

        tmp3d_path = tmp3d.name
        tmpplt_path = tmpplt.name
        tmpsmith_path = tmpsmith.name

        # Renderizar 3D
        pv_plot = create_coaxial_geometry(calc.get_geometry_for_viewer())
        pv_plot.screenshot(tmp3d_path, window_size=(1200, 800))
        pv_plot.close()

        # Gráficos de desempenho
        fig = calc.plot_performance(sim_data=(calc.sim_ntw is not None))
        fig.savefig(tmpplt_path, dpi=150)
        plt.close(fig)

        # Smith chart
        freqs = calc.frequencies * 1e6
        ntw = Network()
        ntw.frequency = Frequency.from_f(freqs, 'Hz')
        ntw.s = np.zeros((len(freqs), 2, 2), dtype=complex)
        ntw.s[:, 0, 0] = calc.s_params['S11']
        fig_s = plt.figure(figsize=(4, 4))
        ax_s = fig_s.add_subplot(1, 1, 1)
        plot_s_smith(ntw, ax=ax_s)
        fig_s.savefig(tmpsmith_path, dpi=150)
        plt.close(fig_s)

        # Gerar PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elems = [
            Paragraph("Relatório Divisor Coaxial", styles['Title']),
            Spacer(1, 12),
            RLImage(tmp3d_path, width=400, height=400 * 800 / 1200), Spacer(1, 12),
            RLImage(tmpplt_path, width=400, height=300), Spacer(1, 12),
            RLImage(tmpsmith_path, width=300, height=300), Spacer(1, 12)
        ]

        # Tabela de parâmetros
        p, r = calc.params, calc.results
        data = [["Parâmetro", "Valor"]]
        data += [
            ["F.Inicial (MHz)", p['f_start']],
            ["F.Final   (MHz)", p['f_stop']],
            ["d_int_tube (mm)", r['d_int_tube']],
            ["d_out_50ohm (mm)", r['d_out_50ohm']],
            ["sec_len_mm (mm)", r['sec_len_mm']],
            ["len_inner_mm (mm)", r['len_inner_mm']],
            ["len_outer_mm (mm)", r['len_outer_mm']],
        ]
        for i, di in enumerate(r['main_diams'], start=1):
            data.append([f"di{i} (mm)", di])

        tbl = Table(data, colWidths=[200, 200])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elems.append(tbl)

        doc.build(elems)
        queue.put(f"PDF salvo em: {pdf_path}")

    # Limpeza segura
    for path in [tmp3d_path, tmpplt_path, tmpsmith_path]:
        try:
            os.remove(path)
        except:
            pass


# --------------------------------------------------------------------
# 10. GUI Aprimorada
# --------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Divisor Coaxial RF")
        self.geometry("1400x900")
        self.queue = queue.Queue()
        self.calc = None
        self.hfss_project_path = None
        self.hfss_results_path = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        nb = ctk.CTkTabview(self);
        nb.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        nb.add("Parâmetros");
        nb.add("Resultados")

        self.param_frame = ParameterFrame(nb.tab("Parâmetros"), self)
        self.param_frame.pack(fill="both", expand=True)
        self.result_frame = ResultFrame(nb.tab("Resultados"), self)
        self.result_frame.pack(fill="both", expand=True)

        self.status = ctk.CTkLabel(self, text="Pronto.", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.after(100, self._process_queue)
        self._update_button_states()

    def _process_queue(self):
        try:
            msg = self.queue.get_nowait()
            self.status.configure(text=msg)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._process_queue)

    def _update_button_states(self):
        calc_done = self.calc is not None
        hfss_exported = self.hfss_project_path is not None

        self.result_frame.export_hfss_btn.configure(state="normal" if calc_done else "disabled")
        self.result_frame.export_pdf_btn.configure(state="normal" if calc_done else "disabled")
        self.result_frame.run_hfss_btn.configure(state="normal" if hfss_exported else "disabled")
        self.result_frame.import_results_btn.configure(state="normal")

    def calculate_and_display(self, params):
        self.calc = CoaxialCalculator(params)
        self.queue.put("Calculando parâmetros...")
        if self.calc.calculate():
            self.result_frame.show(self.calc)
            self._update_button_states()
        else:
            self.queue.put("Erro no cálculo")

    def export_hfss(self):
        if self.calc:
            def hfss_thread():
                self.hfss_project_path = generate_hfss_model(
                    self.calc.get_geometry_for_viewer(),
                    self.queue
                )
                self._update_button_states()

            threading.Thread(target=hfss_thread, daemon=True).start()

    def run_hfss_simulation(self):
        if self.hfss_project_path:
            def simulation_thread():
                self.hfss_results_path = run_hfss_simulation(
                    self.hfss_project_path,
                    self.queue
                )
                if self.hfss_results_path and self.calc:
                    self.calc.import_simulation_results(self.hfss_results_path)
                    self.result_frame.show(self.calc)  # Atualiza gráficos

            threading.Thread(target=simulation_thread, daemon=True).start()

    def import_results(self):
        filepath = fd.askopenfilename(
            filetypes=[("Touchstone files", "*.s*p"), ("All files", "*.*")]
        )
        if filepath and self.calc:
            if self.calc.import_simulation_results(filepath):
                self.queue.put(f"Resultados importados: {filepath}")
                self.result_frame.show(self.calc)
            else:
                self.queue.put("Falha ao importar resultados")

    def export_pdf(self):
        if self.calc:
            threading.Thread(
                target=export_full_pdf,
                args=(self.calc, self.queue),
                daemon=True
            ).start()

    def save_project(self):
        if not self.calc:
            return

        filepath = fd.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if filepath:
            data = {
                'params': self.calc.params,
                'results': self.calc.results
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            self.queue.put(f"Projeto salvo: {filepath}")

    def load_project(self):
        filepath = fd.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self.param_frame.load_values(data['params'])
                self.calculate_and_display(data['params'])
                self.queue.put(f"Projeto carregado: {filepath}")
            except Exception as e:
                self.queue.put(f"Erro ao carregar: {e}")


class ParameterFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(self, text="Configuração Coaxial RF", font=("Arial", 18, "bold")) \
            .grid(row=0, column=0, columnspan=4, pady=(0, 20))

        # ... (campos de entrada existentes) ...

        # Botões adicionais
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=6, column=0, columnspan=4, pady=10, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frame, text="Salvar Projeto",
                      command=self.app.save_project).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="Carregar Projeto",
                      command=self.app.load_project).grid(row=0, column=1, padx=5)
        ctk.CTkButton(self, text="Calcular & 3D",
                      command=self._calc,
                      fg_color="#2aa198", hover_color="#268c84") \
            .grid(row=5, column=0, columnspan=4, pady=20, sticky="ew")

    def _calc(self):
        try:
            # Validação de entrada
            f_start = float(self.f_start.get())
            f_stop = float(self.f_stop.get())
            if f_stop <= f_start:
                raise ValueError("Frequência final deve ser maior que inicial")

            d_ext = float(self.d_ext.get())
            wall_thick = float(self.wall.get())
            if d_ext <= 2 * wall_thick:
                raise ValueError("D_externo deve ser maior que 2x espessura da parede")

            n_sec = int(self.n_sec.get())
            n_out = int(self.n_out.get())
            if n_sec <= 0 or n_out <= 0:
                raise ValueError("Número de seções/saídas deve ser positivo")

            params = {
                'topology': Topology.COAXIAL,
                'f_start': f_start,
                'f_stop': f_stop,
                'd_ext': d_ext,
                'wall_thick': wall_thick,
                'n_sections': n_sec,
                'n_outputs': n_out,
                'diel_material': self.mat_var.get()
            }
            self.app.calculate_and_display(params)
        except Exception as e:
            self.app.queue.put(f"Erro entrada: {e}")
            traceback.print_exc()

    def load_values(self, params):
        self.f_start.delete(0, 'end')
        self.f_start.insert(0, str(params['f_start']))
        self.f_stop.delete(0, 'end')
        self.f_stop.insert(0, str(params['f_stop']))
        self.d_ext.delete(0, 'end')
        self.d_ext.insert(0, str(params['d_ext']))
        self.wall.delete(0, 'end')
        self.wall.insert(0, str(params['wall_thick']))
        self.n_sec.delete(0, 'end')
        self.n_sec.insert(0, str(params['n_sections']))
        self.n_out.delete(0, 'end')
        self.n_out.insert(0, str(params['n_outputs']))
        self.mat_var.set(params['diel_material'])


class ResultFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        # Layout principal com abas
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        # Aba 1: Gráficos de Desempenho
        self.plot_tab = self.tab_view.add("Gráficos de Desempenho")
        self.plot_tab.grid_rowconfigure(0, weight=1)
        self.plot_tab.grid_columnconfigure(0, weight=1)
        self.plot_frame = ctk.CTkFrame(self.plot_tab)
        self.plot_frame.pack(fill="both", expand=True)

        # Aba 2: Parâmetros Geométricos
        self.param_tab = self.tab_view.add("Parâmetros Geométricos")
        self.param_frame = ctk.CTkScrollableFrame(self.param_tab)
        self.param_frame.pack(fill="both", expand=True)

        # Aba 3: Modelo 3D
        self.model_tab = self.tab_view.add("Modelo 3D")
        self.model_tab.grid_rowconfigure(0, weight=1)
        self.model_tab.grid_columnconfigure(0, weight=1)
        self.model_frame = ctk.CTkFrame(self.model_tab)
        self.model_frame.pack(fill="both", expand=True)
        self.viz_3d_btn = ctk.CTkButton(self.model_frame, text="Atualizar Visualização 3D",
                                        command=self.launch_3d_viewer)
        self.viz_3d_btn.pack(pady=10)

        # Botões de ação
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        self.export_hfss_btn = ctk.CTkButton(
            btn_frame, text="Exportar HFSS", command=app.export_hfss)
        self.export_hfss_btn.pack(side="left", padx=5)

        self.run_hfss_btn = ctk.CTkButton(
            btn_frame, text="Executar Simulação HFSS",
            command=app.run_hfss_simulation)
        self.run_hfss_btn.pack(side="left", padx=5)

        self.import_results_btn = ctk.CTkButton(
            btn_frame, text="Importar Resultados HFSS",
            command=app.import_results)
        self.import_results_btn.pack(side="left", padx=5)

        self.export_pdf_btn = ctk.CTkButton(
            btn_frame, text="Exportar PDF", command=app.export_pdf)
        self.export_pdf_btn.pack(side="right", padx=5)

    def show(self, calc: RFCalculator):
        # Limpar conteúdo anterior
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        for widget in self.param_frame.winfo_children():
            widget.destroy()

        # Atualizar gráficos
        fig = calc.plot_performance(sim_data=(calc.sim_ntw is not None))
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Atualizar parâmetros geométricos
        p, r = calc.params, calc.results
        tbl = [
            ("Parâmetro", "Valor"),
            ("F.Central", f"{(p['f_start'] + p['f_stop']) / 2:.2f} MHz"),
            ("L_int", f"{r['len_inner_mm']:.3f} mm"),
            ("L_ext", f"{r['len_outer_mm']:.3f} mm"),
            ("D_int_tube", f"{r['d_int_tube']:.3f} mm"),
            ("D_out50", f"{r['d_out_50ohm']:.3f} mm")
        ]
        for i, (lab, val) in enumerate(tbl):
            row = ctk.CTkFrame(self.param_frame)
            row.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(row, text=lab, width=150, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, width=100).pack(side="right")

        # Atualizar modelo 3D (preparar para visualização)
        self.current_calc = calc

    def launch_3d_viewer(self):
        if hasattr(self, 'current_calc'):
            threading.Thread(
                target=create_coaxial_geometry,
                args=(self.current_calc.get_geometry_for_viewer(),),
                daemon=True
            ).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()