"""

This is a simple HTTP server which listens on port 8080, accepts connection request, and processes the client request
in separate threads.

It implements basic service functions (methods) which generate HTTP response to service the HTTP
requests. Currently there are 3 service functions; default, welcome and getFile.

The process function maps the request URL pattern to the service function. When the requested resource in the URL is
empty, the default function is called which currently invokes the welcome function.
The welcome service function responds with a simple HTTP response: "Welcome to my homepage".
The getFile service function fetches the requested html or img file and generates an HTTP response containing the file
contents and appropriate headers.

To extend this server's functionality, define your service function(s), and map it to suitable URL pattern in the
process function.

This web server runs on python v3
Usage: execute this program, open your browser (preferably chrome) and type http://servername:8080
e.g. if server.py and browser are running on the same machine, then use http://localhost:8080

"""

from socket import *
import _thread
import base64
import requests
import json


class Server:

	# We process client request here. The requested resource in the URL is mapped to a service function which generates the
	# HTTP response that is eventually returned to the client.
	def __init__(self):
		self.token = "pk_25bf16864f614cd2bcee257a341c7e72"

		# username and password
		self.key = base64.b64encode(bytes('%s:%s' % (13136165, 13136165), 'utf-8')).decode('ascii')

		with open("portfolio.json", "r", newline="") as datafile:
			self.portfolio = json.load(datafile)

		server_socket = socket(AF_INET, SOCK_STREAM)

		server_port = 8080
		server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		server_socket.bind(("", server_port))

		server_socket.listen(5)
		print('The server is running')
		# Server should be up and running and listening to the incoming connections
		# Main web server loop. It simply accepts TCP connections, and get the request processed in seperate threads.
		while True:
			# Set up a new connection from the client
			conn_sock, addr = server_socket.accept()
			# Clients timeout after 60 seconds of inactivity and must reconnect.
			conn_sock.settimeout(60)
			# start new thread to handle incoming request
			_thread.start_new_thread(self.process, (conn_sock,))

	def process(self, connection_socket):
		def get_PL(symbol):
			latest_quote = requests.get(
				"https://cloud.iexapis.com/stable/stock/{}/quote?token={}".format('AAPL', self.token)).json()[
				'iexRealtimePrice']
			price = self.portfolio[symbol]['price']
			return str(round((latest_quote - price) / price * 100)) + "%"

		def get_symbols():
			api_url = "https://cloud.iexapis.com/stable/ref-data/symbols?token={}".format(self.token)
			return {"symbols": [i['symbol'] for i in requests.get(api_url).json() if i['type'] == 'cs']}

		# Extract the given header value from the HTTP request message
		def get_header(message, header):
			if message.find(header) > -1:
				value = message.split(header)[1].split()[2]
			else:
				value = None
			return value

		def stock():
			header = ""
			body = ""
			# Send the HTTP response header line to the connection socket
			connection_socket.send(header)
			# Send the content of the HTTP body (e.g. requested file) to the connection socket
			connection_socket.send(body)
			# Close the client connection socket
			connection_socket.close()

		def portfolio():
			header = "HTTP/1.1 200 OK\r\n\r\n".encode()
			with open("portfolio.html") as datafile:
				body = datafile.read().encode()
			# Send the HTTP response header line to the connection socket
			connection_socket.send(header)
			# Send the content of the HTTP body (e.g. requested file) to the connection socket
			connection_socket.send(body)
			# Close the client connection socket
			connection_socket.close()

		# service function to generate HTTP response with a simple welcome message
		def welcome():
			header = "HTTP/1.1 200 OK\r\n\r\n".encode()
			body = "<html><head></head><body><h1>Welcome to my homepage</h1></body></html>\r\n".encode()
			connection_socket.send(header)
			# Send the content of the HTTP body (e.g. requested file) to the connection socket
			connection_socket.send(body)
			# Close the client connection socket
			connection_socket.close()

		# Receives the request message from the client
		message = connection_socket.recv(1024).decode()

		if len(message) > 1:
			# Extract the path of the requested object from the message
			# Because the extracted path of the HTTP request includes
			# a character '/', we read the path from the second character
			print("Message")
			print(message)

			if get_header(message, "Authorization") == None:
				connection_socket.send(
					'HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Demo Realm"\r\n\r\n'.encode())

			elif get_header(message, 'Authorization') == str(self.key):

				resource = message.split()[1][1:]

				print("Resource")
				print(resource)

				# map requested resource (contained in the URL) to specific function which generates HTTP response
				if resource == "portfolio":
					portfolio()
				elif resource == "symbols":
					header = "HTTP/1.1 200 OK\r\n\r\n".encode()
					connection_socket.send(header)
					connection_socket.send(json.dumps(get_symbols(), indent=2).encode('utf-8'))
					connection_socket.close()
				elif resource == "portfoliodata":
					header = "HTTP/1.1 200 OK\r\n\r\n".encode()
					connection_socket.send(header)
					connection_socket.send(json.dumps(self.portfolio, indent=2).encode('utf-8'))
					connection_socket.close()
				elif resource == "stock":
					stock()
				else:
					welcome()


# service function to fetch the requested file, and send the contents back to the client in a HTTP response.
# def getFile(filename):
# 	try:
# 		# open and read the file contents. This becomes the body of the HTTP response
# 		f = open(filename, "rb")
#
# 		body = f.read()
# 		header = "HTTP/1.1 200 OK\r\n\r\n".encode()
#
# 	except IOError:
# 		# Send HTTP response message for resource not found
# 		header = "HTTP/1.1 404 Not Found\r\n\r\n".encode()
# 		body = "<html><head></head><body><h1>404 Not Found</h1></body></html>\r\n".encode()
#
# 	return header, body
if __name__ == "__main__":
	Server()
