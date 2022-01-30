from flask import Flask, render_template, request
import requests, json, xmltodict, pickle

app = Flask(
	__name__,
	template_folder = 'templates',
	static_folder = 'static'
)

@app.route("/")
def index():
  res = requests.get("https://inciweb.nwcg.gov/feeds/rss/incidents/")
  data = xmltodict.parse(res.content)
  data = data["rss"]["channel"]["item"]

  activeWildfires = []

  for item in data:
    if not "Prescribed Fire" in item["title"] and not "Burned Area Emergency Response" in item["title"]:
      trimmedTitle = item["title"].rpartition(' (')[0]

      lat = item["geo:lat"]
      long = item["geo:long"]
      res = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng=" + lat + ", " + long + "&key=AIzaSyD2ZWo9VogormcvsIxF3U8e0yCB84O0p8c")
      data = res.json()
      formattedAddress = data["results"][0]["formatted_address"]
      trimmedFormattedAddress = formattedAddress[:len(formattedAddress) - 5]
      if (trimmedFormattedAddress[len(trimmedFormattedAddress)-1].isdigit()):
        trimmedFormattedAddress = trimmedFormattedAddress[:len(trimmedFormattedAddress) - 6]
      
      strippedFormattedAddress = ""
      numSpaces = 0
      for c in trimmedFormattedAddress[::-1]:
        if c == " ":
          numSpaces += 1
        if numSpaces < 2:
          strippedFormattedAddress += c

      strippedFormattedAddress = strippedFormattedAddress[::-1]
      
      if len(strippedFormattedAddress) > 3:
        wildfireInfo = trimmedTitle + " — " + strippedFormattedAddress
        activeWildfires.append(wildfireInfo)
        
  activeWildfires = sorted(activeWildfires, key = lambda x:x[-2])

  return render_template("index.html", wildfires=activeWildfires)

