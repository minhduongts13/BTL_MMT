import socket
import threading
import json
import hashlib
import time
from utils import *


class Peer_Server:
    def __init__(self, download_manager, metainfo):
        self.download_manager = download_manager
        self.metainfo = metainfo

    def peer_server(self, port = 0):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', port))  # Lắng nghe trên tất cả các địa chỉ
        server_socket.listen(5)
        print(f"Peer server is listening on port {port}")
        while True:
            try:
                peer_socket, peer_addr = server_socket.accept()
                print(f"Connected with peer: {peer_addr}")
                thread = threading.Thread(target=self.handle_peer, args=(peer_socket,))
                thread.daemon = True  # Đảm bảo thread dừng khi main thread thoát
                thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")


    def handle_peer(self, peer_socket):
        try:
            while True:
                # Nhận yêu cầu từ peer khác
                request = peer_socket.recv(1024).decode('utf-8')
                if not request:
                    break  # Kết thúc nếu nhận được dữ liệu rỗng
                print(f"Received request: {request}")
                
                if request == "request_metainfo":
                    self.send_metainfo(peer_socket)
                elif request.startswith("Request piece:"):
                    piece_index = int(request.split(":")[1])
                    print(f"Piece index: {piece_index}")
                    self.send_piece(peer_socket, piece_index)
                elif request.startswith("has_piece:"):
                    piece_index = int(request.split(":")[1])
                    if self.download_manager.has_piece(piece_index):
                        peer_socket.send("yes".encode('utf-8'))
                    else:
                        peer_socket.send("no".encode('utf-8'))
                elif request == "establish":
                    peer_socket.send("established".encode('utf-8'))
                elif request == "end":
                    print("Received end signal, closing connection.")
                    break
                else:
                    peer_socket.send("Invalid request".encode('utf-8'))
                    print("Invalid request received.")
        except Exception as e:
            print(f"Error handling peer request: {e}")
        finally:
            peer_socket.close()


    def send_metainfo(self, peer_socket):
        try:
            if not self.metainfo:
                raise ValueError("Metainfo is missing or invalid.")
            metainfo_data = json.dumps(self.metainfo).encode('utf-8')
            for i in range(0, len(metainfo_data), 1024):
                peer_socket.send(metainfo_data[i:i+1024])
                print(f"Sending metainfo data chunk: {metainfo_data[i:i+1024]}")
            # Gửi thông báo kết thúc
            peer_socket.send("END".encode('utf-8'))
            print("Sent metainfo to peer.")
        except Exception as e:
            print(f"Error sending metainfo: {e}")




    def send_piece(self, peer_socket, piece_index):
        """Gửi dữ liệu piece cho peer khác nếu có sẵn."""
        try:
            if not self.download_manager.has_piece(piece_index):
                peer_socket.send("Piece not available".encode('utf-8'))
                print(f"Piece {piece_index} not available.")
                return

            piece_data = self.download_manager.get_piece_data(piece_index)
            peer_socket.sendall(piece_data)
            print(f"Sent piece {piece_index} to peer.")
        except Exception as e:
            print(f"Error sending piece {piece_index}: {e}")




