import hashlib
import json
import os
import requests
import socket
import hashlib
from file_manager import assemble_file  

class DownloadManager:
    def __init__(self, total_pieces, files):
        self.piece_status = {i: {'data': None, 'downloaded': False} for i in range(total_pieces)}
        self.total_pieces = total_pieces
        self.files = files

    def save_piece(self, piece_index, piece_data):
        """Lưu piece vào bộ nhớ và đánh dấu đã tải xong."""
        if not self.piece_status[piece_index]['downloaded']:
            self.piece_status[piece_index]['data'] = piece_data
            self.piece_status[piece_index]['downloaded'] = True
            print(f"Saved piece {piece_index}.")

    def is_file_complete(self):
        """Kiểm tra nếu tất cả các pieces đã được tải xong."""
        return all(self.piece_status[i]['downloaded'] for i in range(self.total_pieces))

    def has_piece(self, piece_index):
        """Kiểm tra xem piece đã được tải xong chưa."""
        return self.piece_status[piece_index]['downloaded']

    def assemble(self):
        """Ghép các pieces thành tệp hoàn chỉnh, hỗ trợ nhiều tệp."""
        if not self.is_file_complete():
            print("File download is not yet complete.")
            return None

        offset = 0
        for file in self.files:
            file_length = file["length"]
            file_path = file["path"][0]
            with open(file_path, "wb") as f:
                while file_length > 0:
                    piece_index = offset // self.piece_status[0]['length']
                    piece_offset = offset % self.piece_status[0]['length']
                    piece_data = self.piece_status[piece_index]['data']
                    write_size = min(file_length, len(piece_data) - piece_offset)
                    f.write(piece_data[piece_offset:piece_offset + write_size])
                    offset += write_size
                    file_length -= write_size

        print("Files assembled successfully.")

    def get_piece_data(self, piece_index):
        return self.piece_status[piece_index]['data']

class Metainfo:
    def __init__(self, file_paths, piece_length, tracker_url):
        self.file_paths = file_paths
        self.piece_length = piece_length
        self.tracker_url = tracker_url
        self.pieces = []
        self.files = []
        self.info_hash = None

    def generate_pieces(self):
        # Duyệt qua từng tệp và tính toán hash của các phần
        for file_path in self.file_paths:
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                while True:
                    piece_data = f.read(self.piece_length)
                    if not piece_data:
                        break
                    piece_hash = hashlib.sha1(piece_data).hexdigest()
                    self.pieces.append(piece_hash)
            # Thêm thông tin tệp vào danh sách files
            self.files.append({"length": file_size, "path": [file_path]})

    def generate_metainfo(self):
        # Gọi hàm generate_pieces để tính toán pieces và files
        self.generate_pieces()
        
        # Tạo từ điển metainfo
        metainfo_data = {
            "info": {
                "piece length": self.piece_length,
                "pieces": self.pieces,
                "files": self.files
            },
            "announce": self.tracker_url
        }
        
        # Tạo mã hash duy nhất (info_hash) đại diện cho tệp
        info_serialized = json.dumps(metainfo_data["info"], sort_keys=True).encode("utf-8")
        self.info_hash = hashlib.sha1(info_serialized).hexdigest()
        
        # Lưu vào file .torrent
        torrent_file_path = f"{self.file_paths[0]}.torrent"
        with open(torrent_file_path, "w") as f:
            json.dump(metainfo_data, f)
        
        print(f"Metainfo file created at: {torrent_file_path}")
        return torrent_file_path
    
    def load_from_data(self, data):
        # Giải mã dữ liệu và gán giá trị cho các thuộc tính
        # Ví dụ: self.total_pieces, self.piece_size, self.file_size
        metainfo = json.loads(data.decode('utf-8'))  # Giả sử dữ liệu là JSON
        self.total_pieces = metainfo.get("total_pieces")
        self.piece_size = metainfo.get("piece_size")
        self.file_size = metainfo.get("file_size")

def create_metainfo():
    metaInfo = Metainfo([r"D:/BTL/BTLMMT/BTL_MMT/Peer/sample.txt", r"D:/BTL/BTLMMT/BTL_MMT/Peer/sample2.txt"], 512, "https://btl-mmt.onrender.com/announce")
    metaInfo.generate_metainfo()
    return metaInfo.info_hash

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json")
        ip = response.json()["ip"]
        return ip
    except requests.RequestException as e:
        print(f"Error getting public IP: {e}")
        return None
    
def save_piece_to_file(piece_data, piece_index, file_path):
    """Lưu phần đã tải xong vào tệp."""
    with open(file_path, 'r+b') as f:
        # Tính toán vị trí ghi dựa trên chỉ số phần (mỗi phần có kích thước cố định)
        f.seek(piece_index * len(piece_data))
        f.write(piece_data)
    print(f"Saved piece {piece_index} to {file_path}")

def create_empty_file(file_path, total_size):
    """Tạo một tệp trống với kích thước xác định trước."""
    with open(file_path, 'wb') as f:
        f.seek(total_size - 1)
        f.write(b'\0')

def request_metainfo_from_peer(peer_ip, peer_port):
    """Gửi yêu cầu đến peer để lấy thông tin metainfo."""
    try:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_ip, peer_port))
        
        # Gửi yêu cầu metainfo
        peer_socket.send("request_metainfo".encode('utf-8'))
        
        # Nhận dữ liệu metainfo từ peer
        metainfo_data = b""
        while True:
            chunk = peer_socket.recv(4096)  # Nhận dữ liệu thành từng phần
            if not chunk:  # Nếu không có dữ liệu nào còn lại thì dừng
                break
            metainfo_data += chunk
        peer_socket.close()
        
        # Giải mã dữ liệu JSON nhận được thành dictionary
        metainfo = json.loads(metainfo_data.decode('utf-8'))
        return metainfo  # Trả về dữ liệu metainfo đã giải mã
    except socket.error as e:
        print(f"Error requesting metainfo from peer {peer_ip}:{peer_port} - {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode metainfo data.")
        return None

