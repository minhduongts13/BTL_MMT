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
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'port': self.port,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.left,
            'event': event,
            'compact': 1,
            'public_ip': public_ip,  # Gửi IP công khai của client
            'local-ip' : local_ip
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



def handle_peer_response(peer_socket, piece_index):
    """Nhận và xử lý dữ liệu từ peer."""
    try:
        data = peer_socket.recv(1024)
        if data:
            print(f"Received block data for piece {piece_index}")
            return data
    except socket.error as e:
        print(f"Error receiving block data: {e}")

def connect_to_peer_and_download(peer_ip, peer_port, piece_index, download_manager):
    try:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_ip, peer_port))

        peer_socket.send("establish".encode('utf-8'))
        response = peer_socket.recv(1024).decode('utf-8')
        if response == "established":
            print(f"Connection established with {peer_ip}:{peer_port}")

        request_message = f"Request piece:{piece_index}"
        peer_socket.send(request_message.encode('utf-8'))
        print(f"Requested piece {piece_index}")
        
        piece_data = peer_socket.recv(1024)  # Nhận dữ liệu
        if piece_data:
            print(f"Received block data for piece {piece_index}")
            download_manager.save_piece(piece_index, piece_data)

        # Gửi lệnh kết thúc
        peer_socket.send("end".encode('utf-8'))
    except socket.error as e:
        print(f"Error connecting to peer {peer_ip}:{peer_port} - {e}")
    finally:
        peer_socket.close()

def peer_has_piece(peer_ip, peer_port, piece_index):
    try:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_ip, peer_port))

        # Gửi yêu cầu kiểm tra piece
        request_message = f"has_piece:{piece_index}"
        peer_socket.send(request_message.encode('utf-8'))
        
        # Nhận phản hồi từ peer
        response = peer_socket.recv(1024).decode('utf-8')
        if response == "yes":
            print(f"Peer {peer_ip}:{peer_port} has piece {piece_index}")
        else:
            print(f"Peer {peer_ip}:{peer_port} does not have piece {piece_index}")

        # Gửi lệnh kết thúc
        peer_socket.send("end".encode('utf-8'))
        return response == "yes"  # Nếu peer có piece này, trả về True
    except socket.error as e:
        print(f"Error contacting peer {peer_ip}:{peer_port} - {e}")
        return False
    finally:
        peer_socket.close()


def download_piece_from_multiple_peers(peer_list, total_pieces, download_manager):
    threads = []
    invalid_requests = 0  # Đếm số lượng yêu cầu không hợp lệ
    max_invalid_requests = 10  # Ngưỡng tối đa cho phép

    while not download_manager.is_file_complete():
        for piece_index in range(total_pieces):
            if download_manager.has_piece(piece_index):
                continue

            if piece_index >= download_manager.total_pieces:
                print(f"Skipping invalid piece index: {piece_index}")
                invalid_requests += 1
                if invalid_requests > max_invalid_requests:
                    print("Too many invalid requests. Exiting.")
                    return
                continue

            for peer in peer_list:
                peer_ip, peer_port, peer_local_ip = peer["ip"], peer["port"], peer['local-ip']

                if get_public_ip() == peer_ip:
                    peer_ip = peer_local_ip

                if peer_has_piece(peer_ip, peer_port, piece_index):
                    thread = threading.Thread(
                        target=connect_to_peer_and_download, 
                        args=(peer_ip, peer_port, piece_index, download_manager)
                    )
                    threads.append(thread)
                    thread.start()
                    break

        for thread in threads:
            thread.join()

    print("Downloaded all pieces.")



def run_server(download_manager, metainfo_data, port):
    peer_server = Peer_Server(download_manager, metainfo_data)
    peer_server.peer_server(port)

def send_stopped_event(tracker_client):
    tracker_client.send_tracker_request(event="stopped")
    print("Sent 'stopped' event to tracker.")

def run_server_in_thread(download_manager, metainfo_data, port):
    """Khởi động server trong một thread riêng biệt."""
    server_thread = threading.Thread(target=run_server, args=(download_manager, metainfo_data, port))
    server_thread.daemon = True  # Đảm bảo thread dừng khi main thread thoát
    server_thread.start()

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', 0))  # Bind với cổng 0 để hệ thống chọn cổng tự do
        return s.getsockname()[1]  # Lấy cổng mà hệ thống đã chọn


def cli_interface():
    parser = argparse.ArgumentParser(description="P2P File sharing application")

    # Tạo nhóm tùy chọn loại trừ lẫn nhau
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true", help="Start downloading the file")
    group.add_argument("--upload", action="store_true", help="Start connecting to the tracker to share info-hash")

    args = parser.parse_args()

    if args.download:
        info_hash = input("Enter the info-hash of the file that you want to download: ")
        # Thông tin tracker
        tracker_url = "https://btl-mmt-pma6.onrender.com/announce"
        peer_id = generate_peer_id()
        port = get_free_port()
        tracker_client = TrackerClient(tracker_url, info_hash, peer_id, port)

        # Gửi yêu cầu "started" đến tracker và nhận danh sách peers
        peer_list = tracker_client.send_tracker_request(event="started")
        # Yêu cầu metainfo từ một peer đầu tiên
        if peer_list:
            first_peer = peer_list[0]
            peer_ip = first_peer['ip']
            if get_public_ip() == first_peer['ip']:
                # continue
                peer_ip = first_peer['local-ip']
            metainfo_data = request_metainfo_from_peer(peer_ip, first_peer["port"])
            if metainfo_data:
                total_pieces, piece_length, files = len(metainfo_data['info']['pieces']), metainfo_data['info']['piece length'], metainfo_data['info']['files'] 
                download_manager = DownloadManager(total_pieces, piece_length, files)
                # Bắt đầu tải xuống từ nhiều peers
                run_server_in_thread(download_manager, metainfo_data, port)
                download_piece_from_multiple_peers(peer_list, total_pieces, download_manager)
                
                # Sau khi tải xong, gửi yêu cầu "completed" đến tracker
                tracker_client.send_tracker_request(event="completed")
                download_manager.assemble2()
            else:
                print("Failed to retrieve metainfo from peer.")
        else:
            print("No peers available to download from.")
    else:
        metaInfo = create_metainfo()
        info_hash = metaInfo[0]
        port = get_free_port()
        print(info_hash)
        metainfo_data = metaInfo[1]
        total_pieces, piece_length, files = len(metainfo_data['info']['pieces']), metainfo_data['info']['piece length'], metainfo_data['info']['files'] 
        tracker_url = "https://btl-mmt-pma6.onrender.com/announce"
        peer_id = generate_peer_id()
        tracker_client = TrackerClient(tracker_url, info_hash, peer_id, port)
        peer_list = tracker_client.send_tracker_request(event="started")
        tracker_client.send_tracker_request(event="completed")
        download_manager = DownloadManager(total_pieces, piece_length, files, True)
        run_server(download_manager, metainfo_data, port)

    atexit.register(send_stopped_event, tracker_client)

if __name__ == "__main__":
    cli_interface()
