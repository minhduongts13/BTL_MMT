import hashlib

def split_file(file_path, piece_size=512*1024):
    pieces = []
    with open(file_path, 'rb') as file:
        while True:
            piece = file.read(piece_size)
            if not piece:
                break
            pieces.append(piece)
    return pieces

def assemble_file(pieces, output_file):
    with open(output_file, 'wb') as file:
        for piece in pieces:
            file.write(piece)
    print(f"File assembled: {output_file}")

def generate_piece_hashes(pieces):
    piece_hashes = []
    for piece in pieces:
        piece_hash = hashlib.sha256(piece).hexdigest()
        piece_hashes.append(piece_hash)
    return piece_hashes

def verify_piece(piece, expected_hash):
    piece_hash = hashlib.sha256(piece).hexdigest()
    return piece_hash == expected_hash