@app.route("/location", methods=["POST"])
def location():
  res = requests.get("https://maps.googleapis.com/maps/api/geocode/json?components=country:US%7Cpostal_code:" + request.form.get("zip-code", "94010") + "&key=AIzaSyD2ZWo9VogormcvsIxF3U8e0yCB84O0p8c")
  data = res.json()
  formattedAddress = data["results"][0]["formatted_address"]

  trimmedFormattedAddress = ""
  for c in formattedAddress:
    if c.isdigit():
      trimmedFormattedAddress = trimmedFormattedAddress[:-1]
      break  
    trimmedFormattedAddress += c
  
  state = trimmedFormattedAddress[-2:]

  res = requests.get("https://inciweb.nwcg.gov/feeds/rss/incidents/")
  data = xmltodict.parse(res.content)
  data = data["rss"]["channel"]["item"]

  nearbyWildfires = []

  for item in data:
    if not "Prescribed Fire" in item["title"] and not "Burned Area Emergency Response" in item["title"]:
      trimmedTitle = item["title"].rpartition(' (')[0]

      lat = item["geo:lat"]
      long = item["geo:long"]
      res2 = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng=" + lat + ", " + long + "&key=AIzaSyD2ZWo9VogormcvsIxF3U8e0yCB84O0p8c")
      data2 = res2.json()
      formattedAddress2 = data2["results"][0]["formatted_address"]
      trimmedFormattedAddress2 = formattedAddress2[:len(formattedAddress2) - 5]
      if (trimmedFormattedAddress2[len(trimmedFormattedAddress2)-1].isdigit()):
        trimmedFormattedAddress2 = trimmedFormattedAddress2[:len(trimmedFormattedAddress2) - 6]
      
      strippedFormattedAddress = ""
      numSpaces = 0
      for c in trimmedFormattedAddress2[::-1]:
        if c == " ":
          numSpaces += 1
        if numSpaces < 2:
          strippedFormattedAddress += c

      strippedFormattedAddress = strippedFormattedAddress[::-1]
      
      if len(strippedFormattedAddress) > 3 and state in strippedFormattedAddress:
        wildfireInfo = trimmedTitle + " — " + strippedFormattedAddress
        nearbyWildfires.append(wildfireInfo)
        
  nearbyWildfires = sorted(nearbyWildfires, key = lambda x:x[-2])

  latLongRequest = requests.get("https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyD2ZWo9VogormcvsIxF3U8e0yCB84O0p8c&components=postal_code:94010")
  latLongData = latLongRequest.json()
  lat = latLongData["results"][0]["geometry"]["location"]["lat"]
  long = latLongData["results"][0]["geometry"]["location"]["lng"]

  aqiRequest = requests.get("http://api.openweathermap.org/data/2.5/air_pollution/forecast?lat=" + str(lat) + "&lon=" + str(long) + "&appid=cca337204f411e7b74e77b4aa7d29613")
  aqiData = aqiRequest.json()
  ozoneLevel = aqiData["list"][1]["components"]["o3"]
  ozoneLevelRelative = ""
  ozoneLevelColor = ""

  if ozoneLevel < 120:
    ozoneLevelRelative = "Good"
    ozoneLevelColor = "text-green"
  elif ozoneLevel < 180:
    ozoneLevelRelative = "Moderate"
    ozoneLevelColor = "text-orange"
  else:
    ozoneLevelRelative = "Poor"
    ozoneLevelColor = "text-red"

  pmLevel = aqiData["list"][1]["components"]["pm10"]
  pmLevelRelative = ""
  pmLevelColor = ""

  if pmLevel < 30:
    pmLevelRelative = "Good"
    pmLevelColor = "text-green"
  elif pmLevel < 55:
    pmLevelRelative = "Moderate"
    pmLevelColor = "text-orange"
  else:
    pmLevelRelative = "Poor"
    pmLevelColor = "text-red"

  weatherRequest = requests.get("https://api.openweathermap.org/data/2.5/weather?lat=50&lon=50&appid=cca337204f411e7b74e77b4aa7d29613")
  weatherData = weatherRequest.json()

  temp = weatherData["main"]["temp"] - 273.15
  humidity = weatherData["main"]["humidity"]
  wind = weatherData["wind"]["speed"]
  isRaining = weatherData["weather"][0]["main"]
  rain = 0
  if isRaining:
    rain = 0.2

  model = pickle.load(open('static/model.pkl','rb'))
  areaPrediction = model.predict([[temp, humidity, wind, rain]])
  predictedStatus = ""
  predictedStatusColor = ""

  if areaPrediction < 5:
    predictedStatus = "Low risk"
    predictedStatusColor = "text-green"
  elif areaPrediction < 20:
    predictedStatus = "Moderate risk"
    predictedStatusColor = "text-orange"
  else:
    predictedStatus = "High risk"
    predictedStatusColor = "text-red"

  return render_template("location.html", address=trimmedFormattedAddress, wildfires=nearbyWildfires, status=predictedStatus, statusColor=predictedStatusColor, ozone=ozoneLevelRelative, ozoneColor=ozoneLevelColor, pm=pmLevelRelative, pmColor=pmLevelColor)

@app.route("/emergency-kit")
def emergencyKit():
  return render_template("emergency-kit.html")

@app.route("/emergency-plan")
def emergencyPlan():
  return render_template("emergency-plan.html")

@app.route("/agriculture")
def agriculture():
  return render_template("agriculture.html")

@app.route("/child-safety")
def childSafety():
  return render_template("child-safety.html")

@app.route("/pet-safety")
def petSafety():
  return render_template("pet-safety.html")

@app.route("/prepare-for-evacuation")
def prepareForEvacuation():
  return render_template("prepare-for-evacuation.html")

@app.route("/evacuation")
def evacuation():
  return render_template("evacuation.html")

@app.route("/returning-home")
def returningHome():
  return render_template("returning-home.html")

if __name__ == "__main__":
	app.run(
		host='0.0.0.0',
		port=1000
	)