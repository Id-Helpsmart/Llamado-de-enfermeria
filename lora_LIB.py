import board
import busio
import digitalio
import adafruit_rfm9x
import time
from gpiozero import DigitalInputDevice

class LoRaHandler:
    def __init__(self, id_red="0x12", frecuencia_mhz=915.0):
        # Configuración de red y radio
        self.id_red = id_red
        self.frecuencia_mhz = frecuencia_mhz

        # Pines según guía del módulo LoRa para Raspberry Pi
        self.pin_dio = 5              # GPIO 5
        self.pin_cs = board.CE0       # CE0 (GPIO 7)
        self.pin_reset = board.D25    # GPIO 25

        # Estados internos
        self.lora_inicializado = False
        self.paquete_recibido = False
        self.mensaje_recibido = ""

        # Objetos hardware
        self.rfm9x = None
        self.spi = None
        self.cs = None
        self.reset = None
        self.dio0 = None

    # --- Callback cuando hay recepción ---
    def rx_callback(self):
        if self.rfm9x.rx_done:
            paquete = self.rfm9x.receive(timeout=None)
            if paquete:
                try:
                    mensaje = paquete.decode("ascii", errors="replace")
                    print("\n--- Paquete recibido ---")
                    print(f"Mensaje bruto: {mensaje}")

                    if mensaje.startswith(f"{self.id_red}:"):
                        self.mensaje_recibido = mensaje.split(":", 1)[1]
                        print(f"Mensaje válido recibido")
                        print(f"RSSI: {self.rfm9x.last_rssi} dBm")
                        self.paquete_recibido = True
                    else:
                        print("Mensaje recibido con ID inválido")

                except UnicodeDecodeError as e:
                    print(f"Error de decodificación: {e}")

                print("-------------------------")

    # --- Liberar recursos ---
    def cerrar(self):
        if self.dio0:
            self.dio0.close()
            self.dio0 = None
        if self.cs:
            self.cs.deinit()
            self.cs = None
        if self.reset:
            self.reset.deinit()
            self.reset = None
        if self.spi:
            self.spi.deinit()
            self.spi = None
        self.rfm9x = None
        self.lora_inicializado = False

    # --- Inicializar LoRa ---
    def iniciar_lora(self, max_intentos=3):
        self.cerrar()  # Por si hay algo anterior abierto

        for intento in range(1, max_intentos + 1):
            print(f"\n[LoRa] Inicializando... (Intento {intento})")

            try:
                # Inicializar pines CS y RESET
                self.cs = digitalio.DigitalInOut(self.pin_cs)
                self.cs.direction = digitalio.Direction.OUTPUT

                self.reset = digitalio.DigitalInOut(self.pin_reset)
                self.reset.direction = digitalio.Direction.OUTPUT

                # Resetear físicamente el módulo LoRa
                self.reset.value = False
                time.sleep(0.1)
                self.reset.value = True
                time.sleep(0.1)

                # Inicializar SPI
                self.spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

                # Inicializar módulo RFM9x
                self.rfm9x = adafruit_rfm9x.RFM9x(
                    self.spi, self.cs, self.reset, self.frecuencia_mhz, baudrate=1000000)

                # Configurar parámetros LoRa
                self.rfm9x.spreading_factor = 7
                self.rfm9x.signal_bandwidth = 125E3
                self.rfm9x.coding_rate = 4
                self.rfm9x.preamble_length = 8
                self.rfm9x.enable_crc = True
                self.rfm9x.tx_power = 14

                # Configurar interrupción DIO0
                self.dio0 = DigitalInputDevice(self.pin_dio, pull_up=False)
                self.dio0.when_activated = self.rx_callback

                # Comenzar a escuchar
                self.rfm9x.listen()
                print("[LoRa] Inicializado y escuchando.")
                self.lora_inicializado = True
                return

            except Exception as e:
                print(f"[ERROR LoRa Init - intento {intento}] {type(e).__name__}: {e}")

                # Limpiar recursos de este intento
                self.cerrar()

            time.sleep(1)  # Esperar antes de reintentar

        # Si llega aquí, todos los intentos fallaron
        self.lora_inicializado = False
        raise RuntimeError(f"[LoRa] No se pudo inicializar tras {max_intentos} intentos.")

    # --- Enviar mensajes por LoRa ---
    def enviar_lora(self, mensaje, cabecera=False):
        if not self.lora_inicializado:
            print("[LoRa] No inicializado. No se puede enviar mensaje.")
            return False

        try:
            mensaje_completo = f"{self.id_red}:{mensaje}" if cabecera else mensaje

            print("\n[LoRa] Enviando paquete...")
            print(f"Contenido: {mensaje_completo}")

            self.rfm9x.send(bytes(mensaje_completo, "utf-8"), keep_listening=True)

            print("[LoRa] Mensaje enviado correctamente.")
            return True

        except Exception as e:
            print(f"[ERROR LoRa Envío] {type(e).__name__}: {e}")
            return False
