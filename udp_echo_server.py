import socket

HOST = "0.0.0.0"
PORT = 5005

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((HOST, PORT))

print("UDP Echo Server listening on port", PORT)

try:
    while True:
        data, address = server.recvfrom(1024)
        print("Received:", data.decode(errors="replace"))
        server.sendto(data, address)
except KeyboardInterrupt:
    print("Server stopped")
finally:
    server.close()
