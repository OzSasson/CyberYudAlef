import os
import socket, threading

exit_all = False
PROTOCOL = 'HTTP1.1'
moved_302 = {'A/dog.jpg': 'B/dog.jpg', 'B/dog.jpg': 'B/dog2.jpg'}


def http_send(s, reply_header, reply_body):
    reply = reply_header.encode()
    if reply_body != b'':
        try:
            body_length = len(reply_body)
            reply_header += 'Content-Length: ' + str(body_length) + '\r\n' + '\r\n'
            reply = reply_header.encode() + reply_body
        except Exception as e:
            print(e)
    else:
        reply += b'\r\n'
    s.send(reply)
    print('SENT:', reply[:min(100, len(reply))])


def http_recv(sock):
    header = ''
    while '\r\n\r\n' not in header:
        header += sock.recv(1).decode()
    print('RECV:', header[:min(100, len(header))])
    if 'Content-Length' not in header:
        return header, b''
    i = header.index('Content-Length:') + 16
    content_length = ''
    cur = ''
    while True:
        cur = header[i]
        if cur == '\r':
            break
        content_length += cur
        i += 1
    content_length = int(content_length)
    body = b''
    data_len = content_length
    while len(body) < data_len:
        _d = sock.recv(data_len - len(body))
        if len(_d) == 0:
            body = b""
            break
        body += _d
    body = body
    return header, body


def get_type_header(requested_file):
    request = requested_file.split('\r\n')[0]
    request_parts = request.split(' ')
    if len(request_parts) == 3 and request_parts[0] == 'GET':
        file_name = request_parts[1]
        if file_name == '/':
            file_name = r'/index.html'
        return 'GET', file_name
    elif len(request_parts) == 3 and request_parts[0] == 'POST':
        file_name = request_parts[1]
        return 'POST', file_name
    else:
        return '', ''


def get_data(type_request, requested_file, body):
    data = b''
    if type_request == 'GET':
        if '/calculate-next' in requested_file:
            val = requested_file.split('?')[1].split('=')[1]
            try:
                val = str(int(val) + 1)
                return val.encode()
            except:
                return b'NaN'
        elif '/calculate-area' in requested_file:
            val = requested_file.split('?')[1].split('&')
            try:
                height = int(val[0].split('=')[1])
                width = int(val[1].split('=')[1])
                val = str(height * width / 2)
                return val.encode()
            except:
                return b'NaN'
        elif '/image' in requested_file:
            file_name = requested_file.split('?')[1].split('=')[1]
            with open(f'E:\python\webroot/upload/{file_name}', 'rb') as f:
                data = f.read()
            return data
        else:
            with open('E:\python\webroot' + requested_file, 'rb') as f:
                data = f.read()
            return data
    else:
        ls = requested_file.split('?')
        file_name = ls[1].split('=')[1]
        with open(f'E:\python\webroot\{ls[0][1:]}\{file_name}', 'wb') as f:
            f.write(body)
        return b'Saved'


def Add_Content_Type(filename):
    if '.' in filename:
        filename = filename.split('.')
        filename = filename[len(filename) - 1]
        if filename == 'text' or filename == 'html':
            return 'Content-Type: text/html\r\n'
        elif filename == 'jpg':
            return 'Content-Type: image/jpeg\r\n'
        elif filename == 'js':
            return 'Content-Type: text/javascript\r\n'
        elif filename == 'css':
            return 'Content-Type: text/css\r\n'
    else:
        return ''


def handle_request(request_header, body):
    try:
        t, f = get_type_header(request_header)
        if f == '':
            return '', ''
        if f in moved_302.keys():
            return f'HTTP/1.1 302 Found\r\nLocation: {moved_302[f]}\r\n', get_data(t, f, body)
        if t == 'GET':
            return f'HTTP/1.1 200 OK\r\n{Add_Content_Type(f)}', get_data(t, f, body)
        else:
            return f'HTTP/1.1 200 OK\r\n', get_data(t, f, body)
    except FileNotFoundError as e:
        print(e)
        return 'HTTP/1.1 404 Not Found\r\n', b'404 Not Found'
    except PermissionError as e:
        print(e)
        return 'HTTP/1.1 403 Forbidden\r\n', b'403 Forbidden'
    except Exception as e:
        print(e)
        return 'HTTP/1.1 500 Internal Server Error\r\n', b'500 Internal Server Error'


def handle_client(s_clint_sock, tid, addr):
    global exit_all
    print('new client arrive', tid, addr)
    while not exit_all:
        request_header, body = http_recv(s_clint_sock)
        if request_header == b'':
            print('seems client disconected, client socket will be close')
            break
        else:
            reply_header, body = handle_request(request_header, body)
            if reply_header == '':
                print('Not GET/POST request')
                break
            if PROTOCOL == "HTTP1.0":
                reply_header += "Connection': close\r\n"
            else:
                reply_header += "Connection: keep-alive\r\n"
            http_send(s_clint_sock, reply_header, body)
            if PROTOCOL == "HTTP1.0":
                break
    print("Client", tid, "Closing")
    s_clint_sock.close()


def main():
    global exit_all
    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', 80))
    server_socket.listen(5)
    threads = []
    tid = 1
    while True:
        try:
            # print('\nbefore accept')
            client_socket, addr = server_socket.accept()
            t = threading.Thread(target=handle_client, args=(client_socket, tid, addr))
            t.start()
            threads.append(t)
            tid += 1

        except socket.error as err:
            print('socket error', err)
            break
    exit_all = True
    for t in threads:
        t.join()

    server_socket.close()
    print('server will die now')


if __name__ == "__main__":
    main()
