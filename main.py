import time
import subprocess
import sys
from lora_LIB import LoRaHandler
from tramas_LIB import TramaHandler
from mqtt_LIB import MQTTClientHandler
from archivos_LIB import FileHandler

# Variables globales
direccion_topicos = {"empresa": None, "area": None}
topic_base = None
mac_local = None
internet_ok = False
contador_publicaciones = 0

def estado_wifi():
    global internet_ok

    try:
        ping_resultado = subprocess.run(
            ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        if ping_resultado.returncode == 0:
            # Hay internet, señalamos bandera OK y salimos
            internet_ok = True
            return
        
        else:
            print("Sin acceso a internet...")
            internet_ok = False
        
    except Exception as e:
        internet_ok = False
        error_msg = f"Error al verificar o reiniciar WiFi: {type(e).__name__} - {e}"
        archivo.log_errores(error_msg)

def sub_manager():
    global direccion_topicos, topic_base
    datos = archivo.leer_archivo()

    try:
        empresa_actual = datos.loc[datos['clave'] == 'empresa', 'valor'].values[0]
        area_actual = datos.loc[datos['clave'] == 'area', 'valor'].values[0]
    except IndexError as e:
        error_msg = f"No se encontró 'empresa' o 'area' en el archivo de configuración: {type(e).__name__} - {e}"
        archivo.log_errores(error_msg)
        return

    topic_sub_nuevo = f"{empresa_actual}/{area_actual}/{mac_local}/down"

    if direccion_topicos["empresa"] is None or direccion_topicos["area"] is None:
        mqtt.subscribe(topic_sub_nuevo)
        direccion_topicos["empresa"] = empresa_actual
        direccion_topicos["area"] = area_actual
        topic_base = f"{empresa_actual}/{area_actual}"
        print(f"Suscrito inicialmente a: {topic_sub_nuevo}")

    elif (empresa_actual != direccion_topicos["empresa"]) or (area_actual != direccion_topicos["area"]):
        topic_sub_anterior = f"{direccion_topicos['empresa']}/{direccion_topicos['area']}/{mac_local}/down"
        mqtt.unsubscribe(topic_sub_anterior)
        mqtt.subscribe(topic_sub_nuevo)
        print(f"Suscrito a nuevo topic: {topic_sub_nuevo}")

        direccion_topicos["empresa"] = empresa_actual
        direccion_topicos["area"] = area_actual
        topic_base = f"{empresa_actual}/{area_actual}"

    else:
        print(f"Sin cambios en empresa/area")

if __name__ == "__main__":
    print("iniciando llamado de enfermeria...")

    lora = LoRaHandler()
    archivo = FileHandler()
    while not internet_ok:
        estado_wifi()
        time.sleep(10)
    trama = TramaHandler()
    mqtt = MQTTClientHandler()

    try:
        mac_local = trama.mac_local
        lora.iniciar_lora()
        mqtt.connect()
        sub_manager()

        tiempo_ultima_inicializacion = time.monotonic()
        intervalo_reinicializacion = 300.0  # 5 minutos

        while True:
            tiempo_actual = time.monotonic()

            # Verificar si hubo error en MQTT o si no esta conectado, y reconectar si es necesario
            if (mqtt.error_flag or (not mqtt.is_connected)):
                estado_wifi()
                if internet_ok:
                    print("Reconectando a MQTT por error o desconexión...")
                    try:
                        mqtt.disconnect()
                    except Exception as e:
                        error_msg = f"Error al desconectar MQTT previo: {type(e).__name__} - {e}"
                        archivo.log_errores(error_msg)
                    try:
                        mqtt.connect()
                        sub_manager()  # volver a suscribirse al último topic guardado
                        mqtt.error_flag = False
                        print("Reconexion MQTT exitosa.")
                    except Exception as e:
                        error_msg = f"Error al reconectar MQTT: {type(e).__name__} - {e}"
                        archivo.log_errores(error_msg)
                        print("Esperando 10 segundos antes de reintentar conexión MQTT...")
                        time.sleep(10)
                else:
                    print("No hay internet, no se intenta reconectar a MQTT.")
            
            if lora.paquete_recibido:
                mensaje = lora.mensaje_recibido
                json_final = trama.procesar(mensaje)

                if json_final is not None:
                    if trama.llamado_text == "sincro":
                        respuesta_codificada = trama.codificar(f"F5,{mac_local}")
                        lora.enviar_lora(respuesta_codificada)
                    else:
                        respuesta_codificada = trama.codificar(trama.mac_remitente)
                        lora.enviar_lora(respuesta_codificada)
                        
                        # Publicar solo si internet está OK, MQTT está conectado y no hay error_flag
                        estado_wifi()
                        if internet_ok and mqtt.is_connected and not mqtt.error_flag:
                            topic_publish = f"{topic_base}/{trama.mac_remitente}/up"
                            try:
                                mqtt.publish(topic_publish, json_final)
                                print(f"Publicado en: {topic_publish}")

                                contador_publicaciones += 1

                                if contador_publicaciones >= 10:
                                    subprocess.run(["clear"])
                                    contador_publicaciones = 0  # reinicio contador
                            except Exception as e:
                                error_msg = f"Error al publicar MQTT: {type(e).__name__} - {e}"
                                archivo.log_errores(error_msg)
                        else:
                            print("No hay conexión a internet, MQTT desconectado o en estado de error, no se publica")

                lora.paquete_recibido = False
                lora.mensaje_recibido = ""

            if mqtt.actualizacion:
                archivo.actualizar_archivo(mqtt.mensaje_recibido)
                sub_manager()
                mqtt.actualizacion = False

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nInterrupcion por teclado. Saliendo...\n")

    except Exception as e:
        error_msg = f"\nError: {e}\n"
        print(error_msg)
        archivo.log_errores(error_msg)

    finally:
        print("Liberando recursos...\n")
        lora.cerrar()
        mqtt.disconnect()
        sys.exit(0)








