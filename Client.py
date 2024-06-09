import socket
import threading
import json
import signal
import sys

class ChatClient:
    def __init__(self, coordinator_host='127.0.0.1', coordinator_port=5000):
        self.coordinator_host = coordinator_host
        self.coordinator_port = coordinator_port
        self.chat_sock = None

    def start(self):
        signal.signal(signal.SIGINT, self.shutdown)
        while True:
            action = input("Enter action (start/join): ")
            if action == 'start':
                self.start_session()
            elif action == 'join':
                session_id = int(input("Enter session ID to join: "))
                self.join_session(session_id)
            elif action == 'exit':
                self.shutdown()
                break

    def start_session(self):
        request = {'action': 'start'}
        self.send_udp_request(request)

    def join_session(self, session_id):
        request = {'action': 'join', 'session_id': session_id}
        self.send_udp_request(request)

    def send_udp_request(self, request):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(request).encode(), (self.coordinator_host, self.coordinator_port))
            data, _ = sock.recvfrom(1024)
            response = json.loads(data.decode())
            print(f"Received response: {response}")
            if 'error' in response:
                print(f"Error: {response['error']}")
            else:
                self.connect_to_chat_server(response['host'], response['port'])
        except Exception as e:
            print(f"Error sending UDP request: {e}")

    def connect_to_chat_server(self, host, port):
        try:
            self.chat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chat_sock.connect((host, port))
            print(f"Connected to chat server at {host}:{port}")
            threading.Thread(target=self.receive_messages, daemon=True).start()
            self.send_messages()
        except Exception as e:
            print(f"Error connecting to chat server: {e}")

    def send_messages(self):
        while True:
            message = input()
            if message == 'exit':
                self.chat_sock.close()
                break
            try:
                self.chat_sock.send(message.encode())
                print(f"Sent message: {message}")
            except Exception as e:
                print(f"Error sending message: {e}")

    def receive_messages(self):
        while True:
            try:
                data = self.chat_sock.recv(1024)
                if not data:
                    break
                print(f"Received message: {data.decode()}")
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def shutdown(self, signum=None, frame=None):
        print("\nShutting down the client.")
        if self.chat_sock:
            self.chat_sock.close()
        sys.exit(0)

if __name__ == '__main__':
    client = ChatClient()
    client.start()
