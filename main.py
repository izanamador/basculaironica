import asyncio
import binascii
import streamlit as st
from gtts import gTTS
import tempfile
import os
from bleak import BleakScanner
import json
import random
import time

# Variables para almacenar el último peso y el tiempo en que se empezó a recibir
last_weight = None
stable_weight_time = None
stable_duration = 3  # Tiempo en segundos para considerar que el peso es estable

# Función para obtener los datos de la báscula
async def get_scale_data(address: str):
    data = {"weight": None, "impedance": None}
    stop_event = asyncio.Event()

    def callback(device, advertising_data):
        if device.address.lower() == address.lower():
            # Decodificar los datos de la báscula
            data_hex = binascii.b2a_hex(advertising_data.service_data['0000181b-0000-1000-8000-00805f9b34fb']).decode('ascii')
            byte12 = data_hex[-2:]  # Peso (byte menos significativo)
            byte11 = data_hex[-4:-2]  # Peso (byte más significativo)
            weight = (int(byte12 + byte11, 16)) / 200
            data["weight"] = round(weight, 2)
            byte09 = data_hex[-6:-4]  # Impedancia
            byte10 = data_hex[-8:-6]  # Impedancia
            data["impedance"] = int(byte09 + byte10, 16)
            stop_event.set()

    async with BleakScanner(callback) as scanner:
        await stop_event.wait()
    return data

# Función para generar archivo de audio con st.audio
def generar_audio(message):
    try:
        # Crear un archivo temporal de audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            tts = gTTS(text=message, lang='es')
            tts.save(temp_audio.name)
        
        # Retornar el archivo de audio temporal
        return temp_audio.name

    except Exception as e:
        print(f"Error al generar el audio: {e}")
        return None

# Función de Streamlit para mostrar los datos
def main():
    global last_weight, stable_weight_time  # Usamos las variables globales para mantener el estado del último peso y el tiempo

    # Mostrar logo y subtítulo
    st.image("logo.png")

    # Campo de texto para introducir la dirección MAC
    mac_address = st.text_input("Introduce la dirección MAC de la báscula", value="5C:CA:D3:96:14:EC")

    # Botón de comenzar
    if st.button("Comenzar"):
        # Ciclo infinito para obtener datos continuamente
        while True:
            # Ejecutar la función asincrónica para obtener los datos de la báscula
            scale_data = asyncio.run(get_scale_data(mac_address))

            # Leer mensajes desde mensajes.json
            try:
                with open('mensajes.json', 'r', encoding='utf-8') as file:
                    mensajes = json.load(file)
                
                # Verificar si la clave 'mensajes' existe y es una lista
                if 'mensajes' in mensajes and isinstance(mensajes['mensajes'], list):
                    # Seleccionar un mensaje aleatorio
                    mensaje_ironico = random.choice(mensajes['mensajes'])
                else:
                    mensaje_ironico = "Mensaje no disponible"
            except Exception as e:
                print(f"Error al leer el archivo de mensajes: {e}")
                mensaje_ironico = "Mensaje no disponible"

            # Comprobar si se ha recibido un peso
            if scale_data["weight"] is not None:
                weight = scale_data["weight"]

                # Si es la primera vez o el peso ha cambiado
                if weight != last_weight:
                    last_weight = weight  # Actualizamos el peso actual
                    stable_weight_time = time.time()  # Reiniciamos el tiempo de estabilidad

                # Si el peso se ha mantenido estable durante el tiempo requerido
                elif stable_weight_time and (time.time() - stable_weight_time >= stable_duration):
                    # Generar siempre un mensaje irónico independientemente del peso
                    message = f"Pesas {weight} kilos. {mensaje_ironico}"
                    
                    # Mostrar el mensaje en la interfaz
                    st.write(message)
                    
                    # Generar el archivo de audio y mostrar el botón de reproducción
                    audio_path = generar_audio(message)
                    if audio_path:
                        st.audio(audio_path, format="audio/mp3")

                    stable_weight_time = None  # Reiniciar la cuenta para futuras lecturas estables
            else:
                st.write("No se pudo obtener los datos de la báscula")

if __name__ == "__main__":
    main()
