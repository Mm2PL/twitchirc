import atexit
import socket
import time
import typing

import irclib  # Import self.


def readuntil(buffer, char, max_size=1024):
    m = ''
    num = 0
    while 1:
        num += 1
        if num >= max_size:
            break
        c = buffer.read(1)
        if c == char:
            break
        m += c
    return m


def to_bytes(obj, encoding='utf-8'):
    if isinstance(obj, str):
        return bytes(obj, encoding)
    else:
        return bytes(obj)


class Connection:
    def __init__(self, address: str, port: int = 6667, message_cooldown: int = 3, no_atexit=False):
        self.message_cooldown: int = message_cooldown
        self.address: str = address
        self.port: int = port
        self.socket: typing.Union[socket.socket, None] = None
        self.queue: typing.Dict[str, typing.List[bytes]] = {
            'misc': []
        }
        self.receive_queue: typing.List[typing.Union[irclib.Message, irclib.ChannelMessage, irclib.PingMessage]] = []
        self.receive_buffer: str = ''
        self.message_wait: typing.Dict[str, float] = {
            'misc': time.time()
        }
        self.hold_send = False
        self.channels_connected = []
        self.channels_to_remove = []
        if no_atexit:
            @atexit.register
            def close_self():
                try:
                    self.disconnect()
                except:
                    pass

    def join(self, channel):
        irclib.info('Joining channel {}'.format(channel))
        self.force_send('join #{}\r\n'.format(channel))
        self.queue[channel] = []
        self.message_wait[channel] = time.time()
        self.channels_connected.append(channel)

    def part(self, channel):
        irclib.info(f'Departing from channel {channel}')
        self.force_send(f'part #{channel}\r\n')
        self.channels_to_remove.append(channel)

    def disconnect(self):
        self.socket.send(b'quit\r\n')
        self.socket.shutdown(socket.SHUT_WR)
        self.socket.close()
        self.socket = None

    def twitch_mode(self):
        irclib.info('Twitch mode enabled.')
        self.force_send('CAP REQ :twitch.tv/commands twitch.tv/membership twitch.tv/tags\r\n')

    def connect(self, username, password: typing.Union[str, None] = None) -> None:
        """
        Connect to the IRC server.

        :param username: Username that will be used.
        :param password: Password to be sent. If None the PASS packet will not be sent.
        """
        irclib.info('Connecting...')
        self._connect()
        irclib.info('Logging in...')
        self._login(username, password)
        irclib.info('OK.')

    def _login(self, username, password: typing.Union[str, None] = None):
        if password is not None:
            self.force_send('PASS {}\r\n'.format(password))
        self.force_send('NICK {}\r\n'.format(username))

    def _connect(self):
        """Connect the IRC server."""
        self.socket = socket.socket()
        self.socket.connect((self.address, self.port))

    def send(self, message: typing.Union[str, irclib.ChannelMessage], queue='misc') -> None:
        """
        Queue a packet to be sent to the server.

        For sending a packet immediately use :py:meth:`force_send`.

        :param queue: Queue name
        :param message: Message to be sent to the server.
        :return: Nothing
        """
        if isinstance(message, irclib.ChannelMessage):
            if message.user == 'rcfile':
                irclib.info(str(message))
                return
            queue = message.channel
        if self.socket is not None or self.hold_send:
            irclib.info('Queued message: {}'.format(message))
            if queue not in self.queue:
                self.queue[queue] = []
                self.message_wait[queue] = time.time()
            self.queue[queue].append(to_bytes(message, 'utf-8'))
        else:
            irclib.info(f'Cannot queue message: {message!r}: Not connected.')

    def force_send(self, message: str):
        """
        Sent a packet to be sent to the server without making the packet wait.
        For queueing a packet use :py:meth:`send`.

        :param message: Message to be sent to the server.
        :return: Nothing
        """
        irclib.info('Force send message: {!r}'.format(message))
        self.queue['misc'].insert(0, to_bytes(message, 'utf-8'))
        self.flush_single_queue('misc', no_cooldown=True)

    def _send(self, message: bytes):
        if self.socket is None:
            return
        self.socket.send(message)

    def flush_single_queue(self, queue, no_cooldown=False, max_messages=1, now=time.time()):
        if self.hold_send:
            return 0
        if self.message_wait[queue] > now and not no_cooldown:
            return 0
        sent = 0
        for num, message in enumerate(self.queue[queue][:max_messages]):
            irclib.info(f'Sending message {message!r}')
            self._send(message)
            sent += 1
            self.message_wait[queue] = now + self.message_cooldown
        self.queue[queue] = self.queue[queue][max_messages:]
        return sent

    def flush_queue(self, max_messages: int = 1) -> int:
        if self.hold_send:
            return 0
        sent = 0
        now = time.time()
        for queue_name in self.queue:
            sent += self.flush_single_queue(queue_name, False, max_messages, now)
        return sent

    def receive(self):
        """Return all messages that are waiting to be read."""
        message = str(self.socket.recv(4096), 'utf-8', errors='ignore').replace('\r\n', '\n')
        # irclib.info(f'< {message!r}')
        if message == '':
            irclib.log('WARN', 'Empty message')
            self.disconnect()
            exit()
        self.receive_buffer += message

    def _remove_parted_channels(self):
        for i in self.channels_to_remove.copy():
            if not self.queue[i]:
                self.channels_to_remove.remove(i)
                del self.message_wait[i]
                del self.queue[i]

    def process_messages(self, max_messages: int = 1, mode=-1) -> typing.List[irclib.Message]:
        """
        Process the messages from self.receive_buffer
        Modes:
           * -1 every message. Nothing goes to self.receive_queue.
           *  0 chat messages. Other messages go to self.receive_queue.
           *  1 other messages. Chat messages go to self.receive_queue.
           *  2 do not return anything. Everything goes to self.receive_queue.

        :param max_messages: Maximum amount of messages to process.
        :param mode: What messages to return.
        :return: All messages specified by `mode`.
        """
        self._remove_parted_channels()
        messages_to_return = []
        messages_to_add_to_recv_queue = []
        for i in range(max_messages):
            if '\n' not in self.receive_buffer:
                break
            message = self.receive_buffer.split('\n', 1)[0]
            self.receive_buffer = self.receive_buffer.replace(message + '\n', '', 1)
            # Remove `message` from the buffer.
            if message == '':
                continue
            m = irclib.auto_message(message)
            if isinstance(m, irclib.ChannelMessage):
                if mode in [-1, 0]:
                    messages_to_return.append(m)
                else:
                    messages_to_add_to_recv_queue.append(m)
            else:
                if mode in [-1, 1]:
                    messages_to_return.append(m)
                else:
                    messages_to_add_to_recv_queue.append(m)
        self.receive_queue.extend(messages_to_add_to_recv_queue)
        return messages_to_return
