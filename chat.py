import websocket
import threading

# Represents connection to Twitch's chat server. Can join multiple channels at once.
# Obtain a Connection by calling connect() or connect_as_guest().
class Connection:
    username = None
    msg_callback = None
    notice_callback = None
    roomstate_callback = None
    timeout_callback = None
    _ws = None
    _pong = None
    closed = False
    
    def __init__(self, name, ws, msg_cb, notice_cb, rs_cb, timeout_cb):
        self.username = name
        self._ws = ws
        self.msg_callback = msg_cb
        self.notice_callback = notice_cb
        self.roomstate_callback = rs_cb
        self.timeout_callback = timeout_cb
    
    # Called whenever a message is received from the websocket. Don't call this.
    def _receive(self, message):
        self._ev.set()
        #print(message)
        message = message.split()
        
        if message[0] == "PING":
            self._ws.send("PONG")
        if message[0] == "PONG":
            if self._pong:
                self._pong.set()
        elif len(message) >= 5 and message[2] == "PRIVMSG":
            if self.msg_callback:
                threading.Thread(target=self.msg_callback, args=(Message(message[0], message[3][1:], message[1].split('!')[0][1:], ' '.join(message[4:])[1:]),)).start()
        elif len(message) >= 5 and message[2] == "NOTICE":
            if self.notice_callback:
                threading.Thread(target=self.notice_callback, args=(Notice(message[0], message[3][1:], ' '.join(message[4:])[1:]),)).start()
        elif len(message) >= 4 and message[2] == "ROOMSTATE":
            if self.roomstate_callback:
                threading.Thread(target=self.roomstate_callback, args=(RoomState(message[0], message[3][1:]),)).start()
        elif len(message) >= 5 and message[2] == "CLEARCHAT":
            if self.timeout_callback:
                threading.Thread(target=self.timeout_callback, args=(Timeout(message[0], message[3][1:], message[4][1:]),)).start()
    
    # Join chat in a given channel, eg join_channel("adamcake")
    def join_channel(self, channel):
        self._ws.send("JOIN #{}".format(channel.lower()))
        return Channel(channel, self._ws)
    
    # Close this connection - any attempt to use this connection after calling disconnect() will raise an exception.
    def disconnect(self):
        self._ws.close()

    # Sends a PING and blocks until a PONG is received. You may optionally specify a timeout in seconds.
    # Always returns True unless a timeout occurs, in which case it will return False.
    # Note that calling ping() more than once at a time on the same connection will cause the first ping to be dropped and thus timeout.
    # As such, this method should only be used synchronously, or, if you absolutely must thread it, do not call ping() again until the previous call has returned.
    def ping(self, timeout=None):
        self._pong = threading.Event()
        self._ws.send("PING")
        return self._pong.wait(timeout)

    # Check if the connection has been closed (it may have been closed by the far end without warning)
    def is_closed(self):
        return self.closed

# Represents a joined Twitch channel. Obtained by calling Connection.join_channel.
# This object is tied to the Connection object you used to join the channel.
class Channel:
    channel_name = ""
    _ws = None
    
    def __init__(self, channel, ws):
        self.channel_name = channel
        self._ws = ws
    
    # Sends a message in the channel.
    def send(self, msg):
        self._ws.send("PRIVMSG #{} :{}".format(self.channel_name, msg))
    
    # Leaves the channel - attempting to use this object after calling leave() will raise an exception.
    def leave(self):
        self._ws.send("PART #{}".format(self.channel_name))
        self._ws = None

# A message received in Twitch chat
class Message:
    def __init__(self, header, channel, login, msg):
        info = _parse_header(header)
        self.channel = channel
        self.message = msg
        self.badge_info = info.get("badge-info", [])
        self.badges = info.get("badges", [])
        self.color = info.get("color", None)
        self.display_name = info.get("display-name", None)
        self.login = login
        self.user_id = info.get("user-id", None)
        self.user_type = info.get("user-type", None)
        self.msg_id = info.get("msg-id", None)
        self.moderator = int(info.get("mod", 0)) != 0
        self.subscriber = int(info.get("subscriber", 0)) != 0
        self.turbo = int(info.get("turbo", 0)) != 0 # guess this is for Prime?
        self.timestamp = info.get("tmi-sent-ts", None)

