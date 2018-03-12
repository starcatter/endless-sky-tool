import typing
import re
import json
from py_expression_eval import Parser

# ----------------------------------------------------
setupPath = "./"
# ----------------------------------------------------

parser = Parser()

setupData : {} = {}
setupActions : {} = {}

inputPath = ""
outputPath = ""

outfitFileContents = {}

entityIndex = {}
entityIndex["Outfit"] = {}
entityIndex["Effect"] = {}

# ----------------------------------------------------

class Attribute:
	name :str
	values :[str]	
	attributes : {}
	linked : []

	def addLink(self, entity, count):
		self.linked.append((entity,count))

	def addAttr(self, attr:'Attribute'):
		if(attr.name not in self.attributes):
			self.attributes[attr.name] = [attr]
		else:
			self.attributes[attr.name].append(attr)

	def __init__(self, name:str, values:[str]):
		self.name = name.replace('"',"").replace("\n","")
		if(values != None): 
			self.values = [value.replace('"',"").replace('`',"") for value in values]
		else:
			self.values = None
		self.attributes = {}
		self.linked = []

class Effect(Attribute):
	def __init__(self, name:str):
		self.name = name.replace("\n","")
		self.values = None
		self.attributes = {}
		self.linked = []

class Outfit(Attribute):
	def __init__(self, name:str):
		self.name = name.replace("\n","")
		self.values = None
		self.attributes = {}
		self.linked = []
	
# ----------------------------------------------

def loadContents():
	print("Load Outfits:")
	for fileName in setupData["Files"]["Outfits"]:
		loadFile(fileName)
	
	print("Load Effects:")
	for fileName in setupData["Files"]["Effects"]:
		loadFile(fileName)

# ----------------------------------------------

def loadFile(fileName):
	print(fileName)

	outfitFileContents[fileName] = []
	with open(inputPath + fileName) as fileHandle:
		entry = None						# currently loaded outfit
		attributeStack :[Attribute] = []	# currently loaded attribute stack
		count : int = 0
		for line in fileHandle:
			line : str = line
			count += 1
			
			if line.startswith("outfit"):
				name :str= re.sub("^outfit\s+","", line)
				name = name.replace('"',"")

				entry :Outfit = Outfit(name)
				outfitFileContents[fileName].append(entry)
				entityIndex["Outfit"][entry.name] = entry
			elif line.startswith("effect"):
				name = re.sub("^effect\s+","", line)
				name = name.replace('"',"")

				entry :Effect = Effect(name)
				outfitFileContents[fileName].append(entry)
				entityIndex["Effect"][entry.name] = entry
			elif entry != None and line.startswith("\t") and not line.isspace():				
				match : typing.Match = re.match('^(\t+)(("[^"]+")|([\S]+))\s?(.*)?$',line)

				if match == None:
					print("Failed match:\n\t[["+line+"]]\n\t@"+str(count))
					continue

				index : int = len(match.group(1))
				attrName :str = match.group(2)
				attrValue :str = match.group(5)

				if attrName == "#":
					continue

				valueMatches = re.findall('(("[^"]+")|(`[^`]+`)|(\S+))', attrValue)
				values = [ match[0] for match in valueMatches ]
			
				attr = Attribute(attrName,values)

				if index == 1:	# outfit attribute
					entry.addAttr(attr)
					attributeStack :[Attribute] = [attr]
				elif index >= 2: # nested attribute	
					parent : Attribute = attributeStack[index-2]
					parent.addAttr(attr)

					if len(attributeStack) == index-1:
						attributeStack.append(attr)
					elif len(attributeStack) >= index:
						attributeStack[index-1] = attr
			elif line.startswith("#"):
				outfitFileContents[fileName].append(line)
			# process line
		# for line in fileHandle
	# open file
	

# ----------------------------------------------
def needsQuotes(input : str, isValue : bool) -> bool:
	if input == None : return False
	if input.isalpha(): return isValue
	if input.count(" ") > 0 : return True
	invChars = re.sub(r"[a-zA-Z0-9\-.,]","",input)
	return len(invChars) > 0

