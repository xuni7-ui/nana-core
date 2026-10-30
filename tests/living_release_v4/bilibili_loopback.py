"""Synthetic API-shape counterpart using actual bounded loopback HTTP."""
import json
import socket
import threading
import urllib.parse
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class LoopbackOpener:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.urls = []
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        parsed = urllib.parse.urlsplit(request.full_url)
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        return self.opener.open(urllib.request.Request(self.endpoint + path, data=request.data,
            headers=dict(request.header_items()), method=request.get_method()), timeout=timeout)


@contextmanager
def counterpart():
    state = {"requests": [], "posts": 0, "comments": [], "lose_response": False, "read_unavailable": False,
             "account_id": 42, "logged_in": True}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            state["requests"].append(("GET", self.path))
            if state["read_unavailable"]:
                self.send_error(503)
                return
            if "/web-interface/nav" in self.path:
                value = {"isLogin": state["logged_in"], "mid": state["account_id"]}
            elif '/fetch_session_msgs' in self.path:
                value = {'messages':state.get('messages',[])}
            elif '/get_sessions' in self.path:
                value = {'session_list':[{'session_type':1,'talker_id':43,'unread_count':1,'max_seqno':1}]}
            elif "/search/type" in self.path:
                value = {"result": state.get('search_results', [{"bvid": "BV1t55v6DE2v", "aid": 7, "cid": 8, "title": "Loopback source"}])}
            elif "/web-interface/view" in self.path:
                target = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)['bvid'][0]
                value = {"bvid": target, "aid": 7, "cid": 8, "title": "Loopback source"}
            elif "/player/v2" in self.path:
                value = {"subtitle": {"subtitles": [{"subtitle_url": "https://aisubtitle.hdslb.com/fixture.json"}]}}
            elif '/player/videoshot' in self.path:
                value = {'index': [0, 5, 10], 'image':['https://i0.hdslb.com/owned-storyboard.png'],
                    'img_x_size':32, 'img_y_size':24, 'img_x_len':3, 'img_y_len':1}
            elif self.path == '/owned-storyboard.png':
                import io
                from PIL import Image
                image = Image.new('RGB', (96,24), 'blue')
                for x in range(32,64):
                    for y in range(24): image.putpixel((x,y), (255,0,0))
                output = io.BytesIO()
                image.save(output, format='PNG')
                self.send_response(200)
                self.end_headers()
                self.wfile.write(output.getvalue())
                return
            elif self.path == "/fixture.json":
                self.reply({"body": [{"from": 1, "to": 2, "content": "Synthetic timestamped subtitle"}]})
                return
            elif "/dm/list.so" in self.path:
                raw = b'<i><d p="1.5,1,25">Synthetic viewer</d></i>'
                self.send_response(200)
                self.end_headers()
                self.wfile.write(raw)
                return
            elif "/x/v2/reply" in self.path:
                value = {"replies": state["comments"]}
            else:
                self.send_error(404)
                return
            self.reply({"code": 0, "data": value})

        def do_POST(self):
            state["requests"].append(("POST", self.path))
            if '/web_im/send_msg' in self.path:
                values=urllib.parse.parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
                state['posts']+=1
                text=json.loads(values['msg[content]'][0])['content']
                row={'msg_key':'out-'+str(state['posts']),'msg_seqno':2,'sender_uid':42,'receiver_id':43,
                     'content':json.dumps({'content':text}),'timestamp':1}
                state.setdefault('messages',[]).append(row)
                if state['lose_response']:
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();state['read_unavailable']=True
                    return
                self.reply({'code':0,'data':{'msg_key':row['msg_key']}})
                return
            assert self.path == "/x/v2/reply/add"
            assert self.headers["Cookie"] == "TEST_ONLY_NOT_SECRET_COOKIE"
            values = urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
            assert values["csrf"] == ["TESTONLYNOTSECRET0123456789"]
            state["posts"] += 1
            row = {"rpid": state["posts"], "root": int(values.get('root',['0'])[0]),
                'parent':int(values.get('parent',['0'])[0]),"member": {"mid": 42}, "content": {"message": values["message"][0]}}
            state["comments"].append(row)
            if state["lose_response"]:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                state["read_unavailable"] = True
                return
            self.reply({"code": 0, "data": {"rpid": row["rpid"]}})

        def reply(self, value):
            raw = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield LoopbackOpener("http://127.0.0.1:" + str(server.server_port)), state
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
