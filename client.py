import socket
import time
import threading

def build_connection(sock, server_address, server_port):
    sock.connect((server_address,server_port))


def make_header_protocol(roomname, operation_code, curr_states, username):
    # ヘッダー：10バイト
    roomname_bits = roomname.encode('utf-8')
    roomname_bits_len = len(roomname_bits)
    to_bytes_roomnamelen = roomname_bits_len.to_bytes(4, "big")

    to_bytes_operation_code = operation_code.to_bytes(1, "big")

    to_bytes_curr_states = curr_states.to_bytes(1, "big")

    username_bits = username.encode('utf-8')
    username_bits_len= len(username_bits)
    to_bytes_usernamelen = username_bits_len.to_bytes(4, "big")

    return to_bytes_roomnamelen + to_bytes_operation_code + to_bytes_curr_states + to_bytes_usernamelen


def make_body(roomname, username):
    roomname_bits = roomname.encode('utf-8')
    username_bits = username.encode('utf-8')

    return roomname_bits + username_bits



# def receive_and_parse_payload(sock):
#     header = sock.recv(16)
#     bytes_roomname = int.from_bytes(header[:4], "big")
#     operation = int.from_bytes(header[4:5], "big")
#     curr_states = int.from_bytes(header[5:6], "big")
#     bytes_username = int.from_bytes(header[6:10], "big")
#     bytes_message = int.from_bytes(header[10:], "big")

#     body = sock.recv(2032)
#     roomname = body[:bytes_roomname].decode('utf-8')
#     username = body[bytes_roomname:bytes_roomname+bytes_username].decode('utf-8')
#     message = body[bytes_roomname+bytes_username:].decode('utf-8')

#     print(f"ルーム名：{roomname}")
#     print(f"ユーザー名：{username}")
#     print(f"操作コード：{operation}")
#     print(f"現在の状態：{curr_states}")
#     print(f"サーバーからのメッセージ：{message}")



def main():
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = '0.0.0.0'
    server_port = 9000

    build_connection(sock, server_address, server_port)

    #  チャットルーム作成のリクエスト送信
    roomname = "テストルーム名"
    operation_code = 1
    curr_states = 0
    username = "テストユーザー名１"

    header = make_header_protocol(roomname, operation_code, curr_states, username)
    sock.sendall(header)

    body = make_body(roomname, username)
    sock.sendall(body)


    # サーバーから解析完了のメッセージ受信 & 解析
    header = sock.recv(10)
    bytes_roomname = int.from_bytes(header[:2], "big")
    operation = int.from_bytes(header[2:3], "big")
    curr_states = int.from_bytes(header[3:4], "big")
    bytes_username = int.from_bytes(header[4:6], "big")
    bytes_message = int.from_bytes(header[6:], "big")

    body_len = bytes_roomname + bytes_username + bytes_message
    body = sock.recv(body_len)
    roomname = body[:bytes_roomname].decode('utf-8')
    username = body[bytes_roomname:bytes_roomname+bytes_username].decode('utf-8')
    message = body[bytes_roomname+bytes_username:].decode('utf-8')


    print(f"ルーム名：{roomname}")
    print(f"ユーザー名：{username}")
    print(f"操作コード：{operation}")
    print(f"現在の状態：{curr_states}")
    print(f"サーバーからのメッセージ：{message}")
    
    # states == 0 の場合
    if curr_states == 0:
        print(f"再掲：{message}")
    # 再びユーザーにinputさせる処理(後に作成)
    
    # states == 1 の場合
    elif curr_states == 1:
        print(f"準拠成功：{message}")

        # サーバーからのトークンを受け取るための解析処理
        header = sock.recv(12)
        # roomname, operation, states, username, message, token
        roomname_bytes = int.from_bytes(header[:2], "big")
        operation = int.from_bytes(header[2:3], "big")
        states = int.from_bytes(header[3:4], "big")
        username_bytes = int.from_bytes(header[4:6], "big")
        message_bytes = int.from_bytes(header[6:8], "big")
        token_bytes = int.from_bytes(header[8:], "big")

        # roomname, username, message, token
        stream_rate = roomname_bytes + username_bytes + message_bytes + token_bytes
        body = sock.recv(stream_rate)
        roomname = body[:roomname_bytes].decode('utf-8')
        username = body[roomname_bytes:roomname_bytes+username_bytes].decode('utf-8')
        a = roomname_bytes + username_bytes
        message = body[a: a+message_bytes].decode('utf-8')
        b = a + message_bytes
        token = body[b:].decode('utf-8')

        print(f"これは操作コード：{operation}の、状態：{states}の通信です。")
        print(f"ルーム名：{roomname}")
        print(f"ユーザー名：{username}")
        print(f"メッセージ：{message}")
        print(f"トークン：{token}")

        ip_len_bits = sock.recv(1)
        ip_len = int.from_bytes(ip_len_bits, "big")
        ip_bits = sock.recv(ip_len)
        ip = ip_bits.decode('utf-8')

        port_bits = sock.recv(2)
        port = int.from_bytes(port_bits, "big")

        print("ソケットを閉じました。")
        sock.close()
    
    #### UDP通信
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sock.bind((ip, port))

        roomname_bits = roomname.encode('utf-8')
        roomname_size = len(roomname_bits)
        roomname_size_of_bytes = roomname_size.to_bytes(1, "big")

        token_bits = token.encode('utf-8')
        token_size = len(token_bits)
        token_size_of_bytes = token_size.to_bytes(1, "big")

        message = "はじめまして、テストユーザー１です。"
        message_bits = message.encode('utf-8')

        payload = roomname_size_of_bytes + token_size_of_bytes + roomname_bits + token_bits + message_bits
        
        sent = sock.sendto(payload, (server_address, server_port))
        print(f"メッセージを送信しました。：{sent}")


        print("メッセージを待っています。")
        data, server = sock.recvfrom(4096)
        message_from_server = data.decode('utf-8')
        print(f"データを受信しました。：{message_from_server} from {server}")



if __name__ == "__main__":
    main()