# ----------------------------------------------
def saveAttributes(attributes :{str,Attribute}, indentCnt : int, outFile : typing.TextIO):
	for name in attributes:
		name : str = name	
		
		indent : str = "\t"
		for i in range(1, indentCnt):
			indent += "\t"

		attrs : [Attribute] = attributes[name]
		for attr in attrs:
			if needsQuotes(attr.name, False): 
				outName = '"'+attr.name+'"' 
			else: 
				outName = attr.name

			outValues = ""
			for value in attr.values:
				if needsQuotes(value, True):
					outValues += ' "' + value+'"'
				else:
					outValues += ' ' + value

			print( indent + outName + outValues, file=outFile )

			if len(attr.attributes) > 0:
				saveAttributes(attr.attributes, indentCnt+1, outFile)

# ----------------------------------------------
def saveContents():
	print("Save:")
	for fileName in setupData["Files"]["Outfits"]:
		print(fileName)

		contents = outfitFileContents[fileName]

		with open(outputPath + fileName, "w") as fileHandle:
			for entry in contents:
				if isinstance(entry, Outfit):
					entry : Outfit = entry

					print( "outfit " + '"' + entry.name+ '"', file=fileHandle )
					saveAttributes(entry.attributes,1,fileHandle)

				elif isinstance(entry, Effect):
					entry : Effect = entry

					print( "effect " + '"' + entry.name+ '"', file=fileHandle )
					saveAttributes(entry.attributes,1,fileHandle)
				elif isinstance(entry, str):
					print( entry.replace("\n",""), end="", file=fileHandle )
			
				print( "", file=fileHandle )


# ----------------------------------------------------
def getKeyFromAttribute(key:str,attr:Attribute) -> [Attribute]:
	if( key.count("->") > 0 ):
		queryParts  : [str] = key.split("->",1)
		
		outerName : str = queryParts[0]
		innerName : str = queryParts[1]

		if outerName in attr.attributes:
			attrList : [Attribute] = attr.attributes[outerName]
			for candidate in attrList: # return the first attribute in the list that has the innerName attr we need
				result = getKeyFromAttribute(queryParts[1], candidate)
				if result != None: return result
						
		return None
	else:
		if key in attr.attributes:
			return attr.attributes[key]
		else:
			return None

# ----------------------------------------------		
def calculateValuesForOutfit(outfit : Outfit, stepCalculations:{} ) -> {str,float}:
	values : {str,float} = {}

	for value, process in stepCalculations.items():
		params : {str,float} = {}

		# get required params - skip outfit on fail
		for param, source in process["withRequired"].items():
			attrList = getKeyFromAttribute(source,outfit)
			if attrList != None:
				params[param] = float(attrList[0].values[0])
			else:
				return None

		# get optional data - default to zero on fail
		for param, source in process["with"].items():
			attrList = getKeyFromAttribute(source,outfit)
			if attrList != None:
				params[param] = float(attrList[0].values[0])
			else:
				params[param] = 0.0

		if len(outfit.linked) > 0:
			for link in outfit.linked:
				linkedEntity = link[0]
				if len(link) > 1:
					linkedCount = link[1]
				else:
					linkedCount = 1

				for param, source in process["withRequired"].items():
					attrList = getKeyFromAttribute(source,linkedEntity)
					if attrList != None:
						params[param] += float(attrList[0].values[0])*float(linkedCount)
				for param, source in process["with"].items():
					attrList = getKeyFromAttribute(source,linkedEntity)
					if attrList != None:
						params[param] += float(attrList[0].values[0])*float(linkedCount)

		values[value] = parser.parse(process["formula"]).evaluate(params)
				
	return values

# ----------------------------------------------
def filter_containsAny(attrValue:str,condData) -> bool:
	for value in condData:
		if attrValue.lower().count( value.lower() ) > 0: 
			return True
	return False

filters = {
	"containsAny": filter_containsAny 
	}

