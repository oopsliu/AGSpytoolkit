# Demonstrates how to stop or start all services in a folder

# For Http calls
import httplib, urllib, json
# For system tools
import sys
# For reading passwords without echoing
import getpass
import arcpy

# Defines the entry point into the script
def deleteService(username,password,serverName,serverPort,folder,servicename):
    # Print some info
    print
    print "This tool is a  script that delete a service service in a folder."
    print

    # Get a token
    token = getToken(username, password, serverName, serverPort)
    if token == "":
        print "Could not generate a token with the username and password provided."
        return
    else:
        print "token = " + token

    # Construct URL to read folder
    if str.upper(folder) == "ROOT":
        folder = ""
    else:
        folder += "/"

    folderURL = "/arcgis/admin/services/" + folder

    # This request only needs the token and the response formatting parameter
    params = urllib.urlencode({'token': token, 'f': 'json'})

    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    # Connect to URL and post parameters
    httpConn = httplib.HTTPConnection(serverName, serverPort)

    servicename += ".MapServer"

    deleteURL = folderURL + servicename + "/delete"

    print "deleteURL = " + deleteURL

    httpConn.request("POST", deleteURL, params, headers)

    # Read response
    deleteResponse = httpConn.getresponse()
    if (deleteResponse.status != 200):
        httpConn.close()
        print "Error while executing delete. Please check the URL and try again."
        return
    else:
        deleteData = deleteResponse.read()

        if not assertJsonSuccess(deleteData):
            print "Error returned when delete service " + serverName + "."
            print str(deleteData)
        else:
            print "Service " + serverName + " delete successfully."

    httpConn.close()
    return

# A function to generate a token given username, password and the adminURL.
def getToken(username, password, serverName, serverPort):
    # Token URL is typically http://server[:port]/arcgis/admin/generateToken
    tokenURL = "/arcgis/admin/generateToken"

    params = urllib.urlencode({'username': username, 'password': password, 'client': 'requestip', 'f': 'json'})

    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    # Connect to URL and post parameters
    httpConn = httplib.HTTPConnection(serverName, serverPort)
    httpConn.request("POST", tokenURL, params, headers)

    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "Error while fetching tokens from admin URL. Please check the URL and try again."
        return
    else:
        data = response.read()
        httpConn.close()

        # Check that data returned is not an error object
        if not assertJsonSuccess(data):
            return

        # Extract the token from it
        token = json.loads(data)
        return token['token']
        # A function that checks that the input JSON object

#  is not an error object.
def assertJsonSuccess(data):
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        print "Error: JSON object returns an error. " + str(obj)
        return False
    else:
        return True


# Script start
if __name__ == "__main__":
    deleteService("siteadmin","siteadmin","192.168.220.167","6080","root","new")

