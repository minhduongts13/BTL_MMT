import hashlib
import json
import os

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
