"""

This is a simple HTTP server which listens on port 8080, accepts connection request, and processes the client request
in separate threads.

It implements basic service functions (methods) which generate HTTP response to service the HTTP
requests - these are mapped from the url.

There are 2 main service functions - stock, portfolio

The other service functions are called from the client via HTML. These functions make use of AJAX to update the pages
dynamically.

One POST request is employed to verify that the local portfolio file (stored in JSON) always matches the HTML table

The process function maps the request URL pattern to the service function. When the requested resource in the URL is
empty, the server defaults to a simple homepage that lists the domains which can be accessed to use functionality

This web server runs on python v3
This server runs on heroku cloud but can also run locally on port 8080 - comment line 54

"""
import datetime
import time
from socket import *
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import _thread
import base64
import requests
import json
import os


class Server:

	# We process client request here. The requested resource in the URL is mapped to a service function which generates the
	# HTTP response that is eventually returned to the client.
	def __init__(self):
		self.token = "pk_25bf16864f614cd2bcee257a341c7e72"

		# username and password
		self.key = base64.b64encode(bytes('%s:%s' % (13136165, 13136165), 'utf-8')).decode('ascii')

		self.portfolio = None

		with open("SP500_ticker.json", "r", newline="") as datafile:
			self.tickers = [i['Symbol'] for i in json.load(datafile)]

		server_socket = socket(AF_INET, SOCK_STREAM)

		server_port = 8080
		# server_port = int(os.environ.get('PORT'))
		server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		server_socket.bind(("", server_port))

		server_socket.listen(5)
		# Server should be up and running and listening to the incoming connections
		# Main web server loop. It simply accepts TCP connections, and get the request processed in seperate threads.
		while True:
			# Set up a new connection from the client
			conn_sock, addr = server_socket.accept()
			# Clients timeout after 60 seconds of inactivity and must reconnect.
			conn_sock.settimeout(60)
			# start new thread to handle incoming request
			_thread.start_new_thread(self.process, (conn_sock,))

	def load_portfolio(self):
		with open("portfolio.json", "r", newline="") as datafile:
			self.portfolio = json.load(datafile)

	def process(self, connection_socket):

		self.load_portfolio()

		# update the profit loss of a stock
		def set_gain_loss():
			for i in range(len(self.portfolio['stocks'])):
				s = self.portfolio['stocks'][i]
				latest_quote = requests.get("https://cloud.iexapis.com/stable/stock/{}/quote?token={}".format(s['stock'], self.token)).json()['close']
				self.portfolio['stocks'][i]['pl'] = str(round((latest_quote - float(s['price'])) / float(s['price']) * 100)) + "%"
			with open('portfolio.json', 'w') as json_file:
				json.dump(self.portfolio, json_file)

		# helper method to get all current symbols
		def get_symbols():
			api_url = "https://cloud.iexapis.com/stable/ref-data/symbols?token={}".format(self.token)
			return {"symbols": [i['symbol'] for i in requests.get(api_url).json() if i['symbol'] in self.tickers]}

		# Extract the given header value from the HTTP request message
		def get_header(message, header):
			if message.find(header) > -1:
				value = message.split(header)[1].split()[2]
			else:
				value = None
			return value

		# if chart doesn't exist
		def make_chart(msg):
			path = '{}.png'.format(msg)
			url = "https://cloud.iexapis.com/stable/stock/{}/chart/ytd?chartCloseOnly=true&token={}".format(msg, self.token)
			x_values = [datetime.datetime.strptime(d['date'], "%Y-%m-%d").date() for d in requests.get(url).json()]
			ax = plt.gca()
			formatter = mdates.DateFormatter("%Y-%m-%d")
			ax.xaxis.set_major_formatter(formatter)
			locator = mdates.MonthLocator()
			ax.xaxis.set_major_locator(locator)
			plt.plot(x_values, [i['close'] for i in requests.get(url).json()])
			plt.savefig(path)
			return base64.b64encode(open(path, 'rb').read())

		def get_chart(msg):
			path = '{}.png'.format(msg)
			if os.path.exists(path):
				print("image found")
				return base64.b64encode(open(path, 'rb').read())
			else:
				return make_chart(msg)

		# send stock chart html to client
		def stock():
			with open("stock.html") as datafile:
				body = datafile.read().encode()
			send_success(body)

		# send portfolio html to client
		def portfolio():
			with open("portfolio.html") as datafile:
				body = datafile.read().encode()
			send_success(body)

		def update_portfolio(msg):
			new_stock = {}
			for i in msg.split("&"):
				new_stock[i.split('=')[0]] = i.split('=')[1]
			new_stock['pl'] = "0%"
			current_stocks = [i['stock'] for i in self.portfolio['stocks']]
			# if long
			if float(new_stock['quantity']) > 0:
				# check if stock is in prortfolio already
				if new_stock['stock'] not in current_stocks:
					self.portfolio['stocks'].append(new_stock)
				else:
					for i in range(len(self.portfolio['stocks'])):
						if self.portfolio['stocks'][i]['stock'] == new_stock['stock']:
							self.portfolio['stocks'][i]['quantity'] = str(round(float(self.portfolio['stocks'][i]['quantity']) + float(new_stock['quantity'])))
							self.portfolio['stocks'][i]['price'] = str(round((float(self.portfolio['stocks'][i]['quantity']) * float(self.portfolio['stocks'][i]['price']) + float(new_stock['quantity']) * float(new_stock['price'])) / (float(new_stock['quantity']) + float(self.portfolio['stocks'][i]['quantity']))))
							break
			else:
				count = 0
				for i in self.portfolio['stocks']:
					if i['stock'] == new_stock['stock']:
						new_quantity = float(self.portfolio['stocks'][count]['quantity']) + float(new_stock['quantity'])
						if new_quantity < 0:
							return
						self.portfolio['stocks'][count]['quantity'] = str(new_quantity)

					count += 1

			with open('portfolio.json', 'w') as json_file:
				json.dump(self.portfolio, json_file)
			set_gain_loss()

		def clear_portfolio():
			with open('portfolio.json', 'w') as json_file:
				json.dump({"stocks": []}, json_file)

		# service function to generate HTTP response with a simple welcome message
		def welcome():
			body = "<html><head></head><body><h1>Stock Portfolio Tool - use /stock and /portfolio </h1></body></html>\r\n".encode()
			send_success(body)

		def send_success(body):
			success = "HTTP/1.1 200 OK\r\n\r\n".encode()
			connection_socket.send(success)
			# Send the content of the HTTP body (e.g. requested file) to the connection socket
			connection_socket.send(body)
			# Close the client connection socket
			connection_socket.close()

		# Receives the request message from the client
		message = connection_socket.recv(1024).decode()

		if len(message) > 1:
			# check authorization
			if get_header(message, "Authorization") == None:
				connection_socket.send(
					'HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Demo Realm"\r\n\r\n'.encode())
			# if authorized
			elif get_header(message, 'Authorization') == str(self.key):

				resource = message.split()[1][1:]

				# map requested resource (contained in the URL) to specific function which generates HTTP response
				if message.split()[0] == 'POST':
					if resource == "portfolio":
						update_portfolio(message.split()[-1])
						portfolio()
				elif resource == "portfolio":
					portfolio()
				elif resource == "portfolioClear":
					clear_portfolio()
					header = "HTTP/1.1 200 OK\r\n\r\n".encode()
					connection_socket.send(header)
					connection_socket.close()
				elif len(resource.split("/")) > 1 and resource.split("/")[1]:
					send_success(get_chart(resource.split("/")[1]))
				elif resource.split("/")[0] == "stock":
					stock()
				elif resource == "symbols":
					send_success(json.dumps(get_symbols(), indent=2).encode('utf-8'))
				elif resource == "portfoliodata":
					send_success(json.dumps(self.portfolio, indent=2).encode('utf-8'))
				elif resource == "stock":
					stock()
				else:
					welcome()

if __name__ == "__main__":
	Server()
