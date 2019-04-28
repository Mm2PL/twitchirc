import time
import typing

import irclib


def get_no_permission_generator(bot: irclib.Bot):
    def permission_error_handler(event, msg: irclib.ChannelMessage,
                                 command: irclib.Command,
                                 missing_permissions: typing.List[str]):
        del event
        if command is None:
            return
        bot.send(msg.reply(f"@{msg.user} You are missing permissions ({', '.join(missing_permissions)}) to use "
                           f"command {command.chat_command}."))

    bot.handlers['permission_error'].append(permission_error_handler)


def get_perm_command(bot: irclib.Bot):
    @irclib.require_permission(irclib.PERMISSION_COMMAND_PERM)
    @bot.add_command(command='perm', forced_prefix=None, enable_local_bypass=True)
    def command_perm(msg: irclib.ChannelMessage):
        p = irclib.ArgumentParser(prog='!perm', add_help=False)
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument('-a', '--add', metavar=('USER', 'PERMISSION'), nargs=2, dest='add')
        g.add_argument('-r', '--remove', metavar=('USER', 'PERMISSION'), nargs=2, dest='remove')
        g.add_argument('-l', '--list', metavar='USER', const=msg.user, default=None, nargs='?', dest='list')
        g.add_argument('-h', '--help', action='store_true', dest='help')
        args = p.parse_args(args=msg.text.split(' ')[1:])
        if args is None or args.help:
            usage = msg.reply(f'@{msg.user} {p.format_usage()}')
            bot.send(usage)
            return
        if args.add:
            if bot.check_permissions(msg, [irclib.PERMISSION_COMMAND_PERM_ADD], enable_local_bypass=False):
                bot.send(msg.reply(f"@{msg.user} You cannot use !perm -a, since you don't have"
                                   f"the {irclib.PERMISSION_COMMAND_PERM_ADD} permission"))
                return
            if args.add[0] not in bot.permissions:
                bot.permissions[args.add[0]] = []
            if args.add[1] not in bot.permissions[args.add[0]]:
                bot.permissions[args.add[0]].append(args.add[1])
                bot.send(msg.reply(f'@{msg.user} Given permission {args.add[1]} to user {args.add[0]}.'))
            else:
                bot.send(msg.reply(f'@{msg.user} User {args.add[0]} already has permission {args.add[1]}.'))
                return
        elif args.remove:
            if bot.check_permissions(msg, [irclib.PERMISSION_COMMAND_PERM_REMOVE], enable_local_bypass=False):
                bot.send(msg.reply(f"@{msg.user} You cannot use !perm -r, since you don't have"
                                   f"the {irclib.PERMISSION_COMMAND_PERM_REMOVE} permission"))
                return
            if args.remove[0] not in bot.permissions:
                bot.permissions[args.remove[0]] = []
            if args.remove[1] not in bot.permissions[args.remove[0]]:
                bot.send(msg.reply(f"@{msg.user} User {args.remove[0]} already "
                                   f"doesn't have permission {args.remove[1]}."))
                return
            else:
                bot.permissions[args.remove[0]].remove(args.remove[1])
                bot.send(msg.reply(f'@{msg.user} Removed permission {args.remove[1]} from user {args.remove[0]}.'))
                return
        elif args.list:
            if bot.check_permissions(msg, [irclib.PERMISSION_COMMAND_PERM_LIST]):
                bot.send(msg.reply(f"@{msg.user} You cannot use !perm -l, since you don't have"
                                   f"the {irclib.PERMISSION_COMMAND_PERM_LIST} permission"))
                return
            args.list = args.list.lower()
            if args.list not in bot.permissions:
                bot.permissions[args.list] = []
            if args.list == msg.user:
                output = ', '.join(bot.permissions.get_permission_state(msg))
                bot.send(msg.reply(f'You have permissions: {output}'))
            else:
                output = ', '.join(bot.permissions[args.list])
                bot.send(msg.reply(f'User {args.list} has permissions: {output}'))

            return


def get_quit_command(bot: irclib.Bot):
    @irclib.require_permission(irclib.PERMISSION_COMMAND_QUIT)
    @bot.add_command(command='quit', forced_prefix=None, enable_local_bypass=False)
    def command_quit(msg: irclib.ChannelMessage):
        bot.send(msg.reply('Quitting.'))
        bot.stop()


def get_part_command(bot: irclib.Bot):
    @irclib.require_permission(irclib.PERMISSION_COMMAND_PART)
    @bot.add_command(command='part', forced_prefix=None)
    def command_part(msg: irclib.ChannelMessage):
        p = irclib.ArgumentParser(prog='!part', add_help=False)
        p.add_argument('channel', metavar='CHANNEL', nargs='?', const=msg.channel, default=msg.channel)
        p.add_argument('-h', '--help', action='store_true', dest='help')
        args = p.parse_args(msg.text.split(' ')[1:])
        if args is None or args.help:
            usage = msg.reply(f'@{msg.user} {p.format_usage()}')
            bot.send(usage)
            return
        if args.channel == '':
            args.channel = msg.channel
        channel = args.channel.lower()
        if channel != msg.channel.lower() and bot.check_permissions(msg, [irclib.PERMISSION_COMMAND_PART_OTHER],
                                                                    enable_local_bypass=False):
            bot.send(msg.reply(f"Cannot part from channel {channel}: your permissions are not valid in that channel."))
            return
        if channel not in bot.channels_connected:
            bot.send(msg.reply(f'Not in {channel}'))
            return
        else:
            bot.send(msg.reply(f'Parting from {channel}'))
            m = irclib.ChannelMessage('Bye.', 'OUTGOING', channel)
            m.outgoing = True
            bot.send(m)
            bot.flush_single_queue(msg.channel)
            bot.part(channel)


def get_join_command(bot: irclib.Bot):
    @irclib.require_permission(irclib.PERMISSION_COMMAND_JOIN)
    @bot.add_command(command='join', forced_prefix=None, enable_local_bypass=False)
    def command_join(msg: irclib.ChannelMessage):
        chan = msg.text.split(' ')[1].lower()
        if chan in ['all']:
            bot.send(msg.reply(f'Cannot join #{chan}.'))
            return
        if chan in bot.channels_connected:
            bot.send(msg.reply(f'This bot is already in channel #{chan}.'))
        else:
            bot.send(msg.reply(f'Joining channel #{chan}.'))
            bot.join(chan)
