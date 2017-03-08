import arcpy
import os
import time
import sys
import getpass
import shutil

__author__ = ''

from arcpy import mapping

import xml.dom.minidom as DOM

import tempfile

from datetime import *

import argparse



def addFCData(fc):
	arcpy.AddMessage("--------ADD DATA BEGIN---------")
	prjFC = arcpy.SpatialReference(4326)
	insertCursor = None
	try:
		insertCursor = arcpy.da.InsertCursor(fc, ["SHAPE@"])

		polygon = arcpy.Polygon(arcpy.Array(
			[arcpy.Point(113.478115172, 23.1038225064), arcpy.Point(113.478115172, 23.001717531),
			 arcpy.Point(113.377547383, 23.001717531), arcpy.Point(113.377547383, 23.1038225064)]))

		insertCursor.insertRow([polygon])

		arcpy.AddMessage("--------ADD DATA SUCCESS---------")
	except Exception as e:
		arcpy.AddMessage("--------!ERROR WHILE ADD ROWS!---------")
		arcpy.AddMessage(e.message)
	finally:
		if insertCursor:
			del insertCursor
	arcpy.AddMessage("--------ADD DATA FINISH---------")


def removeFCData(fc):
	arcpy.AddMessage("--------DELETE DATA BEGIN---------")

	cursor = None

	try:

		with arcpy.da.UpdateCursor(fc, ["SHAPE@"]) as cursor:

			for row in cursor:
				cursor.deleteRow()

		arcpy.AddMessage("--------DELETE DATA SUCCESS---------")

	except Exception as e:

		arcpy.AddMessage("--------!ERROR WHILE DELETE ROWS!---------")

		arcpy.AddMessage(e.message)

	finally:

		if cursor:
			del cursor

	arcpy.AddMessage("--------DELETE DATA FINISH---------")


def makeMxd(conFile, mxd, df, fc, mxdpath):

	fieldNames = [f.name for f in arcpy.ListFields(fc)]

	arcpy.AddMessage("---------FIELD NAMES------------")

	arcpy.AddMessage(fieldNames)

	fcsql = "SELECT * FROM SDE.huaweitestpolygon"

	addFCData(fc)

	result = arcpy.MakeQueryLayer_management(conFile, "querylayer", fcsql, "OBJECTID", "POLYGON", "4326")

	addLayer = result.getOutput(0)

	addLayer.showLabel = True

	for myLabel in addLayer.labelClasses:
		myLabel.showClassLabels = True

		myLabel.expression = '[OBJECTID]'

	arcpy.mapping.AddLayer(df, addLayer, "BOTTOM")

	removeFCData(fc)

	result2 = arcpy.MakeFeatureLayer_management(fc, "newfeaturelayer")

	addLayer2 = result2.getOutput(0)

	arcpy.mapping.AddLayer(df, addLayer2, "BOTTOM")

	newMxd = mxdpath + r"\new\new.mxd"

	print "newMxd" + newMxd

	mxd.saveACopy(newMxd)

	arcpy.AddMessage("------------MAKE MXD FINISH---------")

	del mxd
	


class CreateSddraft:

	def CreateSddraft(self,mapDocPath,con,serviceName,copy_data_to_server=True,folder=None):

		"""
		:param mapDocPath: mxd path
		:param con: arcgis server connection file
		:param serviceName: service name
		:param clusterName: cluster name
		:param folder: folder to contain the publishing service
		:return: the file path of the sddraft

		"""
		mapDoc=mapping.MapDocument(mapDocPath)
		sddraft=mapDocPath.replace(".mxd",".sddraft")
		result= mapping.CreateMapSDDraft(mapDoc, sddraft, serviceName, 'ARCGIS_SERVER', con, copy_data_to_server, folder)

		return sddraft

	def setTheClusterName(self,xml,clusterName):# the new description

		doc = DOM.parse(xml)

		# find the Item Information Description element
		doc.getElementsByTagName('Cluster')[0].childNodes[0].nodeValue=clusterName
		# output to a new sddraft
		outXml =xml
		f = open(outXml, 'w')
		doc.writexml( f )
		f.close()

		return  outXml





