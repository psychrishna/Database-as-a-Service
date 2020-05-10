from werkzeug.exceptions import MethodNotAllowed
from flask import Flask,request,jsonify,abort
import requests as send_request
import json
from flask import make_response
from datetime import datetime
import pandas as pd


dbaas_url = "http://18.210.102.92"
load_balancer_url = "CC-Assignment-3-907148319.us-east-1.elb.amazonaws.com"
rides_ip = '54.156.206.230'


df = pd.read_csv("AreaNameEnum.csv")
area_dict = dict()

COUNTER_TABLE = 'rides_counter_table'

for i in range(len(df)):
	area_dict[df['Area No'][i]]=df['Area Name'][i]

app = Flask(__name__)



empty_response = app.make_response('{}') #default 200 OK send this response for sending 200 OK



def increment_counter():
	data_to_send = dict()
	data_to_send['table'] = 'rides_counter_table'
	data_to_send['operation'] = 'update'
	data_to_send['data'] = {'$inc': {'http_counter':1}}
	data_to_send['filter'] = {}

	response_recieved = send_request.post( dbaas_url + '/api/v1/write',json=data_to_send)
	
	


	#db.rides_counter_table.update({},{'$inc' : {'http_counter' : 1}})



@app.route("/api/v1/rides/count",methods = ["GET"])
def get_total_rides_count():

	increment_counter()

	data_to_send = {}
	data_to_send['table'] = 'rides'
	data_to_send['conditions'] = {}
	response_received = send_request.post( dbaas_url + '/api/v1/read',json=data_to_send)
	if(response_received.status_code==204):
		return jsonify([0])
		
	data = response_received.json()
	return jsonify([len(data)])

@app.route("/api/v1/db/clear",methods=["POST"])
def clear_db():
	response_recieved = send_request.post( dbaas_url + '/api/v1/db/clear')
	return empty_response
	
"""
Total HTTP requests made

GET Request
Route : /api/v1/_count

Response Codes : 200,405

Reset HTTP Counter

DELETE Request
Route : /api/v1/_count

Response Code : 200,405

"""	


@app.route("/api/v1/_count",methods = ["GET","DELETE"])
def total_requests():
	
	if request.method == 'GET':
		
		data_to_send = dict()
		data_to_send['table'] = 'rides_counter_table'
		data_to_send['conditions'] = {}

		response_recieved = send_request.post( dbaas_url + '/api/v1/read',json = data_to_send)

		data_recieved = response_recieved._content

		json_data = json.loads(data_recieved)
		counter = json_data[0]['http_counter']

		
		if(response_recieved.status_code == 200):
			return jsonify([counter])
	
	else:

		data_to_send = dict()
		data_to_send['table'] = 'rides_counter_table'
		data_to_send['operation'] = 'update'
		data_to_send['data'] = {"http_counter":0}
		data_to_send['filter'] = {}

		response_recieved = send_request.post( dbaas_url + '/api/v1/write',json=data_to_send)

		print(response_recieved.status_code)

		if(response_recieved.status_code == 200):
			response_200 = make_response('{}', 200)
			return response_200

				
"""
3. Add Ride
POST Request
body Format
{
	"created by":"username"
	"timestamp": "D/m/y:s/m/h"
	"source": "source"
	"destination":"destination"

5. List all upcoming rides for a given source and destination
}
"""

@app.route("/api/v1/rides",methods = ["POST","GET"])
def add_ride():
	response_400 = make_response('{}',400)
	if request.method == 'POST':
		
		increment_counter()

		print("recieved a request to add ride")
		ride_details = request.get_json()
		
		try:
			ride_details['source'] = area_dict[int(ride_details['source'])]
			ride_details['destination'] = area_dict[int(ride_details['destination'])]
		except:
			abort(400)

		custom_headers = {'Origin':rides_ip}	#fill ip with public ip or dns ip of rides instance
		response_received = send_request.get( load_balancer_url + '/api/v1/users',headers = custom_headers) #fill the ip with that of load balancer
		
		if(response_received.status_code == 204):
			abort(400)
		
		elif(ride_details["created_by"] not in list(response_received.json())):
			abort(400)
		
		else:
			response_received = send_request.post( dbaas_url + '/api/v1/read',json = {"table":"rides","conditions":{}})
			max_rideID = -1
			if(response_received.status_code != 204):
				data_recieved = response_received.json()
				for row in data_recieved:
					if(int(row['rideId']) > max_rideID ):
						max_rideID = int(row['rideId'])
			rideId = max_rideID + 1
			ride_details['rideId'] = rideId
			ride_details['users'] = []
		# ride_details['users'] = [ride_details["created_by"]]
			data_send = {}
			data_send['operation'] = 'insert'
			data_send['data'] = ride_details
			data_send['table'] = 'rides'
			print(data_send)
			response_recieved = send_request.post( dbaas_url + '/api/v1/write',json=data_send)
			if(response_recieved.status_code == 200):
				response_201 = make_response('{}', 201)
				return response_201
	else:

		increment_counter()

		print('received a request to list rides')
		source = request.args.get('source')
		destination = request.args.get('destination')
		try:
			source = area_dict[int(source)]
			destination = area_dict[int(destination)]
		except :
			return response_400
		response_400 = make_response('{}',400)
		response_204 = make_response('{}',204)
		

		if(source == None or destination == None):
			return response_400

		data_to_send = {}
		data_to_send['table'] = 'rides'
		data_to_send['conditions'] = {'source': source, 'destination': destination}

		response_received = send_request.post( dbaas_url + '/api/v1/read',json = data_to_send)
	
		response_400 = make_response('{}',400)
		response_204 = make_response('{}',204)
		if(response_received.status_code == 204):
			return response_204
		# assumed that the response of above returns a array of json objects which just need to be returned.
		else:
			data = response_received.json()			
			response_data = []
			print(data)
			for i in data:
				temp = dict()
				print(i)
				temp['rideId'] = i['rideId']
				temp['username'] = i['created_by']
				temp['timestamp'] = i['timestamp']

				time_now = datetime.now()
				time_created = datetime.strptime(temp['timestamp'],'%d-%m-%Y:%H-%M-%S')

				if(time_created >= time_now):						
					response_data.append(temp)

			return jsonify(response_data)


