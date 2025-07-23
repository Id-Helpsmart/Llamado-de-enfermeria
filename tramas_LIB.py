import json
import random
import subprocess
from datetime import datetime
from archivos_LIB import FileHandler


CANTIDAD_CARACTERES = 72
alfa = ['<', ':', '-', 'R', ' ', '%', 'Z', '^', 'h', 'A', '7', 'K', 'j', 'z', 'J', 'c',
        'B', 's', '2', 'g', '9', 'L', 'b', 'm', 'k', 'I', '8', 'V', 'f', 'E', 'y', '6',
        'M', 'i', 'd', 'D', '4', 'l', 'N', '5', 'F', 'n', 'C', 'r', 'W', '3', 'Q', 'u',
        '1', 'U', ',', 'G', '+', '0', 'X', 'a', 'H', 'P', 'w', 'e', 'x', 'T', 'p', 't',
        'q', 'v', 'o', 'O', '*', 'Y', '.', 'S']

class TramaHandler:
    def __init__(self):
        self.direccion = 1
        self.mac_remitente = ""
        self.mac_local = self.obtener_mac()
        self.llamado_text = ""
        self.acciones = {
            'FF': "sincro",
            'NN': "notificación",
            'EE': "Alta",
            'AA': "Rojo",
            'BB': "Azul",
            'BA': "Bano",
            'CC': "Cancelar",
            'DD': "Paciente",
            'RI': "reporte incendio",
            'SS': "sensor temp/humedad",
            'SI': "sensor incendio",
            'SV': "sensor vibración"
        }
    
    def obtener_mac(self):
        try:
            resultado = subprocess.check_output("ip link show wlan0", shell=True).decode()
            for linea in resultado.split('\n'):
                if 'link/ether' in linea:
                    mac = linea.split()[1].upper()
                    return mac
        except subprocess.CalledProcessError:
            return None
        
    def leer_parametros(self):
        archivo = FileHandler()
        df = archivo.leer_archivo()

        # Obtenemos directamente los valores porque las claves siempre existen desde crear_archivo
        empresa = df.loc[df["clave"] == "empresa", "valor"].values[0]
        sede    = df.loc[df["clave"] == "sede", "valor"].values[0]
        area    = df.loc[df["clave"] == "area", "valor"].values[0]

        return empresa, sede, area


    def codificar(self, mensaje: str) -> str:
        """
        Codifica 'mensaje' con la lógica inversa a 'decode'.
        Retorna la trama completa como string:
        "direccion,clave,mensaje_codificado"
        """
        
        # Cambia dirección: 0 -> 1 o 1 -> 0
        self.direccion ^= 1

        # Clave aleatoria entre 1 y 10
        clave = random.randint(1, 10)

        resultado = ""
        for char in mensaje:
            if char in alfa:
                pos = alfa.index(char)
                if self.direccion == 1:
                    pos = (pos - clave) % CANTIDAD_CARACTERES  # inverso a decode
                else:
                    pos = (pos + clave) % CANTIDAD_CARACTERES
                resultado += alfa[pos]
            else:
                resultado += char

        # Devuelve la trama completa lista
        return f"{self.direccion},{clave},{resultado}"
    
    def decode(self, decodifier, key, msg, debug=False):
        msg_2 = ""

        for char in msg:
            if char in alfa:
                position = alfa.index(char)
                if decodifier == 1:
                    position = (position + key) % CANTIDAD_CARACTERES
                else:
                    position = (position - key) % CANTIDAD_CARACTERES
                msg_2 += alfa[position]
            else:
                msg_2 += char

        if debug:
            print("Mensaje decodificado:", msg_2)
        return msg_2


    def procesar(self, trama):
        partes = trama.strip().split(",")

        if len(partes) < 3:
            print("Trama inválida")
            return None

        # Extraigo los parámetros de cifrado
        decodifier = int(partes[0])
        key = int(partes[1])
        msg = ",".join(partes[2:])

        decoded_msg = self.decode(decodifier, key, msg, debug=True)

        # Split según comas
        decoded_parts = decoded_msg.split(',')

        # Variables por defecto
        code = None
        mac_remitente = None
        mac_destinatario = None
        bateria_valor = None

        if len(decoded_parts) == 5:
            code, mac_destinatario, mac_remitente, _, bateria_str = decoded_parts
            try:
                bateria_valor = float(bateria_str)
            except ValueError:
                print("Valor de batería inválido.")
                return None

            # FILTRADO POR MAC DESTINATARIO
            if mac_destinatario.upper() != self.mac_local.upper():
                print(f"Ignorado: MAC destinatario {mac_destinatario} ≠ MAC local {self.mac_local}")
                return None

        elif len(decoded_parts) == 2:
            code, mac_remitente = decoded_parts
            bateria_valor = 100.0  # fijo al 100%

        else:
            print("Formato de mensaje inválido.")
            return None

        self.mac_remitente = mac_remitente
        llamado_text = self.acciones.get(code, code)
        self.llamado_text = llamado_text

        print(f"Acción: {llamado_text}")
        print(f"Mac remitente: {mac_remitente}")
        print(f"Código: {code}")
        print(f"Batería: {bateria_valor}%")

        # Construyo el JSON con batería fija o leída
        json_payload = self.build_json(llamado_text, mac_remitente, bateria_valor)
        print("JSON payload:", json.dumps(json_payload, indent=2))

        return json_payload


    def build_json(self, llamado, mac, bateria):
        empresa, sede, area = self.leer_parametros()

        now = datetime.now()
        timestamp = now.strftime("%Y:%m:%d %H:%M:%S")

        payload = {
            "llamado": llamado,
            "empresa": empresa,
            "sede": sede,
            "area": area,
            "mac": mac,
            "timestamp": timestamp,
            "sensor": [
                {
                    "type": 100,
                    "name": "BAT",
                    "number": 1,
                    "values": [
                        {
                            "type": "BATERIA",
                            "value": bateria,
                            "unit": "%",
                            "Lmin": 10,
                            "Lmax": 100
                        }
                    ]
                }
            ]
        }
        
        return payload


