import requests
import socket
import threading
import argparse
import hashlib
import time
import atexit
import random
from utils import *
from peer_server import Peer_Server

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
        public_ip = get_public_ip()
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'port': self.port,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.left,
            'event': event,
            'compact': 1,
            'public_ip': public_ip  # Gửi IP công khai của client
        }

        if self.tracker_id:
            params['tracker_id'] = self.tracker_id

        try:
            response = requests.get(self.tracker_url, params=params)
            response.raise_for_status()
            
            response_data = response.json()
            self.tracker_id = response_data.get("tracker_id", self.tracker_id)
            peer_list = response_data.get("peers", [])
            print(f"Received peers: {peer_list}")
            return peer_list
        except requests.RequestException as e:
            print(f"Error contacting tracker: {e}")
            return []

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

def request_piece_from_peer(peer_socket, piece_index):
    """Gửi yêu cầu tải xuống một block từ peer."""
    request_message = f"Request piece:{piece_index}"
    peer_socket.send(request_message.encode('utf-8'))
    print(f"Requested piece {piece_index}")

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

def connect_to_peer_and_download(peer_ip, peer_port, piece_index, download_manager):
    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer_socket.connect((peer_ip, peer_port))

    peer_socket.send("establish".encode('utf-8'))
    response = peer_socket.recv(1024).decode('utf-8')
    if response == "established":
        print(f"Connection established with {peer_ip}:{peer_port}")

    request_piece_from_peer(peer_socket, piece_index)
    piece_data = handle_peer_response(peer_socket, piece_index)
    
    # Lưu block_data vào DownloadManager
    download_manager.save_piece(piece_index, piece_data)

    # Gửi thông báo 'has' ngay sau khi tải xong
    peer_socket.send(f"has_piece:{piece_index}".encode('utf-8'))
    print(f"Sent 'has' message for piece {piece_index}.")

    peer_socket.close()

def peer_has_piece(peer_ip, peer_port, piece_index):
    """Gửi yêu cầu đến peer để kiểm tra xem họ có piece không."""
    try:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_ip, peer_port))

        # Gửi yêu cầu kiểm tra piece
        request_message = f"has_piece:{piece_index}"
        peer_socket.send(request_message.encode('utf-8'))
        
        # Nhận phản hồi từ peer
        response = peer_socket.recv(1024).decode('utf-8')
        peer_socket.close()
        
        return response == "yes"  # Nếu peer có piece này, trả về True
    except socket.error as e:
        print(f"Error contacting peer {peer_ip}:{peer_port} - {e}")
        return False


def download_piece_from_multiple_peers(peer_list, total_pieces, download_manager):
    threads = []
    while not download_manager.is_file_complete():
        for piece_index in range(total_pieces):
            # Nếu đã có piece này, không cần tải lại
            if download_manager.has_piece(piece_index):
                continue

            for peer in peer_list:
                # Peer đó là chính client
                peer_ip, peer_port = peer["ip"], peer["port"]
                if get_public_ip() == peer_ip:
                    continue
                
                # Kiểm tra xem peer có piece này không trước khi tải
                if peer_has_piece(peer_ip, peer_port, piece_index):
                    thread = threading.Thread(
                        target=connect_to_peer_and_download, 
                        args=(peer_ip, peer_port, piece_index, download_manager, "downloaded_file.txt")
                    )
                    threads.append(thread)
                    thread.start()
                    break  # Chuyển sang piece tiếp theo sau khi tìm thấy một peer có piece này

    for thread in threads:
        thread.join()
    print("Downloaded all pieces")

def run_server(download_manager, metainfo_data):
    peer_server = Peer_Server(download_manager, metainfo_data)
    peer_server.peer_server()

def send_stopped_event(tracker_client):
    """Gửi sự kiện 'stopped' đến tracker khi peer thoát."""
    tracker_client.send_tracker_request(event="stopped")
    print("Sent 'stopped' event to tracker.")


def cli_interface():
    parser = argparse.ArgumentParser(description="P2P File sharing application")
    parser.add_argument("info_hash", type=str, help="The torrent file to download")
    parser.add_argument("--download", action="store_true", help="Start downloading the file")
    parser.add_argument("--upload", action="store_true", help="Start connect tracker to give it the info-hash")
    args = parser.parse_args()

    if args.download:
        # Tạo metainfo nếu upload được yêu cầu
        if args.upload:
            info_hash = create_metainfo()
        else:
            info_hash = args.info_hash
        
        # Thông tin tracker
        tracker_url = "https://btl-mmt-pma6.onrender.com/announce"
        peer_id = generate_peer_id()
        tracker_client = TrackerClient(tracker_url, info_hash, peer_id, port=6881)

        # Gửi yêu cầu "started" đến tracker và nhận danh sách peers
        peer_list = tracker_client.send_tracker_request(event="started")

        # Yêu cầu metainfo từ một peer đầu tiên
        if peer_list:
            first_peer = peer_list[0]
            metainfo_data = request_metainfo_from_peer(first_peer["ip"], first_peer["port"])
            if metainfo_data:
                total_pieces, piece_size, files = len(metainfo_data['info']['pieces']), metainfo_data['info']['piece length'], metainfo_data['info']['files'] 
                download_manager = DownloadManager(total_pieces, files)
                # Bắt đầu tải xuống từ nhiều peers
                download_piece_from_multiple_peers(peer_list, total_pieces, download_manager)
                
                # Sau khi tải xong, gửi yêu cầu "completed" đến tracker
                tracker_client.send_tracker_request(event="completed")
                
            else:
                print("Failed to retrieve metainfo from peer.")
        else:
            print("No peers available to download from.")
        atexit.register(send_stopped_event, tracker_client)


if __name__ == "__main__":
    cli_interface()