"""
6. update a given ride
request body:
{
	username: username
}
"""

@app.route("/api/v1/rides/<rideId>",methods = ["DELETE","POST"])
def delete_ride(rideId):
	response_400 = make_response('{}',400)
	if request.method == "POST":

		increment_counter()

		flag=1
		response_data = request.get_json()
		data_to_send = dict()
		data_to_send['table'] = 'rides'
		try:
			data_to_send['conditions'] = {"rideId":int(rideId)}
		except:
			abort(400)

		response_received = send_request.post( dbaas_url + '/api/v1/read',json = data_to_send)
		
		if(response_received.status_code == 204):
			flag =0

		custom_headers = {'Origin':rides_ip}
		response_received = send_request.get( load_balancer_url + "/api/v1/users",headers = custom_headers)
		
		if(response_received.status_code==200):
			data = response_received.json()
			try:
				if(response_data['username'] not in data):
					flag = 0 
			except:
				abort(400)	
		else:
			flag = 0
		

		if(flag==0):
			return response_400	
		else:
			data_to_send = dict()
			data_to_send['table'] = 'rides'
			data_to_send['conditions'] = {"rideId":int(rideId),"users":response_data["username"]}
			response_received = send_request.post( dbaas_url + '/api/v1/read',json = data_to_send)
			response_400 = make_response('{}',400)
			if(response_received.status_code == 200):
				return response_400

			data_to_send = {}
			data_to_send['table'] = 'rides'
			data_to_send['operation'] = 'update'
			data_to_send['filter'] = {"rideId":int(rideId)}
			data_to_send['data'] = {"$push": {"users": response_data["username"]}}
			
			response_received = send_request.post( dbaas_url + '/api/v1/write',json = data_to_send)
			
			if(response_received.status_code == 200):
				response_data = make_response('{}', 200)
				return response_data
			else:
				response_data = make_response('{}', 400)
				return response_data
	else:

		increment_counter()

		print("Recieved request to delete the ride with rideId :",rideId)

		data_to_send = dict()
		data_to_send['table'] = 'rides'
		data_to_send['operation'] = 'delete'
		try:
			data_to_send['data'] = {"rideId":int(rideId)}
		except:
			abort(400)
		response_recieved = send_request.post( dbaas_url +'/api/v1/write',json = data_to_send)

		if(response_recieved.status_code  == 405):
			abort(400)
		else:
			return empty_response	


@app.route("/api/v1/rides/<rideId>",methods = ["GET"])
def details_of_ride(rideId):

	increment_counter()

	print("Received request to display all the details of ride with ride ID :",rideId)

	data_to_send = dict()
	try:
		data_to_send['table'] = 'rides'
		data_to_send['conditions'] = {"rideId":int(rideId)}
	except:
		abort(400)
	response_recieved = send_request.post( dbaas_url +'/api/v1/read',json = data_to_send)

	#print(response_recieved.__dict__


	response_204 = make_response('{}',204)

	if(response_recieved.status_code == 204):
		return response_204
	elif(response_recieved.status_code == 200):
		data_recieved = response_recieved.json()[0]
		return jsonify(data_recieved)
	else:
		abort(405)	
"""
8.Write a DB

POST Request
Body Format FOR insert update
{
	"operation":"insert","update"
	"data":data  // A row in JSON format
	"table" :"tablename" 
}

Body Format
{
	"operation":"update"
	"data":"data_to_Be updated"
	"table":"table_name"
	"filter":"filter for documents"


}
"""

@app.errorhandler(MethodNotAllowed)
def handle_exception(e):
	increment_counter()
	response = e.get_response()
	print(response)
	return response



if __name__ == '__main__':	
	app.debug=True
	app.run(host="0.0.0.0",port=5000,threaded=True)  #Threaded to have Mutliple concurrent requests
