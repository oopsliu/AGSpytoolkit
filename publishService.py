#!/usr/bin/env python

#
# Batch publish mxd files under given directory as map services. 
# Created by Jiang Minbin 2016 & Liu Zheng 2017

import os,sys,time
import arcpy
from arcpy import mapping
import getpass
import shutil
import xml.dom.minidom as DOM
import tempfile
from datetime import *
import argparse

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
			arcpy.AddMessage( "++++++++INFO: server connection file created++++++++")
			return connection_file_path

		except Exception, msg:
			arcpy.AddMessage( msg)

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
		arcpy.AddMessage( "++++++++INFO: Validate MXD++++++++")
		file_to_be_published=[]
		for file in mxdLists:
			mxd=mapping.MapDocument(file)
			brknlist=mapping.ListBrokenDataSources(mxd)

			if not len(brknlist)==0:
				arcpy.AddMessage( "++++++++ERROR:Map Document,"+os.path.split(file)[1]+"is broken++++++++")
			else:
				file_to_be_published.append(file)

		arcpy.AddMessage( "++++++++INFO: Done validating mxd++++++")

		return file_to_be_published

	def publishServices(self,mxdLists,con,clusterName='default',copy_data_to_server=True,folder=None):
		for file in self.checkfileValidation(mxdLists):
			###tmp:
			serviceslist=[]
			serviceName=os.path.splitext(os.path.split(file)[1])[0]
			arcpy.AddMessage( "++++++++INFO: Service_"+serviceName +" Start to create SD++++++++")
			clsCreateSddraft=CreateSddraft()
			sddraft=clsCreateSddraft.CreateSddraft(file,con,serviceName,copy_data_to_server,folder)
			arcpy.AddMessage( "++++++++INFO: Start to analyse :"+serviceName+"++++++++")
			analysis = arcpy.mapping.AnalyzeForSD(sddraft)
			dirName=os.path.split(file)[0]

			if analysis['errors'] == {}:
			   arcpy.AddMessage( "++++++++WARNING:No error, but following warnings exist:+++++++")
			   arcpy.AddMessage( analysis['warnings'])
			   if(not self.checkWarnings(analysis['warnings'])):
				   try:
						sd=dirName+"\\"+serviceName+".sd"
						if(os.path.exists(sd)):
							os.remove(sd)
						arcpy.StageService_server(sddraft, sd)
						arcpy.AddMessage( "++++++++INFO:Service:"+ str(serviceName) +" Packed+++++++")
						arcpy.UploadServiceDefinition_server(sd, con,in_cluster=clusterName)
						arcpy.AddMessage( "++++++++INFO:Service:"+str(serviceName)+" Published++++++")
						os.remove(sd)

						####Stop service
				   except Exception,msg:
						arcpy.AddMessage( msg)
			   else:
				   arcpy.AddMessage( "++++++++WARNING:SUGGEST: END THIS AND REGISTER YOUR DATA SOURCE. Continue publishing in 6s +++")
				   # time.sleep(10)

				   try:
					sd=dirName+"\\"+serviceName+".sd"
					if(os.path.exists(sd)):
						os.remove(sd)
					arcpy.StageService_server(sddraft, sd)
					arcpy.AddMessage( "++++++++INFO: " + serviceName + " Packed++++++++")
					arcpy.UploadServiceDefinition_server(sd, con,in_cluster=clusterName)
					arcpy.AddMessage( "++++++++INFO: " + serviceName + " Published+++++++")
					os.remove(sd)
				   except Exception,msg:
					arcpy.AddMessage( msg)
			else:
				arcpy.AddMessage( '++++++++ERROR:Errors:'+analysis['errors']+'++++++++')
				#exit console in 5s
				time.sleep(5)
				sys.exit(1)

	def  checkWarnings(self,warnings):
		for warning in warnings:
			if warning[1]==24011:
				arcpy.AddMessage( "++++++++Data source is not registered. All data will be copied to server.+++++++")
				return True
		return False

	def GetMxFileList(self,filePath):
		#check folder exist
		arcpy.AddMessage( "++++++++INFO: mxd path:" + filePath + "+++++++")
		if not os.path.exists(filePath):
			arcpy.AddMessage( "++++++++ERROR: file not exist+++++++")
			sys.exit(1)
		#get all mxds
		list=[]
		for root,dirname, files in os.walk(filePath):
				 for file in files:
					if os.path.splitext(file)[1]=='.mxd':
						mxdfile=os.path.join(root,file)
						list.append(mxdfile)
		if list==[]:
		  arcpy.AddMessage( "++++++++INFO: no valic mxd file found++++++++")
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

	# create server connection file
	instace=CreateContectionFile()
	instace.filePath=contionfile
	instace.loginInfo=logDict
	instace.CreateContectionFile()

	if(os.path.isfile(contionfile)==False):
		arcpy.AddMessage( "++++++++ERROR: failed to create server connection file ++++++++")
		time.sleep(5)
		sys.exit(1)

	# enter mxd path
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

if __name__=='__main__':

	# input parameters
	serverip = arcpy.GetParameterAsText(0)
	userName = arcpy.GetParameterAsText(1)
	pswd = arcpy.GetParameterAsText(2)
	portNum = arcpy.GetParameterAsText(3)
	cluName = arcpy.GetParameterAsText(4)
	mxdFolder = arcpy.GetParameterAsText(5)
	
	logDict = {'server': arcpy.GetParameterAsText(0),
			   'userName': userName,
			   'passWord': pswd,
			   'port': portNum}

	myInstance = CreateContectionFile()
	myInstance.loginInfo = logDict
	path =os.path.join(tempfile.mkdtemp(),'server.ags')
	myInstance.filePath = path
	myInstance.CreateContectionFile()
	clsPublishservice=publishServices()
	file = mxdFolder
	fileList=clsPublishservice.GetMxFileList(file)
	clusterName = cluName
	servic_dir=''
	t_begin=datetime.now()
	
	# batch publish services
	clsPublishservice.publishServices(fileList,path,clusterName,copy_data_to_server=False,folder=servic_dir)

	t_end=datetime.now()
	time_passed=(t_end-t_begin).seconds
	arcpy.AddMessage( "Publishing time:" +str(time_passed) + "s")