def checkCriteriaForOutfit(outfit:Outfit, criteria:{}) -> bool:
	for attrName,condition in criteria.items():
		if attrName == "_name":
			if isinstance(condition, str):
				if outfit.name != condition: return False
			else:
				for condType, condData in condition.items():
					if filters[condType](outfit.name,condData) == False: return False
		else:
			attrList : [Attribute] = getKeyFromAttribute(attrName,outfit)
			if attrList != None:
				for attr in attrList:
					if isinstance(condition, str):
						if attr.values[0] != condition: return False
					else:
						for condType, condData in condition.items():
							if filters[condType](attr.values[0],condData) == False: return False
			else:
				return False

	return True

# ----------------------------------------------
def execStep(setup : {}):
	stepName :str = setup["name"]
	stepCriteria : {str,str} = setup["criteria"]
	stepReference : [str] = setup["reference"]
	stepCalculations : {} = setup["calculate"]
	stepActions : {} = setup["set"]

	print("Execute step [["+stepName+"]]")

	reference : [Outfit] = []
	workSet : [Outfit] = []

	for index,outfit in entityIndex["Outfit"].items():
		if checkCriteriaForOutfit(outfit, stepCriteria):
			workSet.append(outfit)

	for refName in stepReference:
		if refName in entityIndex["Outfit"]:
			reference.append(entityIndex["Outfit"][refName])

	# ---
	print( "\t processing "+ str(len(workSet)) + " outfits")
	
	referenceValues = {}
	for outfit in reference:
		print( "\t reference item: "+ outfit.name)
		referenceValues[outfit.name] = calculateValuesForOutfit(outfit, stepCalculations)
		for key,value in referenceValues[outfit.name].items():
			print( "\t\t - "+ key +": "+str(value))

	print("")

	for outfit in workSet:
		
		print("\n\t [ "+outfit.name+" ]")
		values = calculateValuesForOutfit(outfit, stepCalculations)
		if values == None:
			print("\t |-> Skip outfit")
			continue

		for attributeName, process in stepActions.items():
			params : {str,float} = {}

			for param, source in process["with"].items():
				attrList = getKeyFromAttribute(source,outfit)
				if attrList != None:
					params[param] = float(attrList[0].values[0])
				else:
					params[param] = 0.0

			for valueName, value in values.items():
				params[valueName] = value

			#TODO: pick closest ref item
			for paramName, paramValue in referenceValues[ reference[0].name ].items():
				params["reference."+paramName] = paramValue

			floatValue : float = parser.parse(process["formula"]).evaluate(params)
			value = str.format("{:.1f}",floatValue);
			
			# ----------------------------------------------		
			# set the value
			# ----------------------------------------------		
			outfit.attributes[attributeName] = [Attribute(attributeName,[value])]
			print("\t |-> "+attributeName+": " + value)

# ----------------------------------------------			
def alterContents():
	for step in setupActions:
		execStep(step)


# ----------------------------------------------
def assembleContents():
	for entityType, connections in setupData["Structure"].items():
		print("Assembling: " + entityType)
		for link, targetType in connections.items():
			for name, entity in entityIndex[entityType].items():
				ref = getKeyFromAttribute(link, entity)
				if ref != None:										
					targetName = ref[0].values[0]
					if targetName in entityIndex[targetType]:
						target = entityIndex[targetType][targetName]
						if len(ref[0].values) > 1:
							count = ref[0].values[1]
						else:
							count = 1

						ref[0].addLink(target, count)
						entity.addLink(target, count)
					else:
						print("Cannot find [["+targetType+"]]:[["+targetName+"]], \n\trequired by [["+entityType+"]]:[[" + name + "]] @ " + link)



# ----------------------------------------------
def loadSetup():
	with open(setupPath + "balancer.json") as fileHandle:
		fileHandle : typing.TextIO = fileHandle
		setupFile = json.loads( fileHandle.read() )
		return (setupFile["Setup"],setupFile["Actions"])

# ----------------------------------------------

setupData,setupActions = loadSetup()

inputPath = setupData["Paths"]["Input"]
outputPath = setupData["Paths"]["Output"]

loadContents()
assembleContents()
alterContents()
saveContents()
