import csv
import copy

listTagProviders = ['Utah01']

# Handles tag property values that may include binding syntax. 
# If the value contains {, it returns a dictionary indicating a parameter binding; 
# otherwise, it returns the raw value directly.
def getTagPropValue(rawValue):
	if '{' in rawValue:
		return {"bindType": "parameter", "binding": rawValue}
	else:
		return rawValue

# Imports UDT (User Defined Type) definitions from a CSV file into Ignition. 
# It builds UDT structures with tags and parameters, optionally supports custom parameters from a second CSV, 
# and configures them in the tag provider using system.tag.configure.
def importUDTDefinitionCSV():
	system.gui.messageBox('Select UDT Definition CSV to Import', 'UDT Definition Tags')
	#csvFilePath = r"C:\Users\trent.boudreaux\The Integration Group of Americas\262, Magnolia Oil & Gas - 20-001, MGY SCADA Transition\Working\Ignition\UDTs\UDT_Definitions_Modbus_ProPack.csv"
	

	
	#starting point for new udt definitions
	baseUDT = 	{
					"tagType": "UdtType",
					"parameters": {
						"Server": {
							"dataType": "String"
							},
						"Channel01": {
							"dataType": "String"
							},
						"History Provider": {
							"dataType": "String"
							},
						"Device01": {
							"dataType": "String"
							},
						"AppConfig": {
							"dateType": "String"
							}
						}
				}
						
	#starting point for new tags
	baseTag = 	{
					"enabled": True,
					"tagType": "AtomicTag"
				}
	
	dictUDTDefs = {} #key = udt definition name, value = udt definition
	
	#list of columns to add to tags
	listTagPropNames = ['name', 'engUnit', 'dataType', 'valueSource', 'opcServer', 'opcItemPath', 'historyEnabled', 'historyProvider', 'scaleMode', 'rawHigh', 'scaledHigh']
	
	csvFilePath = system.file.openFile()
	with open(csvFilePath) as csvfile: #open csv file
		reader = csv.DictReader(csvfile) #read each row into a dictionary key: column header, value: cell value
		for row in reader: #loop through CSV rows
			udtDefName = row['UDT Definition'] #get the udt definition name, with folder from column "UDT Definition" in csv
			udtDef = dictUDTDefs.get(udtDefName, copy.deepcopy(baseUDT)) #get UDT definiton, created in previous row iterations, or create a new base copy to start
			udtDef['name'] = udtDefName.split('/')[-1] #assign name in case its new, strip folder
			tags = udtDef.get('tags',[]) #get list of tags from udt definition, or start with empty list
			newTag = baseTag.copy() #create a new tag from base
			for key, value in row.items(): #loop through the items in the row dictionary
				if key in listTagPropNames: #check if tag property is one we want to import. list defined above
					if getTagPropValue(value) != '':
						newTag[key] = getTagPropValue(value) #add property to tag dictionary with csv value 
			tags.append(newTag) #add new tag to list of tags
			udtDef['tags'] = tags #update list of tags in udt definition object
			dictUDTDefs[udtDefName] = udtDef #update udt definition in dictionary of all udt definitions
	
	if system.gui.confirm('Custom UDT Definition Parameters?'):
		csvParamsFilePath = system.file.openFile()
		with open(csvParamsFilePath) as csvParamsFile: #open UDT parameter csv file
			reader = csv.DictReader(csvParamsFile) #read each row into a dictionary key: column header, value: cell value
			for row in reader: #loop through CSV rows
				udtDefName = row['UDT Definition'] #get the udt definition name, with folder from column "UDT Definition" in csv
				udtDef = dictUDTDefs.get(udtDefName, copy.deepcopy(baseUDT)) #get UDT definiton, created in previous row iterations, or create a new base copy to start
				print system.util.jsonEncode(udtDef)
				parameters = udtDef.get('parameters',{}) #get list of parameters from udt definition, or start with empty list
				print udtDefName, system.util.jsonEncode(parameters)		
				parameters[row['parameter']] = {'dataType': row['dataType']}
				print udtDefName, system.util.jsonEncode(parameters)								
				udtDef['parameters'] = parameters #update list of tags in udt definition object
				dictUDTDefs[udtDefName] = udtDef #update udt definition in dictionary of all udt definitions
	
	#print dictUDTDefs.values()
	for udtDefName, udtDef in dictUDTDefs.items(): #loop through all udt definitions
		for tagProvider in listTagProviders:
			fullUdtDefName = '[%s]_types_/%s' % (tagProvider,udtDefName)
			folder = '/'.join(fullUdtDefName.split('/')[:-1]) #parse out folder path from full UDT definition name
			name = fullUdtDefName.split('/')[-1] #parse out udt definition name from full udt definition name
			print 'Importing UDT Definition "%s"' % fullUdtDefName 
			#print folder
			#print system.util.jsonEncode(udtDef)
			results = system.tag.configure(folder, udtDef, 'o') #perform tag configuration import, override any conflicts/existing udt def
			#print results
		
	print 'done'
		
