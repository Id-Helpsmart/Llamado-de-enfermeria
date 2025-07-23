from pathlib import Path
import pandas as pd
from datetime import datetime

class FileHandler:
    def __init__(self, file_name="configuracion.csv", directory=None):
        # Si no se pasa directorio, usar el escritorio del usuario activo
        user_home = Path.home()
        self.directory = Path(directory or user_home / "Desktop" / "llamado_enfermeria")
        self.file_path = self.directory / file_name

        try:
            self.directory.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"[FileHandler] Error: No se tienen permisos para crear el directorio {self.directory}.")
            raise
        except Exception as e:
            print(f"[FileHandler] Error al crear el directorio: {e}")
            raise

    def crear_archivo(self):
        if not self.file_path.exists():
            data_inicial = [
                {"clave": "empresa", "valor": ""},
                {"clave": "sede", "valor": ""},
                {"clave": "area", "valor": ""}
            ]
            df = pd.DataFrame(data_inicial)
            df.to_csv(self.file_path, index=False)
            print(f"[FileHandler] Archivo creado con claves iniciales en {self.file_path}")
        else:
            print(f"[FileHandler] El archivo ya existe: {self.file_path}")


    def actualizar_archivo(self, data: dict):
        """
        Recibe un diccionario {clave: valor} y para cada par:
         - Si la clave existe, actualiza su valor.
         - Si no existe, añade una nueva fila.
        Si el archivo no existe, lo crea antes de actualizar.
        """
        # Asegurarnos de que el archivo exista
        if not self.file_path.exists():
            print(f"[FileHandler] El archivo no existe, creando uno nuevo...")
            self.crear_archivo()

        df = pd.read_csv(self.file_path)

        # Para cada clave/valor en data
        for clave, valor in data.items():
            if clave in df["clave"].values:
                df.loc[df["clave"] == clave, "valor"] = valor
            else:
                df = pd.concat([df, pd.DataFrame([{"clave": clave, "valor": valor}])], ignore_index=True)

        # Guardar cambios
        df.to_csv(self.file_path, index=False)
        print(f"[FileHandler] Archivo actualizado en {self.file_path}")

    def leer_archivo(self) -> pd.DataFrame:
        """
        Lee y devuelve todo el contenido del CSV como DataFrame.
        Si no existe, lo crea primero.
        """
        if not self.file_path.exists():
            print(f"[FileHandler] El archivo no existe, creando uno nuevo...")
            self.crear_archivo()
        return pd.read_csv(self.file_path)
    
    def log_errores(self, valor):
        """
        Guarda un error en el archivo de configuración usando timestamp como clave.
        """
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        data = {timestamp: valor}
        self.actualizar_archivo(data)