# Represents a Notice posted in the Twitch chat, such as "the room is now in slow mode".
# These messages are meant to be human-readable. If you need machine-readable updates on room state, use the RoomState callback instead.
class Notice:
    def __init__(self, header, channel, msg):
        info = _parse_header(header)
        self.message = msg
        self.channel = channel
        self.msg_id = info.get("msg-id", None)

# Represents the state of a channel, for instance whether it's in sub-only mode, emote-only mode and so on.
# This will only be constructed when Twitch sends us an update on the room state, which means only when it changes.
class RoomState:
    def __init__(self, header, channel):
        info = _parse_header(header)
        self.channel = channel
        self.msg_id = info.get("msg-id", None)
        self.emote_only = int(info.get("emote-only", 0)) != 0
        self.followers_only = int(info.get("followers-only", -1)) # -1 means disabled, positive means minimum follow age
        self.r9k = int(info.get("r9k", 0)) != 0
        self.slow = int(info.get("slow", 0)) # time in seconds of message cooldown
        self.subscribers_only = int(info.get("subs-only", 0)) != 0

# Represents an instruction to timeout or ban a user, usually resulting in their messages being deleted from chat.
# Timeout.duration is in seconds. It may be None, indicating a permanent ban.
class Timeout:
    def __init__(self, header, channel, username):
        info = _parse_header(header)
        self.channel = channel
        self.username = username
        self.user_id = info.get("target-user-id", None)
        self.duration = info.get("ban-duration", None)
        self.timestamp = info.get("tmi-sent-ts", None)

# Establish a chat connection with your Twitch account. Requires your username and a valid OAuth token.
# Optionally, pass a callback function which will be called when a new chat message is received. Function must take a Message parameter.
def connect(username, oauth, on_message=None, on_notice=None, on_room_state=None, on_timeout=None):
    return _connect(username.lower(), "oauth:{}".format(oauth), on_message, on_notice, on_room_state, on_timeout)

# Establish a chat connection as though you were signed out. This type of connection can read messages but cannot send them.
# Trying to send a message with this type of connection will fail silently.
# Optionally, pass a callback function which will be called when a new chat message is received. Function must take a Message parameter.
def connect_as_guest(on_message=None, on_notice=None, on_room_state=None, on_timeout=None):
    return _connect("justinfan12345", "SCHMOOPIIE", on_message, on_notice, on_room_state, on_timeout) # Yes these are actually Twitch's defaults

# Establishes a connection to irc-ws.chat.twitch.tv and returns a Connection object.
# Shouldn't be called directly - call connect() or connect_as_guest() instead.
def _connect(username, passkey, on_message, on_notice, on_room_state, on_timeout):
    ws = websocket.WebSocketApp("wss://irc-ws.chat.twitch.tv/", on_message=_receive)
    conn = Connection(username, ws, on_message, on_notice, on_room_state, on_timeout)
    ws.conn = conn
    def _intro(ws):
        ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands")
        ws.send("PASS {}".format(passkey))
        ws.send("NICK {}".format(username))
        ws.send("USER {u} 8 * :{u}".format(u=username))
    ws.on_open = _intro
    
    def _run_forever(ws, conn):
        ws.run_forever()
        conn.closed = True
    conn._ev = threading.Event()
    conn._t = threading.Thread(target=_run_forever, args=(ws, conn))
    conn._t.start()
    conn._ev.wait()
    
    return conn

# Callback for Websocket messages. Passes it straight to the associated Connection object.
def _receive(ws, message):
    ws.conn._receive(message)

# parse the message header that's present on some types of message from Twitch into a key-value dict
# eg: @key=value;key2=value2;type=;timestamp=12345678
def _parse_header(str):
    ret = {}
    if not str.startswith('@'):
        return ret
    for pair in [v.split('=', 1) for v in str[1:].split(';') if "=" in v]:
        ret[pair[0]] = pair[1]
    return ret