class CreateContectionFile(object):

	def __init__(self):
		self.__filePath = None
		self.__loginDict = None

	def CreateContectionFile(self):

		"""
		wrkspc: store the ags file

		loginDict: dictionary stored login information

		"""

		# con = 'http://localhost:6080/arcgis/admin'

		try:
			server_url = "http://{}:{}/arcgis/admin".format(self.__loginDict['server'],self.__loginDict['port'])
			connection_file_path = str(self.__filePath)			#
			use_arcgis_desktop_staging_folder = False

			if os.path.exists(connection_file_path):
				os.remove(connection_file_path)
			out_name = os.path.basename(connection_file_path)

			path = os.path.split(self.filePath)[0]
			result = mapping.CreateGISServerConnectionFile("ADMINISTER_GIS_SERVICES",
														   path,
														  out_name,
														   server_url,
														   "ARCGIS_SERVER",
														   use_arcgis_desktop_staging_folder,
														   path,
														   self.__loginDict['userName'],
														   self.__loginDict['passWord'],
														   "SAVE_USERNAME"
														   )
			print "++++++++INFO: server connection file created++++++++"
			return connection_file_path

		except Exception, msg:
			print msg



	#

	@property
	def filePath(self):
		return self.__filePath

	@filePath.setter
	def filePath(self, value):
		self.__filePath = value

	@property
	def loginInfo(self):
		return self.__loginDict

	@loginInfo.setter
	def loginInfo(self, value):
		self.__loginDict = value

class publishServices:

	def checkfileValidation(self,mxdLists):
		print "++++++++INFO:Velidate MXD++++++++"
		file_to_be_published=[]
		for file in mxdLists:
			mxd=mapping.MapDocument(file)
			brknlist=mapping.ListBrokenDataSources(mxd)

			if not len(brknlist)==0:
				print "++++++++ERROR:Map Document,"+os.path.split(file)[1]+"is broken++++++++"
			else:
				file_to_be_published.append(file)

		print "++++++++INFO: Done validating mxd++++++"

		return file_to_be_published

	def publishServices(self,mxdLists,con,clusterName='default',copy_data_to_server=True,folder=None):
		for file in self.checkfileValidation(mxdLists):
			###tmp:
			serviceslist=[]
			serviceName=os.path.splitext(os.path.split(file)[1])[0]
			print "++++++++INFO:Service_"+serviceName+"Start to create SD++++++++"
			clsCreateSddraft=CreateSddraft()
			sddraft=clsCreateSddraft.CreateSddraft(file,con,serviceName,copy_data_to_server,folder)
			print "++++++++INFO: Start to analyse :"+serviceName+"++++++++"
			analysis = arcpy.mapping.AnalyzeForSD(sddraft)
			dirName=os.path.split(file)[0]

			if analysis['errors'] == {}:
			   print "++++++++WARNING:No error, but following warnings exist:+++++++"
			   print analysis['warnings']
			   if(not self.checkWarnings(analysis['warnings'])):
				   try:
						sd=dirName+"\\"+serviceName+".sd"
						if(os.path.exists(sd)):
							os.remove(sd)
						arcpy.StageService_server(sddraft, sd)
						print "++++++++INFO:Service:"+serviceName+"Packed+++++++"
						arcpy.UploadServiceDefinition_server(sd, con,in_cluster=clusterName)
						print "++++++++INFO:Service:"+str(serviceName)+"Published++++++"
						os.remove(sd)

						####Stop service
				   except Exception,msg:
						print msg
			   else:
				   print "++++++++WARNING:SUGGEST: END THIS AND REGISTER YOUR DATA SOURCE. Continue publishing in 6s +++"
				   # time.sleep(10)

				   try:
					sd=dirName+"\\"+serviceName+".sd"
					if(os.path.exists(sd)):
						os.remove(sd)
					arcpy.StageService_server(sddraft, sd)
					print "++++++++INFO:Packed++++++++"
					arcpy.UploadServiceDefinition_server(sd, con,in_cluster=clusterName)
					print "++++++++INFO:"+serviceName+"Published+++++++"
					os.remove(sd)
				   except Exception,msg:
					print msg
			else:
				print '++++++++ERROR:Errors:'+analysis['errors']+'++++++++'
				#exit console in 5s
				time.sleep(5)
				sys.exit(1)

	def  checkWarnings(self,warnings):
		for warning in warnings:
			if warning[1]==24011:
				print "++++++++Data source is not registered. All data will be copied to server.+++++++"
				return True
		return False

	def GetMxFileList(self,filePath):
		#check folder exist
		print "mxd path: " + filePath
		if not os.path.exists(filePath):
			print "++++++++ERROR: file not exist+++++++"
			sys.exit(1)
		#get all mxds
		list=[]
		for root,dirname, files in os.walk(filePath):
				 for file in files:
					if os.path.splitext(file)[1]=='.mxd':
						mxdfile=os.path.join(root,file)
						list.append(mxdfile)
		if list==[]:
		  print "++++++++INFO: no valic mxd file found++++++++"
		  time.sleep(5)
		  sys.exit(1)
		return list

