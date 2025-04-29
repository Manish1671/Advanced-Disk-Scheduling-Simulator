import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import animation
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import random
from itertools import cycle
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.colors as mcolors

def calculate_metrics(sequence):
    """Calculate performance metrics for a disk scheduling sequence"""
    if len(sequence) < 2:
        return {
            "total_movement": 0,
            "avg_seek_time": 0,
            "num_operations": 0
        }
    
    total_movement = sum(abs(sequence[i] - sequence[i-1]) for i in range(1, len(sequence)))
    avg_seek_time = total_movement / (len(sequence) - 1)
    num_operations = len(sequence) - 1
    
    return {
        "total_movement": total_movement,
        "avg_seek_time": avg_seek_time,
        "num_operations": num_operations
    }

class DiskSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Disk Scheduling Simulator")
        self.root.geometry("1200x800")

        # Theme variables
        self.theme_mode = tk.StringVar(value="light")
        self.themes = {
            "light": {
                "bg": "#f0f0f0",
                "fg": "#000000",
                "plot_bg": "#ffffff",
                "plot_fg": "#000000",
                "grid": "#dddddd"
            },
            "dark": {
                "bg": "#2d2d2d",
                "fg": "#ffffff",
                "plot_bg": "#1e1e1e",
                "plot_fg": "#ffffff",
                "grid": "#444444"
            }
        }

        # Variables
        self.requests = []
        self.head_position = tk.IntVar(value=50)
        self.disk_size = tk.IntVar(value=200)
        self.algorithm = tk.StringVar(value="FCFS")
        self.animation_speed = tk.IntVar(value=500)
        self.is_animating = False
        self.anim = None
        self.selected_algorithms = []
        self.comparison_mode = tk.BooleanVar(value=False)
        self.random_requests = tk.BooleanVar(value=False)
        self.num_requests = tk.IntVar(value=8)
        self.step_mode = tk.BooleanVar(value=False)
        self.current_step = 0
        self.metrics_data = []
        self.sequence = []
        self.view_3d = tk.BooleanVar(value=False)
        self.color_dialog = None
        self.lines = {}

        # Color scheme for different algorithms
        self.color_map = {
            "FCFS": ('#FF6B6B', '#4ECDC4'),
            "SSTF": ('#A8E6CF', '#FF8B94'),
            "SCAN": ('#6C5B7B', '#C06C84'),
            "C-SCAN": ('#45B7D1', '#FFBE0B'),
            "LOOK": ('#96CEB4', '#FFEEAD'),
            "C-LOOK": ('#9B5DE5', '#00BBF9')
        }

        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)
        self.root.grid_rowconfigure(0, weight=1)

        self.create_widgets()
        self.setup_plot()
        self.apply_theme()

    def create_widgets(self):
        # Left panel for controls
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.grid(row=0, column=0, sticky="nsew")

        # Input fields
        ttk.Label(control_frame, text="Head Position:", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=5)
        ttk.Entry(control_frame, textvariable=self.head_position).grid(row=0, column=1, pady=5)

        ttk.Label(control_frame, text="Disk Size:", font=('Arial', 10, 'bold')).grid(row=1, column=0, pady=5)
        ttk.Entry(control_frame, textvariable=self.disk_size).grid(row=1, column=1, pady=5)

        ttk.Label(control_frame, text="Request Queue:", font=('Arial', 10, 'bold')).grid(row=2, column=0, pady=5)
        self.request_entry = ttk.Entry(control_frame, width=30)
        self.request_entry.grid(row=2, column=1, pady=5)
        self.request_entry.insert(0, "98, 183, 37, 122, 14, 124, 65, 67")

        # Number of requests for random generation
        ttk.Label(control_frame, text="Number of Requests:", font=('Arial', 10, 'bold')).grid(row=3, column=0, pady=5)
        ttk.Entry(control_frame, textvariable=self.num_requests).grid(row=3, column=1, pady=5)

        # Random requests checkbox
        ttk.Checkbutton(control_frame, text="Generate Random Requests",
                       variable=self.random_requests).grid(row=4, column=0, columnspan=2, pady=5)

        # Animation speed slider
        ttk.Label(control_frame, text="Animation Speed:", font=('Arial', 10, 'bold')).grid(row=5, column=0, pady=5)
        speed_slider = ttk.Scale(control_frame, from_=100, to=1000,
                                variable=self.animation_speed,
                                orient='horizontal')
        speed_slider.grid(row=5, column=1, pady=5, sticky="ew")

        # Algorithm selection
        algorithms = ["FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"]
        ttk.Label(control_frame, text="Algorithm:", font=('Arial', 10, 'bold')).grid(row=6, column=0, pady=5)
        algorithm_menu = ttk.Combobox(control_frame, textvariable=self.algorithm, values=algorithms)
        algorithm_menu.grid(row=6, column=1, pady=5)

        # Comparison mode checkbox
        ttk.Checkbutton(control_frame, text="Comparison Mode",
                       variable=self.comparison_mode).grid(row=7, column=0, columnspan=2, pady=5)

        # Algorithm multi-select listbox (hidden by default)
        self.algorithm_listbox = tk.Listbox(control_frame, selectmode=tk.MULTIPLE, height=6)
        self.algorithm_listbox.grid(row=8, column=0, columnspan=2, pady=5, sticky="ew")
        for algo in algorithms:
            self.algorithm_listbox.insert(tk.END, algo)
        self.algorithm_listbox.grid_remove()

        # Step mode controls
        ttk.Checkbutton(control_frame, text="Step-by-Step Mode",
                       variable=self.step_mode).grid(row=9, column=0, columnspan=2, pady=5)
        self.next_button = ttk.Button(control_frame, text="Next Step", command=self.next_step,
                                    state=tk.DISABLED)
        self.next_button.grid(row=10, column=0, columnspan=2, pady=5)

        # 3D view checkbox
        ttk.Checkbutton(control_frame, text="3D View",
                       variable=self.view_3d).grid(row=11, column=0, columnspan=2, pady=5)

        # Buttons
        ttk.Button(control_frame, text="Simulate", command=self.simulate).grid(row=12, column=0, columnspan=2, pady=10)
        ttk.Button(control_frame, text="Clear", command=self.clear).grid(row=13, column=0, columnspan=2, pady=5)
        ttk.Button(control_frame, text="Export Report", command=self.export_report).grid(row=14, column=0, columnspan=2, pady=10)
        
        # Theme toggle button
        ttk.Button(control_frame, text="Toggle Theme", 
                  command=self.toggle_theme).grid(row=15, column=0, columnspan=2, pady=5)
        
        # Color customization button
        ttk.Button(control_frame, text="Customize Colors", 
                  command=self.open_color_dialog).grid(row=16, column=0, columnspan=2, pady=5)

        # Right panel for visualization
        self.setup_plot()

    def setup_plot(self):
        self.stop_animation()
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()
        if hasattr(self, 'fig'):
            plt.close(self.fig)
        
        if self.view_3d.get():
            self.fig = plt.figure(figsize=(10, 6))
            self.ax = self.fig.add_subplot(111, projection='3d')
        else:
            self.fig, self.ax = plt.subplots(figsize=(10, 6))
            
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.ax.set_title("Disk Scheduling Visualization")
        self.ax.set_xlabel("Request Sequence")
        self.ax.set_ylabel("Disk Position")
        if self.view_3d.get():
            self.ax.set_zlabel("Time")
        self.ax.grid(True, alpha=0.5 if self.theme_mode.get() == "dark" else 0.7)
        self.apply_theme()
        self.canvas.draw()

    def toggle_theme(self):
        current_theme = self.theme_mode.get()
        new_theme = "dark" if current_theme == "light" else "light"
        self.theme_mode.set(new_theme)
        self.apply_theme()
    
    def apply_theme(self):
        theme = self.themes[self.theme_mode.get()]
        
        # Apply to main window
        self.root.config(bg=theme["bg"])
        
        # Apply to all widgets
        for widget in self.root.winfo_children():
            try:
                widget.config(bg=theme["bg"])
                widget.config(fg=theme["fg"])
            except:
                pass
        
        # Apply to plot
        if hasattr(self, 'ax'):
            self.ax.set_facecolor(theme["plot_bg"])
            self.ax.xaxis.label.set_color(theme["plot_fg"])
            self.ax.yaxis.label.set_color(theme["plot_fg"])
            self.ax.title.set_color(theme["plot_fg"])
            self.ax.tick_params(axis='x', colors=theme["plot_fg"])
            self.ax.tick_params(axis='y', colors=theme["plot_fg"])
            self.ax.grid(True, color=theme["grid"], alpha=0.5 if self.theme_mode.get() == "dark" else 0.7)
            
            if self.view_3d.get():
                self.ax.zaxis.label.set_color(theme["plot_fg"])
                self.ax.tick_params(axis='z', colors=theme["plot_fg"])
        
        if hasattr(self, 'fig'):
            self.fig.patch.set_facecolor(theme["bg"])
        
        if hasattr(self, 'canvas'):
            self.canvas.draw()

    def open_color_dialog(self):
        if self.color_dialog and self.color_dialog.winfo_exists():
            self.color_dialog.lift()
            return
            
        self.color_dialog = tk.Toplevel(self.root)
        self.color_dialog.title("Algorithm Color Customization")
        
        # Create color pickers for each algorithm
        row = 0
        self.color_vars = {}
        for algo, (color1, color2) in self.color_map.items():
            ttk.Label(self.color_dialog, text=algo).grid(row=row, column=0, padx=5, pady=5)
            
            self.color_vars[algo] = (tk.StringVar(value=color1), tk.StringVar(value=color2))
            
            ttk.Entry(self.color_dialog, textvariable=self.color_vars[algo][0], width=7).grid(row=row, column=1, padx=5)
            ttk.Entry(self.color_dialog, textvariable=self.color_vars[algo][1], width=7).grid(row=row, column=2, padx=5)
            
            row += 1
        
        ttk.Button(self.color_dialog, text="Apply", command=self.apply_colors).grid(row=row, column=1, pady=10)
    
    def apply_colors(self):
        for algo, (color1_var, color2_var) in self.color_vars.items():
            self.color_map[algo] = (color1_var.get(), color2_var.get())
        
        # Redraw if we have existing data
        if self.sequence:
            self.setup_plot()
            if self.comparison_mode.get():
                self.simulate_comparison([int(x.strip()) for x in self.request_entry.get().split(",")], 
                                       self.head_position.get(), 
                                       self.disk_size.get())
            else:
                self.simulate_single([int(x.strip()) for x in self.request_entry.get().split(",")], 
                                   self.head_position.get(), 
                                   self.disk_size.get())
        
        self.color_dialog.destroy()
        self.color_dialog = None

    def stop_animation(self):
        if self.anim is not None and hasattr(self.anim, 'event_source') and self.anim.event_source is not None:
            self.anim.event_source.stop()
        self.is_animating = False
        self.anim = None

    def simulate(self):
        try:
            self.stop_animation()
            self.setup_plot()
            self.metrics_data = []
            
            # Get input values
            if self.random_requests.get():
                disk_size = self.disk_size.get()
                requests = sorted(random.sample(range(1, disk_size), min(self.num_requests.get(), disk_size-1)))
                self.request_entry.delete(0, tk.END)
                self.request_entry.insert(0, ", ".join(map(str, requests)))
            else:
                requests = [int(x.strip()) for x in self.request_entry.get().split(",")]
            
            head_pos = self.head_position.get()
            disk_size = self.disk_size.get()
            
            if self.comparison_mode.get():
                self.algorithm_listbox.grid()
                self.simulate_comparison(requests, head_pos, disk_size)
            else:
                self.algorithm_listbox.grid_remove()
                self.simulate_single(requests, head_pos, disk_size)
                
            self.canvas.draw()
        except ValueError:
            messagebox.showerror("Error", "Invalid input values")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def simulate_single(self, requests, head_pos, disk_size):
        def fcfs(requests, head, disk_size):
            return [head] + requests

        def sstf(requests, head, disk_size):
            sequence = [head]
            remaining = requests.copy()
            while remaining:
                closest = min(remaining, key=lambda x: abs(x - sequence[-1]))
                sequence.append(closest)
                remaining.remove(closest)
            return sequence

        def scan(requests, head, disk_size):
            requests = sorted(requests + [0, disk_size-1])
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + left[::-1]

        def cscan(requests, head, disk_size):
            requests = sorted(requests + [0, disk_size-1])
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + [0] + left

        def look(requests, head, disk_size):
            requests = sorted(requests)
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + left[::-1]

        def clook(requests, head, disk_size):
            requests = sorted(requests)
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + left

        algorithm_map = {
            "FCFS": fcfs,
            "SSTF": sstf,
            "SCAN": scan,
            "C-SCAN": cscan,
            "LOOK": look,
            "C-LOOK": clook
        }
        
        algo = self.algorithm.get()
        self.sequence = algorithm_map[algo](requests, head_pos, disk_size)
        metrics = calculate_metrics(self.sequence)
        self.metrics_data.append({"Algorithm": algo, **metrics})
        
        if self.step_mode.get():
            self.current_step = 0
            self.next_button.config(state=tk.NORMAL)
            self.animate_step()
        else:
            self.animate_sequence(self.sequence, algo)
            self.show_metrics()

    def simulate_comparison(self, requests, head_pos, disk_size):
        def fcfs(requests, head, disk_size):
            return [head] + requests

        def sstf(requests, head, disk_size):
            sequence = [head]
            remaining = requests.copy()
            while remaining:
                closest = min(remaining, key=lambda x: abs(x - sequence[-1]))
                sequence.append(closest)
                remaining.remove(closest)
            return sequence

        def scan(requests, head, disk_size):
            requests = sorted(requests + [0, disk_size-1])
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + left[::-1]

        def cscan(requests, head, disk_size):
            requests = sorted(requests + [0, disk_size-1])
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + [0] + left

        def look(requests, head, disk_size):
            requests = sorted(requests)
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + left[::-1]

        def clook(requests, head, disk_size):
            requests = sorted(requests)
            left = [r for r in requests if r < head]
            right = [r for r in requests if r >= head]
            return [head] + right + left

        algorithm_map = {
            "FCFS": fcfs,
            "SSTF": sstf,
            "SCAN": scan,
            "C-SCAN": cscan,
            "LOOK": look,
            "C-LOOK": clook
        }
        
        selected_indices = self.algorithm_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one algorithm")
            return
            
        selected_algos = [self.algorithm_listbox.get(i) for i in selected_indices]
        sequences = {}
        
        # Calculate all sequences and metrics
        for algo in selected_algos:
            seq = algorithm_map[algo](requests, head_pos, disk_size)
            sequences[algo] = seq
            metrics = calculate_metrics(seq)
            self.metrics_data.append({"Algorithm": algo, **metrics})
        
        # Find best algorithm
        best_algo = min(self.metrics_data, key=lambda x: x["total_movement"])["Algorithm"]
        
        # Plot all sequences
        self.ax.clear()
        colors = cycle(['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'])
        
        for algo, seq in sequences.items():
            color = next(colors)
            x = list(range(len(seq)))
            y = seq
            if self.view_3d.get():
                z = list(range(len(seq)))
                line = self.ax.plot(x, y, z, '-', label=f"{algo} ({calculate_metrics(seq)['total_movement']})", 
                            color=color, linewidth=2)
                self.ax.scatter(x, y, z, color=color, s=50)
            else:
                line = self.ax.plot(x, y, '-', label=f"{algo} ({calculate_metrics(seq)['total_movement']})", 
                            color=color, linewidth=2)
                self.ax.scatter(x, y, color=color, s=50)
            
            if algo == best_algo:
                if self.view_3d.get():
                    self.ax.scatter(x[-1], y[-1], z[-1], color='gold', s=200, edgecolor='black', 
                                  label=f"Best: {algo}", zorder=3)
                else:
                    self.ax.scatter(x[-1], y[-1], color='gold', s=200, edgecolor='black', 
                                  label=f"Best: {algo}", zorder=3)
        
        self.ax.set_xlabel("Request Sequence")
        self.ax.set_ylabel("Disk Position")
        if self.view_3d.get():
            self.ax.set_zlabel("Time")
            self.ax.view_init(elev=30, azim=-60)
        self.ax.set_title("Algorithm Comparison")
        
        # Create legend with picker enabled (updated for newer matplotlib)
        legend = self.ax.legend()
        for line in legend.get_lines():
            line.set_picker(5)  # 5 points tolerance
        
        self.fig.canvas.mpl_connect('pick_event', self.on_legend_pick)
        
        # Store line references
        self.lines = {algo: line for algo, line in zip(sequences.keys(), self.ax.lines[::2])}
        
        # Ensure grid is visible
        self.ax.grid(True, alpha=0.5 if self.theme_mode.get() == "dark" else 0.7)
        
        self.ax.set_ylim(-10, disk_size + 10)
        self.apply_theme()
        self.canvas.draw()

    def on_legend_pick(self, event):
        # On legend pick, toggle the visibility of the corresponding line
        line = event.artist
        line.set_visible(not line.get_visible())
        
        # Change the alpha on the legend item
        line.set_alpha(1.0 if line.get_visible() else 0.2)
        
        # Update all parts of the line (including markers)
        if line in self.ax.lines:
            idx = self.ax.lines.index(line)
            if idx < len(self.ax.collections):
                self.ax.collections[idx].set_visible(line.get_visible())
        
        self.canvas.draw()

    def animate_sequence(self, sequence, algo):
        self.sequence = sequence
        self.is_animating = True
        
        color1, color2 = self.color_map[algo]
        
        def update(frame):
            if frame >= len(sequence):
                self.stop_animation()
                return
                
            self.ax.clear()
            current_seq = sequence[:frame+1]
            x = list(range(len(current_seq)))
            y = current_seq
            
            if self.view_3d.get():
                z = [0] * len(x)
                if len(x) > 1:
                    self.ax.plot(x[:-1], y[:-1], z[:-1], '-', color=color1, linewidth=2)
                    self.ax.scatter(x[:-1], y[:-1], z[:-1], color=color1, s=100)
                if len(x) > 0:
                    self.ax.scatter(x[-1], y[-1], z[-1], color='red', s=150)
                
                self.ax.set_zlabel("Time")
                self.ax.view_init(elev=30, azim=-60)
            else:
                if len(x) > 1:
                    self.ax.plot(x[:-1], y[:-1], '-', color=color1, linewidth=2)
                    self.ax.scatter(x[:-1], y[:-1], color=color1, s=100)
                if len(x) > 0:
                    self.ax.scatter(x[-1], y[-1], color='red', s=150)
                
            self.ax.set_xlabel("Request Sequence")
            self.ax.set_ylabel("Disk Position")
            self.ax.set_title(f"{algo} Disk Scheduling")
            self.ax.grid(True, alpha=0.5 if self.theme_mode.get() == "dark" else 0.7)
            self.ax.set_ylim(-10, self.disk_size.get() + 10)
            
            if frame > 0:
                current_movement = sum(abs(sequence[i] - sequence[i-1]) for i in range(1, frame + 1))
                self.ax.text(0.02, 0.98, f'Current head movement: {current_movement}', 
                            transform=self.ax.transAxes, 
                            verticalalignment='top',
                            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
            self.apply_theme()
        
        self.anim = animation.FuncAnimation(
            self.fig, 
            update, 
            frames=len(sequence),
            interval=self.animation_speed.get(),
            repeat=False
        )

    def animate_step(self):
        if self.current_step >= len(self.sequence):
            self.next_button.config(state=tk.DISABLED)
            self.show_metrics()
            return
            
        self.ax.clear()
        current_seq = self.sequence[:self.current_step+1]
        x = list(range(len(current_seq)))
        y = current_seq
        
        color1, color2 = self.color_map[self.algorithm.get()]
        
        if self.view_3d.get():
            z = [0] * len(x)
            if len(x) > 1:
                self.ax.plot(x[:-1], y[:-1], z[:-1], '-', color=color1, linewidth=2)
                self.ax.scatter(x[:-1], y[:-1], z[:-1], color=color1, s=100)
            if len(x) > 0:
                self.ax.scatter(x[-1], y[-1], z[-1], color='red', s=150)
            self.ax.set_zlabel("Time")
            self.ax.view_init(elev=30, azim=-60)
        else:
            if len(x) > 1:
                self.ax.plot(x[:-1], y[:-1], '-', color=color1, linewidth=2)
                self.ax.scatter(x[:-1], y[:-1], color=color1, s=100)
            if len(x) > 0:
                self.ax.scatter(x[-1], y[-1], color='red', s=150)
            
        self.ax.set_xlabel("Request Sequence")
        self.ax.set_ylabel("Disk Position")
        self.ax.set_title(f"{self.algorithm.get()} Disk Scheduling (Step {self.current_step+1}/{len(self.sequence)})")
        self.ax.grid(True, alpha=0.5 if self.theme_mode.get() == "dark" else 0.7)
        self.ax.set_ylim(-10, self.disk_size.get() + 10)
        
        if self.current_step > 0:
            current_movement = sum(abs(self.sequence[i] - self.sequence[i-1]) for i in range(1, self.current_step + 1))
            self.ax.text(0.02, 0.98, f'Current head movement: {current_movement}', 
                        transform=self.ax.transAxes, 
                        verticalalignment='top',
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
        
        self.apply_theme()
        self.canvas.draw()

    def next_step(self):
        self.current_step += 1
        self.animate_step()

    def show_metrics(self):
        metrics_text = "Performance Metrics:\n\n"
        for data in self.metrics_data:
            metrics_text += (
                f"{data['Algorithm']}:\n"
                f"  Total Head Movement: {data['total_movement']}\n"
                f"  Average Seek Time: {data['avg_seek_time']:.2f}\n"
                f"  Number of Operations: {data['num_operations']}\n\n"
            )
        
        if len(self.metrics_data) > 1:
            best = min(self.metrics_data, key=lambda x: x["total_movement"])["Algorithm"]
            metrics_text += f"Best Algorithm: {best['Algorithm']} (Movement: {best['total_movement']})"
        
        messagebox.showinfo("Performance Metrics", metrics_text)

    def export_report(self):
        if not self.metrics_data:
            messagebox.showwarning("Warning", "No simulation data to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("CSV Files", "*.csv")]
        )
        
        if not file_path:
            return
            
        if file_path.endswith('.pdf'):
            self.export_pdf(file_path)
        else:
            self.export_csv(file_path)
            
        messagebox.showinfo("Success", "Report exported successfully")

    def export_pdf(self, file_path):
        with PdfPages(file_path) as pdf:
            pdf.savefig(self.fig)
            
            plt.figure(figsize=(8, 6))
            plt.axis('off')
            
            metrics_text = "Disk Scheduling Simulation Report\n\n"
            metrics_text += f"Head Position: {self.head_position.get()}\n"
            metrics_text += f"Disk Size: {self.disk_size.get()}\n"
            metrics_text += f"Request Queue: {self.request_entry.get()}\n\n"
            
            metrics_text += "Performance Metrics:\n\n"
            for data in self.metrics_data:
                metrics_text += (
                    f"{data['Algorithm']}:\n"
                    f"  Total Head Movement: {data['total_movement']}\n"
                    f"  Average Seek Time: {data['avg_seek_time']:.2f}\n"
                    f"  Number of Operations: {data['num_operations']}\n\n"
                )
            
            if len(self.metrics_data) > 1:
                best = min(self.metrics_data, key=lambda x: x["total_movement"])
                metrics_text += f"Recommended Algorithm: {best['Algorithm']}\n"
                metrics_text += f"Minimum Head Movement: {best['total_movement']}"
            
            plt.text(0.1, 0.9, metrics_text, fontsize=10, va='top')
            pdf.savefig()
            plt.close()

    def export_csv(self, file_path):
        data = {
            "Head Position": [self.head_position.get()],
            "Disk Size": [self.disk_size.get()],
            "Request Queue": [self.request_entry.get()]
        }
        
        for metric in self.metrics_data:
            algo = metric["Algorithm"]
            data[f"{algo}_Total_Movement"] = [metric["total_movement"]]
            data[f"{algo}_Avg_Seek_Time"] = [metric["avg_seek_time"]]
            data[f"{algo}_Num_Operations"] = [metric["num_operations"]]
        
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)

    def clear(self):
        try:
            self.stop_animation()
            self.setup_plot()
            self.request_entry.delete(0, tk.END)
            self.request_entry.insert(0, "98, 183, 37, 122, 14, 124, 65, 67")
            self.head_position.set(50)
            self.disk_size.set(200)
            self.algorithm.set("FCFS")
            self.comparison_mode.set(False)
            self.random_requests.set(False)
            self.step_mode.set(False)
            self.view_3d.set(False)
            self.next_button.config(state=tk.DISABLED)
            self.algorithm_listbox.grid_remove()
            self.metrics_data = []
            self.canvas.draw()
        except Exception as e:
            print(f"Error in clear: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DiskSchedulerApp(root)
    root.mainloop()