# Imports UDT instances from a CSV file, creating tag configurations based on definitions and parameters. 
# Optionally applies tag-level overrides from a second CSV and writes the instances to the tag provider.
def importUDTInstanceCSV():
	system.gui.messageBox('Select UDT Instances CSV to Import', 'UDT Instance Tags')
	
	baseUDT = {'tagType': 'UdtInstance'} #initialize a new udt instance
	
	dictUDTInstances = {} #key = udt instance name, value = udt instance 
	
	csvFilePath = system.file.openFile()
	with open(csvFilePath) as csvfile: #open csv file
		reader = csv.DictReader(csvfile) #read each row into a dictionary key: column header, value: cell value
		for row in reader: #loop through CSV rows
			fullTagPath = row['FullTagPath'] #get the full tag path from csv row
			udtInstance = dictUDTInstances.get(fullTagPath, copy.deepcopy(baseUDT)) #get UDT definiton, created in previous row iterations, or create a new base copy to start
			udtInstance['typeId'] = row['UDT Definition']
			udtInstance['name'] = fullTagPath.split('/')[-1] #parse out udt definition name from full udt definition name
			parameters = {} #initialize a list of udt parameters
			for key, value in row.items(): #loop through the items in the row dictionary
				if key[:6] == 'Param:':
					#print key[6:], value
					if value != '':
						parameters[key[6:]] = value
			udtInstance['parameters'] = parameters
			dictUDTInstances[fullTagPath] = udtInstance
			
	if system.gui.confirm('UDT Instance Overrides?'):
		csvOvrdFilePath = system.file.openFile()
		with open(csvOvrdFilePath) as csvOvrdFile: #open UDT instance override csv file
			reader = csv.DictReader(csvOvrdFile) #read each row into a dictionary key: column header, value: cell value
			for row in reader: #loop through CSV rows
				print row
				fullTagPath = row['FullTagPath'] #get the full tag path from csv row
				udtInstance = dictUDTInstances.get(fullTagPath, copy.deepcopy(baseUDT)) #get UDT definiton, created in previous row iterations, or create a new base copy to start
				#print udtInstance
				tags = udtInstance.get('tags',[])
				tagName = row['TagName']
				tag = {'name': tagName}
				tag[row['Property']] = getTagPropValue(row['Value'])
				tags.append(tag)
				udtInstance['tags'] = tags
				#print udtInstance
				dictUDTInstances[fullTagPath] = udtInstance
				
	#print dictUDTDefs.values()
	for fullTagPath, udtInstance in dictUDTInstances.items(): #loop through all udt definitions
		for tagProvider in listTagProviders:
			folder = '/'.join(fullTagPath.split('/')[:-1]) #parse out folder path from full tag path
			#name = fullTagPath.split('/')[-1] #parse out udt tag name from full tag path
			results = system.tag.configure(folder, udtInstance)
			print 'Importing UDT Instance "%s"' % fullTagPath, results  #perform tag configuration import, override any conflicts/existing udt def
		    
	print 'done'
	
