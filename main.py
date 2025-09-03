import network
import ujson
import time
from client import WebSocketClient

# 🔑 Configura tu WiFi
WIFI_SSID = "HUAWEI-2.4G-94Df"
WIFI_PASS = "xqTKH4X5"

# 🔑 IP de tu PC en la LAN (no localhost)
WS_URL = "ws://192.168.100.3:3000"

ESP32_ID = "esp32_1"

print("Iniciando ESP32...")
# Conectar WiFi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
if not wifi.isconnected():
    print("Conectando a WiFi...")
    wifi.connect(WIFI_SSID, WIFI_PASS)
    timeout = 10
    while not wifi.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1
    
if wifi.isconnected():
    print("\nConectado a WiFi:", wifi.ifconfig())
else:
    print("\nNo se pudo conectar a WiFi. Revisa el SSID y la contraseña.")
    # Si no hay WiFi, no tiene sentido continuar
    while True:
        time.sleep(1)

# Conectar WebSocket
print("Intentando conectar al servidor WebSocket...")
ws = WebSocketClient(WS_URL)
try:
    ws.connect()
    print("Conectado al servidor WebSocket")
    
    # Identificarse
    ws.send(ujson.dumps({"type": "identify", "role": "esp32", "id": ESP32_ID}))
    print("Identificación enviada al servidor")

    while True:
        try:
            msg = ws.recv()
            if msg:
                print(f"Mensaje recibido: {msg}")
                data = ujson.loads(msg)
                print(data['msg'])  
                if data.get("type") == "from_react":
                    cmd = data.get("command")
                    print(f"Comando '{cmd}' recibido.")
                    
                    # Responder con ACK
                    ws.send(ujson.dumps({
                        "type": "to_react",
                        "data": f"ESP32 {ESP32_ID} ejecutó {cmd}"
                    }))

        except Exception as e:
            print(f"Error durante la comunicación: {e}")
            time.sleep(2)

except Exception as e:
    print(f"Error al conectar al servidor WebSocket: {e}")
    print("Reiniciando en 5 segundos...")
    time.sleep(5)
    import machine
    machine.reset()