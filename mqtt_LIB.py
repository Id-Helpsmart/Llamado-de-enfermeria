import time
import threading
import string
import random
import json
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

class MQTTClientHandler:
    def __init__(
        self,
        server: str = "iotm.helpmedica.com",
        port: int = 1883,
        username: str = "device1.helpmedica",
        password: str = "device1.helpmedica",
        client_id=None
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id if client_id else self.generate_client_id()

        # Initialize client
        self.client = mqtt.Client(
            client_id=self.client_id,
            callback_api_version=CallbackAPIVersion.VERSION2,
            clean_session=True,
            reconnect_on_failure=True
        )

        if username and password:
            self.client.username_pw_set(username, password)
        
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe

        self.lock = threading.Lock()
        self.is_connected = False
        self.mensaje_recibido = None
        self.actualizacion = False

        # Bandera de error
        self.error_flag = False

    def generate_client_id(self, length=8):
        characters = string.ascii_letters + string.digits
        return "client_" + ''.join(random.choice(characters) for _ in range(length))

    def on_connect(self, client, userdata, flags, reason_code, properties):
        try:
            if reason_code == 0:
                print(f"Connected to MQTT Broker: {self.server}:{self.port}")
                self.is_connected = True
            else:
                print(f"Failed to connect, return code {reason_code}")
                self.error_flag = True
        except Exception as e:
            print(f"[MQTT] Error en on_connect: {e}")
            self.error_flag = True

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        try:
            self.is_connected = False
        except Exception as e:
            print(f"[MQTT] Error en on_disconnect: {e}")
            self.error_flag = True

    def on_message(self, client, userdata, message):
        try:
            payload_dict = json.loads(message.payload.decode())
            print(f"[MQTT] Mensaje en topico {message.topic}\n")
            print(json.dumps(payload_dict, indent=4))
            self.mensaje_recibido = payload_dict
            self.actualizacion = True
        except Exception as e:
            print(f"[MQTT] Error al procesar mensaje: {e}")
            self.error_flag = True

    def on_publish(self, client, userdata, mid, reason_code, properties):
        try:
            pass
        except Exception as e:
            print(f"[MQTT] Error en on_publish: {e}")
            self.error_flag = True

    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        try:
            pass
        except Exception as e:
            print(f"[MQTT] Error en on_subscribe: {e}")
            self.error_flag = True

    def connect(self, keepalive=60):
        try:
            print(f"Conectando a {self.server}:{self.port}")
            self.client.connect(self.server, self.port, keepalive)
            self.client.loop_start()
        except Exception as e:
            print(f"Error al conectar: {e}")
            self.error_flag = True

    def disconnect(self):
        try:
            self.client.disconnect()
            self.client.loop_stop()
            print("[MQTT] Desconectado del broker")
        except Exception as e:
            print(f"[MQTT] Error al desconectar: {e}")
            self.error_flag = True

    def publish(self, topic: str, message, qos: int = 0, retain: bool = False, timeout: float = 5.0):
        try:
            with self.lock:
                start_time = time.time()
                while not self.is_connected:
                    if time.time() - start_time > timeout:
                        print("[MQTT] Tiempo de espera agotado para conectar.")
                        self.error_flag = True
                        return
                    time.sleep(0.1)

                payload = json.dumps(message)
                result = self.client.publish(topic, payload, qos=qos, retain=retain)
                start_time = time.time()
                while not result.is_published():
                    if time.time() - start_time > timeout:
                        print(f"[MQTT] Timeout esperando confirmacion de publicacion en {topic}")
                        self.error_flag = True
                        return
                    time.sleep(0.1)
        except Exception as e:
            print(f"[MQTT] Error publicando en {topic}: {e}")
            self.error_flag = True

    def subscribe(self, topic: str, qos: int = 0, timeout: float = 5.0):
        try:
            with self.lock:
                start_time = time.time()
                while not self.is_connected:
                    if time.time() - start_time > timeout:
                        print("[MQTT] Tiempo de espera agotado para conectar.")
                        self.error_flag = True
                        return
                    time.sleep(0.1)

                self.client.subscribe(topic, qos)
                print(f"[MQTT] Suscrito a {topic}")

        except Exception as e:
            print(f"[MQTT] Error al suscribirse a {topic}: {e}")
            self.error_flag = True

    def unsubscribe(self, topic: str):
        try:
            with self.lock:
                self.client.unsubscribe(topic)
        except Exception as e:
            print(f"[MQTT] Error al desuscribirse de {topic}: {e}")
            self.error_flag = True