# Exports the structure of specified UDT definitions to a CSV file. 
# It extracts tag properties from each UDT and writes them in a structured format, including handling bound values.
def exportUDTDefinitionCSV(listUdtDefTagPath):
#TIGA.tag.exportUDTDefinitionCSV(["[North01]_types_/TANK/EMERSON107/EMERSON107 TANK v01"])
	from com.inductiveautomation.ignition.common.config import BoundValue

	filePath = system.file.saveFile('UDT_Definition_Export.csv')
	
	listPropNames = ['UDT Definition', 'name','units','dataType','valueSource','opcServer','opcItemPath','scaleMode','rawHigh','scaledHigh']
	
	system.file.writeFile(filePath, ','.join(listPropNames) + '\n', False)
	print(listUdtDefTagPath)
	for udtDefTagPath in listUdtDefTagPath:
		udt = system.tag.getConfiguration(udtDefTagPath, True)[0]

		for tag in udt['tags']:
			props = [udtDefTagPath]
			for propName in listPropNames:
				prop = tag.get(propName,'')
				if type(prop) == BoundValue:
					prop = prop.getBinding()
				props.append(str(prop))
			props = ','.join(props) + '\n'
			system.file.writeFile(filePath, props, True)
	
# Deletes UDT instances listed in a selected CSV file. 
# It reads tag paths from the file and removes them using system.tag.deleteTags.
def deleteUDTInstanceCSV():
	system.gui.messageBox('Select UDT Instances CSV to Delete', 'UDT Instance Tags')

	listTagPaths = [] #list of tag paths to delete
	
	csvFilePath = system.file.openFile()
	with open(csvFilePath) as csvfile: #open csv file
		reader = csv.DictReader(csvfile) #read each row into a dictionary key: column header, value: cell value
		for row in reader: #loop through CSV rows
			fullTagPath = row['FullTagPath'] #get the full tag path from csv row
			listTagPaths.append(fullTagPath)
	
	#print listTagPaths
	results = system.tag.deleteTags(listTagPaths)
	for i, tagPath in enumerate(listTagPaths):
		print tagPath, 'Delete', results[1]
		
	print 'done'
	
