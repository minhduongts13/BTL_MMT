import socket
import threading
import json
import hashlib
from utils import DownloadManager


class Peer_Server:
    def __init__(self, download_manager, metainfo):
        self.download_manager = download_manager
        self.metainfo = metainfo

    def peer_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', 6881))
        server_socket.listen(5)
        print("Peer server is listening on port 6881")

        while True:
            peer_socket, peer_addr = server_socket.accept()
            print(f"Connected with peer: {peer_addr}")
            
            # Tạo thread để xử lý từng yêu cầu từ peer
            thread = threading.Thread(target=self.handle_peer, args=(peer_socket,))
            thread.start()

    def handle_peer(self, peer_socket):
        try:
            # Nhận yêu cầu từ peer khác
            request = peer_socket.recv(1024).decode('utf-8')
            print(f"Received request: {request}")
            
            # Xử lý yêu cầu metainfo
            if request == "request_metainfo":
                self.send_metainfo(self, peer_socket)

            # Xử lý yêu cầu tải piece
            elif request.startswith("Request piece:"):
                piece_index = int(request.split(":")[1])
                self.send_piece(self, peer_socket, piece_index)
                
            elif request.startswith("has_piece:"):
                piece_index = int(request.split(":")[1])
                if self.download_manager.has_piece(piece_index):
                    peer_socket.send("yes".encode('utf-8'))
                else:
                    peer_socket.send("no".encode('utf-8'))
            else:
                peer_socket.send("Invalid request".encode('utf-8'))
                print("Invalid request received.")
        except Exception as e:
            print(f"Error handling peer request: {e}")
        finally:
            peer_socket.close()

    def send_metainfo(self, peer_socket):
        """Gửi metainfo dưới dạng JSON đến peer."""
        try:
            metainfo_data = json.dumps(self.metainfo).encode('utf-8')
            peer_socket.sendall(metainfo_data)
            print("Sent metainfo to peer.")
        except Exception as e:
            print(f"Error sending metainfo: {e}")

    def send_piece(self, peer_socket, piece_index):
        """Gửi dữ liệu piece cho peer khác nếu có sẵn."""
        if self.download_manager.has_piece(piece_index):
            piece_data = self.download_manager.get_piece_data(piece_index)
            try:
                peer_socket.sendall(piece_data)  # Gửi toàn bộ dữ liệu piece
                print(f"Sent piece {piece_index} to peer.")
            except Exception as e:
                print(f"Error sending piece {piece_index}: {e}")
        else:
            peer_socket.send("Piece not available".encode('utf-8'))
            print(f"Piece {piece_index} not available.")



