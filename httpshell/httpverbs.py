import Cookie
import formatters
import httplib2
import json
import oauth2 as oauth
import os
import subprocess
import version


class HttpVerb(object):
    def __init__(self, args, logger, verb):
        self.args = args
        self.logger = logger
        self.verb = verb

    def run(self, url, path, pipe=None, headers=None, cookies=None, body=""):
        self.url = url
        self.path = path
        self.pipe = pipe
        self.headers = headers
        self.cookies = cookies

        host = self.url.netloc

        http = self.init_httpclient()
        http.follow_redirects = False
        httplib2.debuglevel = self.args.debuglevel

        # check for authentication credentials
        if "@" in host:
            split = host.split("@")
            if len(split) > 1:
                host = split[1]
                creds = split[0].split(":")
                self.http.add_credentials(creds[0], creds[1])
            else:
                host = split[0]

        uri = ("{0}://{1}{2}".format(self.url.scheme, host, self.path))

        if not self.args.disable_cookies:
            self.set_request_cookies()

        if not "host" in self.headers:
            self.headers["host"] = host
        if not "accept-encoding" in self.headers:
            self.headers["accept-encoding"] = "gzip, deflate"
        if not "user-agent" in self.headers:
            self.headers["user-agent"] = "httpsh/" + version.VERSION

        self.logger.print_text("Connecting to " + uri)

        response, content = http.request(
            uri, method=self.verb, body=body, headers=headers)

        self.handle_response(response, content)

    def init_httpclient(self):
        http = None

        keysfile = os.path.join(os.path.expanduser("~"),
            ".httpshell", self.url.netloc + ".json")

        if os.path.isfile(keysfile):
            try:
                with open(keysfile, "r") as file:
                    keys = json.load(file)
                    token = None

                    consumer = oauth.Consumer(keys["consumer"]["consumer-key"],
                        keys["consumer"]["consumer-secret"])
                    if "access" in keys:
                        token = oauth.Token(keys["access"]["access-token"],
                            keys["access"]["access-token-secret"])

                    http = oauth.Client(consumer, token)
            except:
                self.logger.print_error(
                    "Failed reading OAuth data from: " + keysfile)
        else:
            http = httplib2.Http()

        return http

    def set_request_cookies(self):
        if self.url.netloc in self.cookies:
            l = []
            cookie = self.cookies[self.url.netloc]
            #  very basic cookie support atm.  no expiry, etc.
            for morsel in cookie.values():
                l.append(morsel.key + "=" + morsel.coded_value)
            self.headers["cookie"] = "; ".join(l)

    def handle_response(self, response, content):
        self.logger.print_response_code(response)
        if self.args.show_headers:
            self.logger.print_headers(self.headers.items(), True)
            self.logger.print_headers(response.items())

        if not self.args.disable_cookies:
            self.store_response_cookies(response)

        if self.args.auto_format:
            mimetype = response["content-type"]

            if mimetype:
                content = formatters.format_by_mimetype(
                    content, mimetype.split(";")[0])

        if self.pipe:
            content = self.pipe_data(self.pipe, content)

        self.logger.print_data(content)

    def store_response_cookies(self, response):
        if "set-cookie" in response:
            header = response["set-cookie"]
            cookie = Cookie.SimpleCookie(header)
            self.cookies[self.url.netloc] = cookie

    # pipes output to external commands like xmllint, tidy for filtering
    def pipe_data(self, command, data):
        result = None

        p = subprocess.Popen(command, shell=True, bufsize=-1,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        output, error = p.communicate(data)

        if error:
            self.logger.print_text()
            self.logger.print_error(error.decode("utf-8"))
        else:
            result = output.decode("utf-8")

        return result


class HttpHead(HttpVerb):
    def __init__(self, args, logger):
        super(HttpHead, self).__init__(args, logger, "HEAD")


class HttpGet(HttpVerb):
    def __init__(self, args, logger):
        super(HttpGet, self).__init__(args, logger, "GET")


class HttpPost(HttpVerb):
    def __init__(self, args, logger):
        super(HttpPost, self).__init__(args, logger, "POST")


class HttpPut(HttpVerb):
    def __init__(self, args, logger):
        super(HttpPut, self).__init__(args, logger, "PUT")


class HttpDelete(HttpVerb):
    def __init__(self, args, logger):
        super(HttpDelete, self).__init__(args, logger, "DELETE")


class HttpTrace(HttpVerb):
    def __init__(self, args, logger):
        super(HttpTrace, self).__init__(args, logger, "TRACE")


class HttpOptions(HttpVerb):
    def __init__(self, args, logger):
        super(HttpOptions, self).__init__(args, logger, "OPTIONS")