# Imports alarm configurations from a CSV file and applies them to tags in Ignition. 
# It translates Cygnet alarm definitions into Ignition alarm properties, including pipelines, priorities, and setpoints, and configures alarms using system.tag.editAlarmConfig.
def importAlarmConfigurationCSV():
	gActivePipeline = 'Standard'
	gClearPipeline = gActivePipeline
	
	#dictionary with definition of translating cygnet alarms to ignition alarms
	alarmTranslation = {
		'AI': {
			2:{
				'name': 'Low Alarm',
				'mode': 3},
			3:{
				'name': 'Low Warning',
				'mode': 3},
			4:{
				'name': 'High Warning',
				'mode': 2},
			5:{
				'name': 'High Alarm',
				'mode': 2}
			},
		'EI': { #need wildcard support
			1:{
				'name': 'Alarm', #Enumeration Alarm 1
				'mode': 0},
			6:{
				'name': 'Alarm 2', #Enumeration Alarm 6
				'mode': 0}
			},
		'DI': { #applies when off?
			4:{
				'name': 'Alarm',
				'mode': 0} 
			},
		'SI': { #need wildcard support
			1:{
				'name': 'Alarm', #String Alarm 1 - no points use both cfg bit 1 & 2
				'mode': 0},
			2:{
				'name': 'Alarm', #String Alarm 2
				'mode': 0},
			8:{
				'name': 'Alarm 2', #String Alarm 8
				'mode': 0}
			}
		}
		
	remotePipelines = {
		'Global': None,
		'Highlander': None,
		'North01': None,
		'South01': None,
		'System': None
		}
	
	def getPriority(alarmpriority):
		alarmpriority = int(alarmpriority)
		#if alarmpriority == 0: 
			#return 0 #diagnostic
		if alarmpriority >= 0 and alarmpriority < 25: 
			return 1 #low
		elif alarmpriority >= 25 and alarmpriority < 50:
			return 2 #Medium
		elif alarmpriority >= 50 and alarmpriority < 75:
			return 3 #High
		elif alarmpriority >= 75:
			return 4 #Critical
		return None
		
	def getAlarmProps(pointdatatype, mode, remotePipeline):
		alarmProps = {}
		alarmProps['enabled'] = 1 #temporarily hardcoded as disabled for testing
		alarmProps['mode'] = mode #passed in
		alarmProps['setpointA'] = cfgbitcalcparm1[cfgbit-1]
		reportcas = cfgbitreportcas[cfgbit-1]
		reportgns = cfgbitreportgns[cfgbit-1]
		if reportcas == '1' or reportgns == '1': #if either report to cas or gns, configure delay
			activedelay = cfgbitrptdelay[cfgbit-1]
			if activedelay != '0': 
				alarmProps['timeOnDelaySeconds'] = activedelay
	#			print tagPath, 'active delay of', activedelay
		if reportgns == '1':
			activePipeline = gActivePipeline
			clearPipeline = gClearPipeline
			if remotePipeline: #check if pipeline is on remote gateway
				activePipeline = remotePipeline + '/' + activePipeline
				clearPipeline = remotePipeline + '/' + clearPipeline
			alarmProps['activePipeline'] = activePipeline #Standard Alarm Pipeline
			alarmProps['clearPipeline'] = clearPipeline #Standard Alarm Pipeline
		if cfgbitgnsid[cfgbit-1] != '':
			alarmProps['Roster Notify'] = cfgbitgnsid[cfgbit-1] #ignition roster matches cygnet gns event id
		alarmProps['priority'] = getPriority(alarmpriority[cfgbit-1]) #use method to convert cygnet alarmpriority to ignition priority
		
		if pointdatatype == 'DI':
			setpointA = alarmProps['setpointA']
			if setpointA.lower() == 'n': #applies when off?
				setpointA = 1
			elif setpointA.lower() == 'y': #applies when off?
				setpointA = 0
			else:
				print 'unsupported digital setpoint', setpointA
			alarmProps['setpointA'] = setpointA #save back to alarm prop dictionary
		
		listAlarmProps = [[name, 'Value', value] for name, value in alarmProps.iteritems()]		
		return listAlarmProps
	
	#text = system.file.readFileAsString(path,'UTF-8')
	#rows = text.splitlines()
	
	#headers = rows[0].split(',')
	
	csvFilePath = system.file.openFile()
	with open(csvFilePath) as csvfile: #open csv file
		reader = csv.DictReader(csvfile) #read each row into a dictionary key: column header, value: cell value
		for row in reader: #loop through CSV rows
	
		#for idx,row in enumerate(rows[1:]):
			alarmConfig = {} #init empty alarm edit config
			#row = row.split(',')
			tagPath = row['ignitiontagpath']
			pointdatatype = row['pointdatatype']
			tagProvider = None #initialize
			if tagPath[:1] == '[' and ']' in tagPath: #check if tag path appears to contain tag provider
				tagProvider = tagPath[1:tagPath.find(']')] #get tag provider from tag path
			remotePipeline = remotePipelines.get(tagProvider, None)
		#	print tagPath, pointdatatype, tagProvider
			
			#build cfgbit lists with values
			cfgbitenabled = []
			cfgbitcalcparm1 = []
			cfgbitcalcparm2 = []
			cfgbitreportcas = []
			cfgbitreportgns = []
			cfgbitgnsid = []
			cfgbitrptdelay = []
			alarmpriority = []
			for cfgbit in range(1,16): #cygnet has cfgbit 1-16
				cfgbitenabled.append(row['cfgbit%02denabled' % cfgbit])
				cfgbitcalcparm1.append(row['cfgbit%02dcalcparm1' % cfgbit])
				cfgbitcalcparm2.append(row['cfgbit%02dcalcparm2' % cfgbit])
				cfgbitreportcas.append(row['cfgbit%02dreportcas' % cfgbit])
				cfgbitreportgns.append(row['cfgbit%02dreportgns' % cfgbit])
				cfgbitgnsid.append(row['cfgbit%02dgnsid' % cfgbit])
				cfgbitrptdelay.append(row['cfgbit%02drptdelay' % cfgbit])
				alarmpriority.append(row['alarm%02dpriority' % cfgbit])
				
			if pointdatatype in alarmTranslation: #if cygnet point type is in alarm translation dictionary
				for cfgbit in range(1,16): #loop through all cygnet alarms
					if cfgbitenabled[cfgbit-1] == '1': #if config bit it enabled
						typeDict = alarmTranslation[pointdatatype] #get the dictionary of configuration bits for this point type
						if cfgbit in typeDict: #if the enabled configuration bit is in the translation dictionary for this point type
							cfgbitDict = typeDict[cfgbit]  #get the dictionary of properties for this cfg bit for this type
							#print pointdatatype, cfgbit, cfgbitDict
							alarmName = cfgbitDict['name'] #get alarm name from cfgbit property dictionary 
							mode = cfgbitDict['mode'] #get mode from cfgbit property dictionary 
							alarmConfig[alarmName] = getAlarmProps(pointdatatype, mode, remotePipeline)
						else:
							print 'Missing support for enabled alarm for pointdatatype', pointdatatype, 'cfgbit', cfgbit
			else:
				print 'Missing support for pointdatatype', pointdatatype, tagPath
		
					
			if alarmConfig != {}:
				if tagPath == '':
					print 'ERROR: missing ignition tag path for enabled alarms for cygnet point', row[headers.index('tagfull')]
				else:
					try:
		#				pass
						print tagPath, alarmConfig
						system.tag.editAlarmConfig([tagPath], alarmConfig)
						#return
					except:
						print 'ERROR:', tagPath, alarmConfig
