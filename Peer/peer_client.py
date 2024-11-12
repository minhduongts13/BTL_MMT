import requests
import socket
import threading
import argparse
import hashlib
import time
import random
from metainfo import *

class TrackerClient:
    def __init__(self, tracker_url, info_hash, peer_id, port):
        self.tracker_url = tracker_url
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.port = port
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.tracker_id = None  # Lưu tracker_id để gửi kèm theo các yêu cầu tiếp theo

    def send_tracker_request(self, event="started"):
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'port': self.port,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.left,
            'event': event,
            'compact': 1
        }

        if self.tracker_id:
            params['tracker_id'] = self.tracker_id  # Gửi lại tracker_id nếu đã nhận được

        try:
            response = requests.get(self.tracker_url, params=params)
            response.raise_for_status()
            
            response_data = response.json()
            self.tracker_id = response_data.get("tracker_id", self.tracker_id)  # Cập nhật tracker_id nếu có
            peer_list = response_data.get("peers", [])
            print(f"Received peers: {peer_list}")
            return peer_list
        except requests.RequestException as e:
            print(f"Error contacting tracker: {e}")
            return []

def create_metainfo():
    metaInfo = Metainfo([r"D:/BTL/BTLMMT/BTL/Peer/sample.txt", r"D:/BTL/BTLMMT/BTL/Peer/sample2.txt"], 512, "https://btl-mmt.onrender.com/announce")
    metaInfo.generate_metainfo()
    return metaInfo.info_hash

def generate_peer_id():
    # Sử dụng prefix mô tả phiên bản của client (8 ký tự đầu tiên)
    prefix = "-PC0001-"  # "PC" là mã client và "0001" là phiên bản

    # Sử dụng thời gian hiện tại và số ngẫu nhiên để tạo chuỗi duy nhất
    unique_string = f"{time.time()}{random.randint(0, 9999)}"
    
    # Tạo một mã hash từ chuỗi duy nhất để có độ dài 12 ký tự còn lại
    hash_unique = hashlib.sha1(unique_string.encode()).hexdigest()[:12]
    
    # Kết hợp prefix với 12 ký tự từ mã hash để tạo peer_id 20 ký tự
    peer_id = prefix + hash_unique
    
    return peer_id

def request_block_from_peer(peer_socket, piece_index, block_index):
    """Gửi yêu cầu tải xuống một block từ peer."""
    request_message = f"Request piece:{piece_index} block:{block_index}"
    peer_socket.send(request_message.encode('utf-8'))
    print(f"Requested piece {piece_index}, block {block_index}")

def handle_peer_response(peer_socket, piece_index):
    """Nhận và xử lý dữ liệu từ peer."""
    try:
        data = peer_socket.recv(1024)
        if data:
            print(f"Received block data for piece {piece_index}")
            return data
    except socket.error as e:
        print(f"Error receiving block data: {e}")
    finally:
        peer_socket.close()

def connect_to_peer_and_download(peer_ip, peer_port, piece_index):
    """Kết nối với peer, thực hiện handshake và tải xuống phần tệp."""
    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer_socket.connect((peer_ip, peer_port))

    # Thực hiện handshake
    peer_socket.send("establish".encode('utf-8'))
    response = peer_socket.recv(1024).decode('utf-8')
    if response == "established":
        print(f"Connection established with {peer_ip}:{peer_port}")

        # Yêu cầu tải từng block trong phần tệp
        for block_index in range(4):  # Giả sử mỗi phần chia làm 4 blocks
            request_block_from_peer(peer_socket, piece_index, block_index)
            block_data = handle_peer_response(peer_socket, piece_index)
            # Lưu block_data vào vị trí tương ứng, cập nhật trạng thái downloaded
    else:
        print(f"Failed to establish connection with {peer_ip}:{peer_port}")

    # Sau khi hoàn tất tải một phần, gửi thông báo "has"
    peer_socket.send("has".encode('utf-8'))
    peer_socket.close()

def download_piece_from_multiple_peers(peer_list, piece_list):
    threads = []
    for i, peer in enumerate(peer_list):
        if i >= len(piece_list):  # Kiểm tra nếu vượt quá số phần tệp cần tải
            break
        peer_ip, peer_port = peer["ip"], peer["port"]
        piece_index = piece_list[i]
        thread = threading.Thread(target=connect_to_peer_and_download, args=(peer_ip, peer_port, piece_index))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
    print("Downloaded all pieces")

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json")
        ip = response.json()["ip"]
        return ip
    except requests.RequestException as e:
        print(f"Error getting public IP: {e}")
        return None

def cli_interface():
    parser = argparse.ArgumentParser(description="P2P File sharing application")
    parser.add_argument("info-hash", type=str, help="The torrent file to download")
    parser.add_argument("--download", action="store_true", help="Start downloading the file")
    parser.add_argument("--upload", action="store_true", help="Start connect tracker to give it the info-hash")
    args = parser.parse_args()

    if args.download:
        if (args.upload):
            info_hash = create_metainfo()
        else:
            info_hash = "aaa"
        tracker_url = "https://btl-mmt.onrender.com/announce"
        peer_id = generate_peer_id()
        tracker_client = TrackerClient(tracker_url, info_hash, peer_id, port=6881)

        # Bắt đầu tải xuống, gửi yêu cầu "started"
        peer_list = tracker_client.send_tracker_request(event="started")
        
        # Danh sách các phần cần tải (ví dụ tải các phần 0, 1, 2)
        piece_list = [0, 1, 2]
        if peer_list:
            download_piece_from_multiple_peers(peer_list, piece_list)
        
        # Gửi yêu cầu "completed" sau khi hoàn tất tải xuống
        tracker_client.send_tracker_request(event="completed")

if __name__ == "__main__":
    cli_interface()
