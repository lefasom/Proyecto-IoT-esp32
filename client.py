# client.py
import usocket
import ubinascii
import hashlib
import time
import urandom

class WebSocketClient:
    def __init__(self, url):
        self.url = url
        self.host, self.port = self.parse_url(url)
        self.sock = None
        self.connected = False

    def parse_url(self, url):
        try:
            url = url.split("://")[1]
            if ":" in url:
                host, port = url.split(":")
                return host, int(port)
            else:
                return url, 80
        except Exception as e:
            print(f"Error al parsear URL: {e}")
            raise e

    def connect(self):
        try:
            addr_info = usocket.getaddrinfo(self.host, self.port)
            addr = addr_info[0][-1]
            print(f"Resolviendo host {self.host} a {addr}")

            self.sock = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
            print("Socket creado. Conectando...")
            self.sock.connect(addr)
            
            # WebSocket handshake
            # Genera 16 bytes de datos aleatorios en 4 partes de 32 bits
            bits = urandom.getrandbits(32) | (urandom.getrandbits(32) << 32) | \
                   (urandom.getrandbits(32) << 64) | (urandom.getrandbits(32) << 96)
            key_bytes = bits.to_bytes(16, 'big')

            key_str = ubinascii.b2a_base64(key_bytes).strip().decode('utf-8')
            
            print(f"Generando Sec-WebSocket-Key: {key_str}")

            request = b"GET / HTTP/1.1\r\n" \
                      + b"Host: " + self.host.encode('utf-8') + b"\r\n" \
                      + b"Upgrade: websocket\r\n" \
                      + b"Connection: Upgrade\r\n" \
                      + b"Sec-WebSocket-Key: " + key_str.encode('utf-8') + b"\r\n" \
                      + b"Sec-WebSocket-Version: 13\r\n\r\n"
            
            print("Enviando handshake...")
            self.sock.send(request)
            
            response = self.sock.recv(1024)
            print("Respuesta recibida:", response)
            if b"101 Switching Protocols" in response:
                print("Handshake exitoso!")
                self.connected = True
            else:
                raise Exception("Handshake fallido")

        except Exception as e:
            self.close()
            raise e
    def send(self, data):
        if not self.connected:
            return
        
        # Enmarcar el mensaje (con máscara de bytes)
        payload = data.encode('utf-8')
        length = len(payload)
        header = bytearray()
        
        # Opcode 1 (texto) y bit de fin
        header.append(0x81)
        
        # Longitud
        if length < 126:
            header.append(length | 0x80)  # Aquí se añade el bit de máscara
        else:
            header.append(126 | 0x80)
            header.append((length >> 8) & 0xFF)
            header.append(length & 0xFF)
        
        # Aplicar máscara (obligatorio para clientes)
        mask = urandom.getrandbits(32).to_bytes(4, 'big')
        header.extend(mask)
        masked_payload = bytearray(payload)
        for i in range(length):
            masked_payload[i] ^= mask[i % 4]
            
        self.sock.send(header + masked_payload)
    
    def recv(self):
        if not self.connected:
            return None
        
        try:
            # Leer el encabezado
            header = self.sock.recv(2)
            if not header:
                return None
            
            # Desempaquetar
            fin = header[0] & 0x80
            opcode = header[0] & 0x0f
            masked = header[1] & 0x80
            length = header[1] & 0x7f

            if opcode != 1:  # Ignorar pings, etc.
                return None
            
            if length == 126:
                length_bytes = self.sock.recv(2)
                length = int.from_bytes(length_bytes, 'big')

            if masked:
                mask = self.sock.recv(4)
            
            # Leer el payload
            payload = self.sock.recv(length)
            
            if masked:
                unmasked_payload = bytearray(payload)
                for i in range(len(payload)):
                    unmasked_payload[i] ^= mask[i % 4]
                return unmasked_payload.decode('utf-8')
            
            return payload.decode('utf-8')

        except Exception as e:
            self.close()
            raise e

    def close(self):
        if self.sock:
            self.sock.close()
        self.connected = False
        self.sock = None