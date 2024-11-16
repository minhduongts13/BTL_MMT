from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Lưu trữ danh sách peers theo từng torrent (info_hash)
#torrent_peers = {info_hash : {metainfo : , peerlist : {}} }
torrent_peers = {}

# Mã ID của tracker server
tracker_id = "tracker_001"

# Giới hạn số lượng peers trả về
MAX_PEERS = 50

@app.route('/announce', methods=['GET'])
@app.route('/announce', methods=['GET'])
def announce():
    # Lấy các tham số từ yêu cầu của client
    info_hash = request.args.get('info_hash')
    peer_id = request.args.get('peer_id')
    port = request.args.get('port')
    event = request.args.get('event')
    uploaded = request.args.get('uploaded', 0)
    downloaded = request.args.get('downloaded', 0)
    left = request.args.get('left', 0)

    # Kiểm tra nếu thiếu tham số bắt buộc
    if not info_hash or not peer_id or not port:
        return jsonify({"Failure reason": "Missing required parameters"}), 400

    # Chuyển port, uploaded, downloaded, và left thành số nguyên
    try:
        port = int(port)
        uploaded = int(uploaded)
        downloaded = int(downloaded)
        left = int(left)
    except ValueError:
        return jsonify({"Failure reason": "Invalid parameter values"}), 400

    # Lấy IP của client từ yêu cầu nếu có, hoặc từ hàm get_client_ip()
    client_ip = request.args.get('public_ip') or get_client_ip()

    # Kiểm tra hoặc tạo mới danh sách peers cho info_hash
    if info_hash not in torrent_peers:
        torrent_peers[info_hash] = {}
    response_data = {}
    # Xử lý sự kiện từ client
    if event == "started":
        if not (peer_id in torrent_peers[info_hash]):
            # Chuẩn bị phản hồi danh sách các peers còn lại, giới hạn theo MAX_PEERS
            peer_list = [
                {"peer_id": pid, "ip": peer["ip"], "port": peer["port"]}
                for pid, peer in torrent_peers[info_hash].items()
            ]
            peer_list = peer_list[:MAX_PEERS]

            response_data = {
                "tracker_id": tracker_id,
                "peers": peer_list
            }

            torrent_peers[info_hash][peer_id] = {
                "ip": client_ip,
                "port": port,
                "uploaded": uploaded,
                "downloaded": downloaded,
                "left": left,
                "completed": False
            }
        print(f"Peer {peer_id} with IP {client_ip} has started downloading torrent {info_hash}.")
    elif event == "completed":
        if peer_id in torrent_peers[info_hash]:
            torrent_peers[info_hash][peer_id]["completed"] = True
        print(f"Peer {peer_id} with IP {client_ip} has completed downloading torrent {info_hash}.")
    elif event == "stopped":
        if peer_id in torrent_peers[info_hash]:
            del torrent_peers[info_hash][peer_id]
        print(f"Peer {peer_id} with IP {client_ip} has stopped and was removed from the list for torrent {info_hash}.")

    

    return app.response_class(
        response=json.dumps(response_data),
        status=200,
        mimetype='text/plain'
    )


def get_client_ip():
    # Kiểm tra X-Forwarded-For header nếu có, lấy IP đầu tiên trong danh sách (IP gốc của client)
    if 'X-Forwarded-For' in request.headers:
        ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    # Kiểm tra X-Real-IP header nếu có
    elif 'X-Real-IP' in request.headers:
        ip = request.headers['X-Real-IP']
    # Nếu không có header nào, dùng request.remote_addr
    else:
        ip = request.remote_addr
    return ip


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
