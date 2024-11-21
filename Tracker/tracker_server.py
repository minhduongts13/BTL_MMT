from flask import Flask, request, jsonify
import ipaddress
import json

app = Flask(__name__)

# Lưu trữ danh sách peers theo từng torrent (info_hash)
torrent_peers = {}

# Mã ID của tracker server
tracker_id = "tracker_001"

# Giới hạn số lượng peers trả về
MAX_PEERS = 50


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
    local_ip = request.args.get('local-ip', 0)

    # Kiểm tra nếu thiếu tham số bắt buộc
    if not info_hash or not peer_id or not port:
        return jsonify({"Failure reason": "Missing required parameters"}), 400

    # Chuyển port, uploaded, downloaded, và left thành số nguyên
    try:
        port = int(port)
        uploaded = int(uploaded)
        downloaded = int(downloaded)
        left = int(left)

        client_ip = request.args.get('public_ip') or get_client_ip()
        ipaddress.ip_address(client_ip)  # Kiểm tra IP hợp lệ
        if port < 1 or port > 65535:
            raise ValueError("Invalid port number")
    except ValueError as e:
        return jsonify({"Failure reason": str(e)}), 400

    # Kiểm tra hoặc tạo mới danh sách peers cho info_hash
    if info_hash not in torrent_peers:
        torrent_peers[info_hash] = {}

    # Kiểm tra và xử lý sự kiện
    valid_events = {"started", "completed", "stopped"}
    response_data = {}
    if event not in valid_events:
        return jsonify({"Failure reason": "Invalid event type"}), 400

    if event == "started":
        # Thêm peer mới vào danh sách
        if peer_id not in torrent_peers[info_hash]:
            torrent_peers[info_hash][peer_id] = {
                "ip": client_ip,
                "local-ip": local_ip,
                "port": port,
                "uploaded": uploaded,
                "downloaded": downloaded,
                "left": left,
                "completed": False
            }
        print(f"Peer {peer_id} with IP {client_ip} has started downloading torrent {info_hash}.")

        # Chuẩn bị danh sách các peers trả về
        peer_list = [
            {"peer_id": pid, "ip": peer["ip"], "port": peer["port"], "local-ip": peer["local-ip"]}
            for pid, peer in torrent_peers[info_hash].items()
            if pid != peer_id  # Loại bỏ chính peer gửi request
        ]
        response_data = {
            "tracker_id": tracker_id,
            "peers": peer_list[:MAX_PEERS]  # Giới hạn số lượng peers trả về
        }


    elif event == "completed":
        if peer_id in torrent_peers[info_hash]:
            torrent_peers[info_hash][peer_id]["completed"] = True
        print(f"Peer {peer_id} with IP {client_ip} has completed downloading torrent {info_hash}.")
        response_data = {"tracker_id": tracker_id, "status": "completed"}

    elif event == "stopped":
        if peer_id in torrent_peers[info_hash]:
            del torrent_peers[info_hash][peer_id]
        print(f"Peer {peer_id} with IP {client_ip} has stopped and was removed from the list for torrent {info_hash}.")
        response_data = {"tracker_id": tracker_id, "status": "stopped"}

    return app.response_class(
        response=json.dumps(response_data),
        status=200,
        mimetype='application/json'
    )


def get_client_ip():
    # Lấy IP của client từ các headers hoặc địa chỉ yêu cầu
    if 'X-Forwarded-For' in request.headers:
        ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    elif 'X-Real-IP' in request.headers:
        ip = request.headers['X-Real-IP']
    else:
        ip = request.remote_addr
    return ip


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