def GetInfo():
	server = raw_input("GIS Server IP:")
	userName=raw_input("Site administrator:")
	passWord=getpass.getpass("Password:")
	port=raw_input("Port(6080):")

	logDict={'server':server,
			'userName':userName,
			'passWord':passWord,
			'port':port}



	contionfile=os.path.join(tempfile.mkdtemp(),'server.ags')

	#create server connection file

	instace=CreateContectionFile()
	instace.filePath=contionfile
	instace.loginInfo=logDict
	instace.CreateContectionFile()

	if(os.path.isfile(contionfile)==False):
		print "++++++++ERROR: failed to create server connection file ++++++++"
		time.sleep(5)
		sys.exit(1)

	#enter mxd path
	mxdDir=raw_input('enter folder path of mxd:')
	clsPublishservice=publishServices()
	fileList=clsPublishservice.GetMxFileList(mxdDir)

	servic_dir=raw_input("Server directory(default:root)")
	if len(servic_dir)==0:
		servic_dir==None
	clusterName=raw_input("Cluster:")

	if len(clusterName)==0:
		clusterName='default'

	clsPublishservice=publishServices()

	clsPublishservice.publishServices(fileList,contionfile,clusterName,copy_data_to_server=False,folder=servic_dir)


if __name__ == "__main__":
	mxdpath = arcpy.GetParameterAsText(0)

	mxd = arcpy.mapping.MapDocument(mxdpath + r"\test.mxd")

	df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]


	conFile = arcpy.GetParameterAsText(1)

	fc = conFile + r"\SDE.huaweitestpolygon"

	print "featureclass" + fc

	makeMxd(conFile,mxd, df, fc,mxdpath)
	
	
   # GetInfo()
	logDict = {'server': '192.168.220.167',
			   'userName': "siteadmin",
			   'passWord': "siteadmin",
			   'port':'6080'}

	dd = CreateContectionFile()
	dd.loginInfo = logDict
	path =os.path.join(tempfile.mkdtemp(),'server.ags')

	print path

	dd.filePath = path
	dd.CreateContectionFile()
	clsPublishservice=publishServices()

	#get

	file=r"C:\huaweitest\mxds\new"

	fileList=clsPublishservice.GetMxFileList(file)

	clusterName='default'

	servic_dir=''
	t_begin=datetime.now()
	clsPublishservice.publishServices(fileList,path,clusterName,copy_data_to_server=False,folder=servic_dir)

	t_end=datetime.now()

	time_passed=(t_end-t_begin).seconds

	arcpy.AddMessage("Publishing time:")
	arcpy.AddMessage(str(time_passed))