import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import socket
import threading
import re
import os
from enum import Enum
import math

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        print("Error: 'toml' library not found. Please install it using 'pip install toml'")
        exit()

CONFIG_FILE = 'config.toml'

class MachineState(Enum):
    """Defines the operational states of the CNC machine."""
    IDLE = "Idle"
    WORKING = "Run" # Using "Run" for GRBL compatibility
    ALARM = "Alarm"

class GrblSimulator:
    """
    A graphical application to simulate a 3-axis GRBL CNC machine with a state machine.
    """

    def __init__(self, master):
        self.master = master
        self.master.title("GRBL 3-Axis CNC Simulator")
        self.master.geometry("850x750")

        self.config = self.load_config()
        if not self.config:
            #master.destroy()
            return
        self.apply_config()

        self.x, self.y, self.z = 0.0, 0.0, 0.0
        self.is_running = False
        self.path_history = [(0.0, 0.0, 0.0)] 
        self.view_mode = tk.StringVar(value='top')
        self.machine_state = None # Will be set by set_state

        self.create_widgets()

        self.host = self.config.get('server', {}).get('host', '127.0.0.1')
        self.port = self.config.get('server', {}).get('port', 10000)
        self.server_socket = None
        self.client_socket = None
        
        self.set_state(MachineState.IDLE)
        self.start_server()
        self.update_info()
        self.redraw_canvas()

    def load_config(self):
        #if not os.path.exists(CONFIG_FILE):
        return self.create_default_config()
        #try:
        #    with open(CONFIG_FILE, 'rb') as f:
        #        return tomllib.load(f)
        #except Exception as e:
        #    messagebox.showerror("Config Error", f"Failed to load or parse {CONFIG_FILE}:\n{e}")
        #    return None

    def create_default_config(self):
        default_config = """
# GRBL Simulator Configuration

[server]
host = "127.0.0.1"
port = 10000

[machine]
x_dim = 300.0
y_dim = 200.0
z_dim = 100.0
# Simulated feed rate in mm/minute for calculating work time
feed_rate = 800.0

[limits]
x_min = 0.0
x_max = 300.0
y_min = 0.0
y_max = 200.0
z_min = -100.0
z_max = 0.0
"""
        with open(CONFIG_FILE, 'w') as f: f.write(default_config)
            
    def apply_config(self):
        try:
            m = self.config['machine']
            self.machine_x_dim, self.machine_y_dim, self.machine_z_dim = float(m['x_dim']), float(m['y_dim']), float(m['z_dim'])
            self.feed_rate = float(m.get('feed_rate', 800.0))

            l = self.config['limits']
            self.limit_x_min, self.limit_x_max = float(l['x_min']), float(l['x_max'])
            self.limit_y_min, self.limit_y_max = float(l['y_min']), float(l['y_max'])
            self.limit_z_min, self.limit_z_max = float(l['z_min']), float(l['z_max'])
        except (KeyError, ValueError) as e:
            messagebox.showerror("Config Error", f"Invalid or missing value in {CONFIG_FILE}:\n{e}")
            raise RuntimeError(f"Configuration error: {e}")

    def set_state(self, new_state):
        """Updates the machine state and the corresponding GUI elements."""
        self.machine_state = new_state
        state_map = {
            MachineState.IDLE: ("Status: Idle", "green"),
            MachineState.WORKING: ("Status: Working", "blue"),
            MachineState.ALARM: ("Status: ALARM", "red"),
        }
        text, color = state_map.get(new_state, ("Status: Unknown", "black"))
        
        self.status_label.config(text=text, fg=color)
        
        # Enable/disable buttons based on state
        is_alarm = new_state == MachineState.ALARM
        self.reset_alarm_button.config(state=tk.NORMAL if is_alarm else tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED if is_alarm else tk.NORMAL)
        self.reset_button.config(state=tk.DISABLED if is_alarm else tk.NORMAL)


    def create_widgets(self):
        main_frame = tk.Frame(self.master)
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        view_frame = ttk.LabelFrame(left_frame, text="View")
        view_frame.pack(pady=5, fill=tk.X)
        ttk.Radiobutton(view_frame, text="Top (XY)", variable=self.view_mode, value='top', command=self.redraw_canvas).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Radiobutton(view_frame, text="Front (XZ)", variable=self.view_mode, value='front', command=self.redraw_canvas).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Radiobutton(view_frame, text="Side (YZ)", variable=self.view_mode, value='side', command=self.redraw_canvas).pack(side=tk.LEFT, padx=10, pady=5)

        self.canvas_size = 500
        self.canvas = tk.Canvas(left_frame, width=self.canvas_size, height=self.canvas_size, bg='white', relief=tk.SUNKEN, borderwidth=1)
        self.canvas.pack(pady=5)
        self.tool = self.canvas.create_oval(-10, -10, -10, -10, fill='red', outline='red')

        control_frame = tk.Frame(left_frame)
        control_frame.pack(pady=5, fill=tk.X)
        self.clear_button = tk.Button(control_frame, text="Clear Path", command=self.clear_path)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        self.reset_button = tk.Button(control_frame, text="Reset Position", command=self.reset_position)
        self.reset_button.pack(side=tk.LEFT, padx=5)
        self.reset_alarm_button = tk.Button(control_frame, text="Reset Alarm", command=self.reset_alarm, state=tk.DISABLED, bg="#ffdddd")
        self.reset_alarm_button.pack(side=tk.LEFT, padx=5)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        info_frame = tk.LabelFrame(right_frame, text="Machine Status", padx=10, pady=10)
        info_frame.pack(pady=5, fill=tk.X)
        self.status_label = tk.Label(info_frame, text="", fg="green")
        self.status_label.pack(anchor='w')
        self.connection_label = tk.Label(info_frame, text="Listening...", fg="blue")
        self.connection_label.pack(anchor='w')
        self.position_label = tk.Label(info_frame, text="X: 0.00 Y: 0.00 Z: 0.00")
        self.position_label.pack(anchor='w', pady=(10,0))
        
        log_frame = tk.LabelFrame(right_frame, text="G-Code Log", padx=10, pady=10)
        log_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, width=40, height=20, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def draw_grid_and_labels(self):
        self.canvas.delete("grid")
        view = self.view_mode.get()
        if view == 'top': x_label, y_label = "X", "Y"
        elif view == 'front': x_label, y_label = "X", "Z"
        else: x_label, y_label = "Y", "Z"
        self.canvas.create_text(self.canvas_size / 2, self.canvas_size - 5, text=f"+{x_label}", fill="black", tags="grid")
        self.canvas.create_text(10, self.canvas_size / 2, text=f"+{y_label}", fill="black", tags="grid", anchor="w")
        for i in range(11):
             p1 = self._project_point(self.limit_x_min, self.limit_y_min + (i/10.0)*(self.limit_y_max - self.limit_y_min), 'top')
             p2 = self._project_point(self.limit_x_max, self.limit_y_min + (i/10.0)*(self.limit_y_max - self.limit_y_min), 'top')
             self.canvas.create_line(p1[0],p1[1], p2[0],p2[1], fill="#dcdcdc", tags="grid")
             p1 = self._project_point(self.limit_x_min + (i/10.0)*(self.limit_x_max - self.limit_x_min), self.limit_y_min, 'top')
             p2 = self._project_point(self.limit_x_min + (i/10.0)*(self.limit_x_max - self.limit_x_min), self.limit_y_max, 'top')
             self.canvas.create_line(p1[0],p1[1], p2[0],p2[1], fill="#dcdcdc", tags="grid")

    def log_message(self, message, color='black'):
        if not hasattr(self, 'log_text'): return
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n', (color,))
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
        
    def clear_path(self):
        current_pos = self.path_history[-1]
        self.path_history = [current_pos]
        self.redraw_canvas()
        self.log_message("Path cleared.", "blue")

    def reset_position(self):
        if (self.limit_x_min <= 0 <= self.limit_x_max and self.limit_y_min <= 0 <= self.limit_y_max and self.limit_z_min <= 0 <= self.limit_z_max):
            self.x, self.y, self.z = 0.0, 0.0, 0.0
            self.path_history = [(0.0, 0.0, 0.0)]
            self.redraw_canvas()
            self.update_info()
            self.log_message("Position reset to home (0,0,0).", "blue")
        else:
            self.log_message("Cannot reset to (0,0,0) as it is outside configured limits.", "red")
            
    def reset_alarm(self):
        """Resets an alarm state back to idle."""
        if self.machine_state == MachineState.ALARM:
            self.set_state(MachineState.IDLE)
            self.log_message("Alarm reset. Machine unlocked.", "green")

    def start_server(self):
        print("startserver")
        self.is_running = True
        self.server_thread = threading.Thread(target=self.accept_connections, daemon=True)
        self.server_thread.start()

    def accept_connections(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            print(self.host, "--", self.port)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.master.after(0, self.connection_label.config, {'text': f"Listening on: {self.host}:{self.port}"})
            self.log_message(f"Server started on {self.host}:{self.port}", "green")
        except OSError as e:
            self.log_message(f"Error starting server: {e}", "red")
            self.master.after(0, self.connection_label.config, {'text': "Error: Port in use", 'fg': 'red'})
            return

        while self.is_running:
            try:
                client, addr = self.server_socket.accept()
                self.master.after(0, self.handle_client, client, addr)
            except OSError: break

    def handle_client(self, client, addr):
        self.client_socket = client
        self.log_message(f"Connected by {addr}", "green")
        self.connection_label.config(text=f"Connected to: {addr[0]}", fg="green")
        try:
            client.sendall(b'Grbl 1.1h [\'$\' for help]\r\n')
            while self.is_running:
                data = client.recv(1024)
                if not data: break
                for line in data.decode('utf-8').strip().splitlines():
                    self.master.after(0, self.process_gcode, line)
        except (ConnectionResetError, BrokenPipeError):
             self.log_message("Client disconnected.", "orange")
        finally:
            if client: client.close()
            self.client_socket = None
            self.connection_label.config(text=f"Listening on: {self.host}:{self.port}", fg="blue")
            if self.machine_state == MachineState.WORKING:
                self.set_state(MachineState.IDLE)

    def process_gcode(self, command):
        if self.machine_state == MachineState.ALARM and command != '$X':
            self.log_message(f"Blocked (ALARM): {command}", "red")
            if self.client_socket: self.client_socket.sendall(b'error:9\r\n') # G-code locked out
            return

        if self.machine_state == MachineState.WORKING:
            self.log_message(f"Blocked (Busy): {command}", "orange")
            if self.client_socket: self.client_socket.sendall(b'error:24\r\n') # G-code queue full
            return
        
        self.log_message(f"Received: {command}")
        
        if command.upper() == '$X':
            self.reset_alarm()
            if self.client_socket: self.client_socket.sendall(b'ok\r\n')
            return

        if command == '?':
            status_report = f"<{self.machine_state.value}|WPos:{self.x:.3f},{self.y:.3f},{self.z:.3f}>\r\n"
            if self.client_socket: self.client_socket.sendall(status_report.encode('utf-8'))
            return

        if command.upper().startswith(('G0', 'G1')):
            new_x = self.get_coord(command, 'X', self.x)
            new_y = self.get_coord(command, 'Y', self.y)
            new_z = self.get_coord(command, 'Z', self.z)
            self.move_to(new_x, new_y, new_z)
            if self.client_socket: self.client_socket.sendall(b'ok\r\n')
        else: # Unrecognized command
            if self.client_socket: self.client_socket.sendall(b'ok\r\n')

    def get_coord(self, cmd, axis, current):
        m = re.search(f'{axis}(-?\\d*\\.?\\d*)', cmd, re.I)
        return float(m.group(1)) if m else current
    
    def _project_point(self, p_x, p_y, view):
        if view == 'top': x_range, y_range, x_min, y_min = self.machine_x_dim, self.machine_y_dim, self.limit_x_min, self.limit_y_min
        elif view == 'front': x_range, y_range, x_min, y_min = self.machine_x_dim, self.machine_z_dim, self.limit_x_min, self.limit_z_min
        else: x_range, y_range, x_min, y_min = self.machine_y_dim, self.machine_z_dim, self.limit_y_min, self.limit_z_min
        x_s = self.canvas_size/x_range if x_range!=0 else 0
        y_s = self.canvas_size/y_range if y_range!=0 else 0
        return (p_x - x_min)*x_s, self.canvas_size - (p_y-y_min)*y_s

    def _project_3d(self, x, y, z):
        v = self.view_mode.get()
        if v=='top': return self._project_point(x, y, v)
        if v=='front': return self._project_point(x, z, v)
        if v=='side': return self._project_point(y, z, v)
        return 0,0

    def redraw_canvas(self):
        self.canvas.delete("path")
        self.draw_grid_and_labels()
        if len(self.path_history) > 1:
            for i in range(len(self.path_history) - 1):
                p1, p2 = self.path_history[i], self.path_history[i+1]
                s_x,s_y = self._project_3d(*p1)
                e_x,e_y = self._project_3d(*p2)
                self.canvas.create_line(s_x,s_y,e_x,e_y,fill='blue',width=2,tags="path")
        if self.path_history:
            lx,ly = self._project_3d(*self.path_history[-1])
            self.canvas.coords(self.tool, lx-5,ly-5,lx+5,ly+5)

    def move_to(self, new_x, new_y, new_z):
        clamped_x = max(self.limit_x_min, min(self.limit_x_max, new_x))
        clamped_y = max(self.limit_y_min, min(self.limit_y_max, new_y))
        clamped_z = max(self.limit_z_min, min(self.limit_z_max, new_z))
        
        limit_hit = False
        if clamped_x != new_x: self.log_message(f"ALARM: X limit hit ({new_x})", "red"); limit_hit=True
        if clamped_y != new_y: self.log_message(f"ALARM: Y limit hit ({new_y})", "red"); limit_hit=True
        if clamped_z != new_z: self.log_message(f"ALARM: Z limit hit ({new_z})", "red"); limit_hit=True
        
        dist = math.sqrt((clamped_x-self.x)**2 + (clamped_y-self.y)**2 + (clamped_z-self.z)**2)
        duration_ms = int((dist / self.feed_rate) * 60 * 1000) if self.feed_rate > 0 else 0

        self.x, self.y, self.z = clamped_x, clamped_y, clamped_z
        self.path_history.append((self.x, self.y, self.z))
        self.redraw_canvas()
        self.update_info()

        if limit_hit:
            self.set_state(MachineState.ALARM)
        elif duration_ms > 0:
            self.set_state(MachineState.WORKING)
            self.master.after(duration_ms, lambda: self.set_state(MachineState.IDLE))

    def update_info(self):
        self.position_label.config(text=f"X: {self.x:.2f}  Y: {self.y:.2f}  Z: {self.z:.2f}")

    def on_closing(self):
        self.is_running = False
        if self.client_socket:
            try: self.client_socket.shutdown(socket.SHUT_RDWR); self.client_socket.close()
            except OSError: pass
        if self.server_socket: self.server_socket.close() 
        self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    try:
        app = GrblSimulator(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except (RuntimeError, tk.TclError) as e:
        print(f"Failed to start application: {e}")