#				
	print 'done'

# Exports tag properties for specified tag paths to a CSV file. 
# Supports recursive traversal of nested tags and handles bound values, writing selected properties for each tag.
def exportTagPropertiesCSV(listTagPath, listPropNames=None, bRecursive=True):
	from com.inductiveautomation.ignition.common.config import BoundValue
	
	if not listPropNames:
			listPropNames = ['tagPath','name','units','dataType','valueSource','opcServer','opcItemPath','scaleMode','rawHigh','scaledHigh']

	filePath = system.file.saveFile('Tag_Properties_Export.csv')
	system.file.writeFile(filePath, ','.join(listPropNames) + '\n', False)
	
	def recursiveExport(filePath, listTagConfig, basePath=''):
		for tag in listTagConfig:
			if basePath == '': #check if currPath is empty string, indicating first iteration
				fullTagPath = str(tag['path'])  #initialize new current path as source path
				tagName = str(tag['name'])
			else: #not first iteration, update newCurrPath as normal
				fullTagPath = basePath + '/' + str(tag['path']) #add new tag(or folder) name to current path for new current path
				tagName = str(tag['path'])
			
			props = [fullTagPath]
			for propName in listPropNames:
				prop = tag.get(propName,'')
				if type(prop) == BoundValue:
					prop = prop.getBinding()
				props.append(str(prop))
			props = ','.join(props) + '\n'
			
			system.file.writeFile(filePath, props, True)
			
			#recursion for nested tags
			if 'tags' in tag and bRecursive:
				recursiveExport(filePath, tag['tags'], fullTagPath)
	
	for basePath in listTagPath:
		listTagConfig = system.tag.getConfiguration(basePath, True)
		recursiveExport(filePath, listTagConfig)
		
	print 'done'
	
# Updates specific DCP point tags based on a CSV file. 
# It checks if the tag exists and is OPC-based, then enables the tag and sets its value source to memory if applicable.
def UpdateDCPPoints():
	if system.gui.confirm('File for Updates to DCP points'):
		csvOvrdFilePath = system.file.openFile()
		with open(csvOvrdFilePath) as csvOvrdFile: #open UDT instance override csv file
			reader = csv.DictReader(csvOvrdFile) #read each row into a dictionary key: column header, value: cell value
			for row in reader: #loop through CSV rows
				#print row
				fullTagPath = row['FullTagPath'] #get the full tag path from csv row

				pointList = ['Static Pressure', 'Differential Pressure', 'Temperature', 'Volume Today', 'Volume Yesterday', 'Energy Yesterday', 'Flow Time Yesterday']
				#Enable the point
				#Make it a memory tag
				values = [True, 'memory']
				for item in pointList:
					tagList = [fullTagPath + '/' + item + '.enabled', fullTagPath + '/' + item + '.valueSource']
					#valSourceType = [fullTagPath + '/' + item + '.valueSource']
					valSourceType = [fullTagPath + '/' + item]
					output =  system.tag.readBlocking(valSourceType)
					#if output[0].value == 0 : 
					if str(output[0].quality) <> "Bad_NotFound":
						valSourceType = [fullTagPath + '/' + item + '.valueSource']
						output =  system.tag.readBlocking(valSourceType)
						if "opc" in output[0].value:
							print fullTagPath + '/' + item
								#system.tag.writeBlocking(tagList, values)
