from six import string_types

from .exceptions import SlackError


class Slack(object):

    def __init__(self, app=None):
        self._commands = {}

        if app:
            self.init_app(app)

    def init_app(self, app=None):
        """Initialize application configuration"""
        self._app = app
        config = getattr(app, 'config', app)
        self._config = config

    def command(self, command, token=None, methods=['GET'], **kwargs):
        """A decorator used to register a command.
        Example::

            @slack.command('your_command', token='your_token',
                           methods=['POST'])
            def your_method(**kwargs):
                text = kwargs.get('text')
                return slack.response(text)

        :param command: the command to register
        :param token: your command token provided by slack
        :param methods: optional. HTTP methods which are accepted to
                        execute the command
        :param kwargs: optional. the optional arguments which will be passed
                       to your register method
        """
        def deco(func):
            self._commands[command] = (func, token, methods, kwargs)
            return func
        return deco

    def dispatch(self):
        """Dispatch http request to registerd commands.
        Example::

            slack = Slack(app)
            app.add_url_rule('/', view_func=slack.dispatch)
        """
        from flask import request

        method = request.method

        data = request.args
        if method == 'POST':
            data = request.form

        token = data.get('token')
        command = data.get('command') or data.get('trigger_word')

        if isinstance(command, string_types):
            command = command.strip().lstrip('/')

        try:
            self.validate(command, token, method)
        except SlackError as e:
            return self.response(e.msg)

        func, _, _, kwargs = self._commands[command]
        kwargs.update(data.to_dict())

        return func(**kwargs)

    dispatch.methods = ['GET', 'POST']

    def validate(self, command, token, method):
        """Validate request queries with registerd commands

        :param command: command parameter from request
        :param token: token parameter from request
        :param method: the request method
        """
        if command not in self._commands:
            raise SlackError('Command {0} is not found'.format(
                             command))

        func, _token, methods, kwargs = self._commands[command]

        if method not in methods:
            raise SlackError('{} request is not allowed'.format(method))

        if _token and token != _token:
            raise SlackError('Your token {} is invalid'.format(token))

    def response(self, text, response_type='ephemeral', attachments=None):
        """Return a response with json format

        :param text: the text returned to the client
        :param response_type: optional. When `in_channel` is assigned,
                              both the response message and the initial
                              message typed by the user will be shared
                              in the channel.
                              When `ephemeral` is assigned, the response
                              message will be visible only to the user
                              that issued the command.
        :param attachments: optional. A list of additional messages
                            for rich response.
        """
        from flask import jsonify
        if attachments is None:
            attachments = []

        data = {
            'response_type': response_type,
            'text': text,
            'attachments': attachments,
        }
        return jsonify(**data)
