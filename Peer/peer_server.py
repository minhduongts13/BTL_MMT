<<<<<<< HEAD
import socket
import threading

# Lưu trữ các phần tệp đã tải xuống dưới dạng {piece_index: data}
downloaded_pieces = {}

def peer_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 6881))
    server_socket.listen(5)
    print("Peer server is listening on port 6881")

    while True:
        peer_socket, peer_addr = server_socket.accept()
        print(f"Connected with peer: {peer_addr}")
        
        # Tạo thread để xử lý từng yêu cầu từ peer
        thread = threading.Thread(target=handle_peer, args=(peer_socket,))
        thread.start()

def handle_peer(peer_socket):
    try:
        # Nhận yêu cầu từ peer khác
        request = peer_socket.recv(1024).decode('utf-8')
        print(f"Received request: {request}")
        
        # Xử lý yêu cầu, giả sử yêu cầu dạng "Request piece:<piece_index>"
        if request.startswith("Request piece:"):
            piece_index = int(request.split(":")[1])
            
            # Kiểm tra nếu phần tệp đã có, gửi lại cho peer
            if has_piece(piece_index):
                piece_data = downloaded_pieces[piece_index]
                peer_socket.send(piece_data)
                print(f"Sent piece {piece_index} to peer.")
            else:
                # Nếu không có phần tệp, gửi thông báo lỗi
                peer_socket.send("Piece not available".encode('utf-8'))
                print(f"Piece {piece_index} not available.")
    except Exception as e:
        print(f"Error handling peer request: {e}")
    finally:
        peer_socket.close()

def add_downloaded_piece(piece_index, data):
    # Thêm phần tệp đã tải xuống vào danh sách
    downloaded_pieces[piece_index] = data

def has_piece(piece_index):
    # Kiểm tra xem phần tệp đã tải xuống chưa
    return piece_index in downloaded_pieces

if __name__ == "__main__":
    # Ví dụ thêm phần tệp để thử nghiệm
    add_downloaded_piece(0, b"This is the data for piece 0")
    add_downloaded_piece(1, b"This is the data for piece 1")

    peer_server()
=======
import socket
import threading

# Lưu trữ các phần tệp đã tải xuống dưới dạng {piece_index: data}
downloaded_pieces = {}

def peer_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 6881))
    server_socket.listen(5)
    print("Peer server is listening on port 6881")

    while True:
        peer_socket, peer_addr = server_socket.accept()
        print(f"Connected with peer: {peer_addr}")
        
        # Tạo thread để xử lý từng yêu cầu từ peer
        thread = threading.Thread(target=handle_peer, args=(peer_socket,))
        thread.start()

def handle_peer(peer_socket):
    try:
        # Nhận yêu cầu từ peer khác
        request = peer_socket.recv(1024).decode('utf-8')
        print(f"Received request: {request}")
        
        # Xử lý yêu cầu, giả sử yêu cầu dạng "Request piece:<piece_index>"
        if request.startswith("Request piece:"):
            piece_index = int(request.split(":")[1])
            
            # Kiểm tra nếu phần tệp đã có, gửi lại cho peer
            if has_piece(piece_index):
                piece_data = downloaded_pieces[piece_index]
                peer_socket.send(piece_data)
                print(f"Sent piece {piece_index} to peer.")
            else:
                # Nếu không có phần tệp, gửi thông báo lỗi
                peer_socket.send("Piece not available".encode('utf-8'))
                print(f"Piece {piece_index} not available.")
    except Exception as e:
        print(f"Error handling peer request: {e}")
    finally:
        peer_socket.close()

def add_downloaded_piece(piece_index, data):
    # Thêm phần tệp đã tải xuống vào danh sách
    downloaded_pieces[piece_index] = data

def has_piece(piece_index):
    # Kiểm tra xem phần tệp đã tải xuống chưa
    return piece_index in downloaded_pieces



if __name__ == "__main__":
    # Ví dụ thêm phần tệp để thử nghiệm
    add_downloaded_piece(0, b"This is the data for piece 0")
    add_downloaded_piece(1, b"This is the data for piece 1")

    peer_server()
>>>>>>> c3d6106 (Initial commit)
