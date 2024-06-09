import socket
import threading
import json
import signal
import sys

class ChatCoordinator:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.sessions = {}
        self.lock = threading.Lock()

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        print(f"Coordinator running on {self.host}:{self.port}")
        signal.signal(signal.SIGINT, self.shutdown)
        threading.Thread(target=self.handle_client_requests, daemon=True).start()

    def handle_client_requests(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                request = json.loads(data.decode())
                print(f"Received request: {request} from {addr}")
                if request['action'] == 'start':
                    self.start_chat_session(addr)
                elif request['action'] == 'join':
                    self.join_chat_session(request['session_id'], addr)
            except Exception as e:
                print(f"Error handling client request: {e}")

    def start_chat_session(self, client_addr):
        session_id = len(self.sessions) + 1
        chat_server = ChatServer(session_id)
        threading.Thread(target=chat_server.start, daemon=True).start()
        with self.lock:
            self.sessions[session_id] = {'server': chat_server, 'clients': []}
        response = {'session_id': session_id, 'host': chat_server.host, 'port': chat_server.port}
        print(f"Starting chat session {session_id} at {chat_server.host}:{chat_server.port}")
        self.sock.sendto(json.dumps(response).encode(), client_addr)

    def join_chat_session(self, session_id, client_addr):
        with self.lock:
            if session_id in self.sessions:
                chat_server = self.sessions[session_id]['server']
                response = {'host': chat_server.host, 'port': chat_server.port}
                print(f"Client {client_addr} joining session {session_id} at {chat_server.host}:{chat_server.port}")
                self.sock.sendto(json.dumps(response).encode(), client_addr)
            else:
                self.sock.sendto(json.dumps({'error': 'Session not found'}).encode(), client_addr)

    def shutdown(self, signum, frame):
        print("\nShutting down the coordinator.")
        self.sock.close()
        sys.exit(0)

class ChatServer:
    def __init__(self, session_id, host='127.0.0.1', port=0):
        self.session_id = session_id
        self.host = host
        self.port = port
        self.clients = []
        self.lock = threading.Lock()

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.host, self.port = self.sock.getsockname()
        self.sock.listen(5)
        print(f"Chat server {self.session_id} running on {self.host}:{self.port}")
        while True:
            client_sock, client_addr = self.sock.accept()
            print(f"Client {client_addr} connected to session {self.session_id}")
            with self.lock:
                self.clients.append(client_sock)
            threading.Thread(target=self.handle_client_connection, args=(client_sock,), daemon=True).start()

    def handle_client_connection(self, client_sock):
        while True:
            try:
                data = client_sock.recv(1024)
                if not data:
                    break
                print(f"Received message: {data.decode()}")
                self.broadcast_message(data, client_sock)
            except Exception as e:
                print(f"Error handling client connection: {e}")
                break
        with self.lock:
            self.clients.remove(client_sock)
        client_sock.close()

    def broadcast_message(self, message, sender_sock):
        with self.lock:
            for client in self.clients:
                if client != sender_sock:
                    try:
                        client.send(message)
                        print(f"Broadcasting message: {message.decode()} to {client.getpeername()}")
                    except Exception as e:
                        print(f"Error broadcasting message: {e}")

if __name__ == '__main__':
    coordinator = ChatCoordinator()
    coordinator.start()
    signal.pause()
