import hashlib
import json
import os
import requests
import socket
import hashlib
from file_manager import assemble_file  

class DownloadManager:
    def __init__(self, total_pieces, piece_length, files, isUpload=False):
        self.isUpload = isUpload
        self.piece_length = piece_length
        self.total_pieces = total_pieces
        self.files = files
        self.file_paths = self.create_file_paths()
        if self.isUpload:
            self.piece_status = self.generate_piece()
        else:
            self.piece_status = {i: {'data': None, 'downloaded': False} for i in range(total_pieces)}

    def create_file_paths(self):
        file_paths = []
        for file in self.files:
            file_paths.append(file['path'][0])
        return file_paths

    def generate_piece(self):
        dic = {}
        i = 0
        for file_path in self.file_paths:
            with open(file_path, "rb") as f:
                while True:
                    piece_data = f.read(self.piece_length)
                    if not piece_data:
                        break
                    dic[i] = {'data': piece_data, 'downloaded': True}
                    i += 1
        return dic

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
        if piece_index < 0 or piece_index >= self.total_pieces:
            print(f"Piece {piece_index} is out of range.")
            return False
        return self.piece_status[piece_index]['downloaded']

    def assemble(self):
        """Ghép các pieces thành tệp hoàn chỉnh, hỗ trợ nhiều tệp."""
        if not self.is_file_complete():
            print("File download is not yet complete.")
            return None

        os.makedirs("torrent", exist_ok=True)  # Tạo thư mục chứa các tệp ghép
        try:
            for file in self.files:
                file_length = file["length"]  # Kích thước của tệp hiện tại
                file_path = file["path"][0]
                file_name = os.path.join("torrent", os.path.basename(file_path))
                print(f"Assembling file: {file_name}, size: {file_length} bytes")

                file_offset = 0  # Offset nội bộ cho tệp hiện tại
                with open(file_name, "wb") as f:
                    while file_length > 0:
                        # Xác định piece_index và piece_offset dựa trên file_offset
                        piece_index = file_offset // self.piece_length
                        piece_offset = file_offset % self.piece_length

                        # Lấy dữ liệu của piece hiện tại
                        piece_data = self.piece_status[piece_index]['data']
                        if piece_data is None:
                            raise ValueError(f"Piece {piece_index} is missing or incomplete.")

                        # Tính toán kích thước khả dụng trong piece và tệp
                        available_piece_data = len(piece_data) - piece_offset
                        if available_piece_data <= 0:
                            raise ValueError(f"Invalid available data in piece {piece_index}.")

                        # Tính toán kích thước ghi dữ liệu vào tệp
                        write_size = min(file_length, available_piece_data)
                        if write_size <= 0:
                            break  # Không còn dữ liệu để ghi

                        # Ghi dữ liệu vào tệp
                        f.write(piece_data[piece_offset:piece_offset + write_size])
                        file_offset += write_size
                        file_length -= write_size

                        print(f"Written {write_size} bytes for piece {piece_index}. Remaining: {file_length} bytes")

                print(f"File assembled successfully: {file_name}")
        except Exception as e:
            print(f"Error during file assembly: {e}")

    def assemble2(self):
        """Ghép các pieces thành tệp hoàn chỉnh, hỗ trợ nhiều tệp."""
        if not self.is_file_complete():
            print("File download is not yet complete.")
            return None

        os.makedirs("torrent", exist_ok=True)  # Tạo thư mục chứa các tệp ghép
        try:
            piece_index = 0
            for file in self.files:
                file_length = file["length"]  # Kích thước của tệp hiện tại
                file_path = file["path"][0]
                file_name = os.path.join("torrent", os.path.basename(file_path))
                print(f"Assembling file: {file_name}, size: {file_length} bytes")

                file_offset = 0  # Offset nội bộ cho tệp hiện tại
                with open(file_name, "wb") as f:
                    while file_length > 0:
                        # Lấy dữ liệu của piece hiện tại
                        piece_data = self.piece_status[piece_index]['data']
                        if piece_data is None:
                            raise ValueError(f"Piece {piece_index} is missing or incomplete.")
                        # Ghi dữ liệu vào tệp
                        f.write(piece_data)
                        file_length -= len(piece_data)
                        piece_index += 1
                print(f"File assembled successfully: {file_name}")
        except Exception as e:
            print(f"Error during file assembly: {e}")

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
        self.metainfo_data = {}

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
        self.metainfo_data = metainfo_data
        # Tạo mã hash duy nhất (info_hash) đại diện cho tệp
        info_serialized = json.dumps(metainfo_data["info"], sort_keys=True).encode("utf-8")
        self.info_hash = hashlib.sha1(info_serialized).hexdigest()
        
        # Lưu vào file .torrent
        torrent_file_path = f"{self.file_paths[0]}.torrent"
        with open(torrent_file_path, "w") as f:
            json.dump(metainfo_data, f)
        
        print(f"Metainfo file created at: {torrent_file_path}")
        return torrent_file_path
    

def create_metainfo():
    file_paths = []
    file_path = str(input("Enter files paths, type '//' to stop.\n"))
    while (file_path != "//"):
        file_paths.append(file_path)
        file_path = str(input())

    piece_length = int(input("Enter piece length: "))
    metaInfo = Metainfo(file_paths, piece_length, "https://btl-mmt-pma6.onrender.com/announce")
    # metaInfo = Metainfo([r"D:/BTL/BTLMMT/BTL/BTL1/BTL_MMT/Peer/sample.txt", r"D:/BTL/BTLMMT/BTL/BTL1/BTL_MMT/Peer/sample2.txt"], 512, "https://btl-mmt-pma6.onrender.com/announce")
    metaInfo.generate_metainfo()
    return [metaInfo.info_hash, metaInfo.metainfo_data]

_cached_public_ip = None  # Biến toàn cục để lưu trữ IP công khai

def get_public_ip():
    global _cached_public_ip
    if _cached_public_ip is not None:
        return _cached_public_ip

    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        _cached_public_ip = response.json()["ip"]
        return _cached_public_ip
    except requests.RequestException as e:
        print(f"Error getting public IP: {e}")
        return "127.0.0.1"  # Dùng localhost nếu không thể lấy IP công khai


    
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
    try:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_ip, peer_port))

        # Gửi yêu cầu metainfo
        peer_socket.send("request_metainfo".encode('utf-8'))

        # Nhận dữ liệu metainfo
        metainfo_data = b""
        while True:
            chunk = peer_socket.recv(1024)
            print(f"Received chunk: {chunk}")
            if chunk == b"END":  # Dừng khi nhận thông báo kết thúc
                break
            if not chunk:
                raise ValueError("Connection closed unexpectedly.")
            metainfo_data += chunk

        print("Received metainfo successfully.")
        return json.loads(metainfo_data.decode('utf-8'))
    except Exception as e:
        print(f"Error requesting metainfo from peer {peer_ip}:{peer_port} - {e}")
        return None
    finally:
        peer_socket.close()




