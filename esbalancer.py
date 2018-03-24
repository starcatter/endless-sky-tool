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

# ----------------------------------------------------

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def quoteName(string : str) -> str:
	if string is None:
		return ''
	elif string.count('"') > 0:
		return '`' + string + '`'
	elif string.count(' ') > 0:
		return '"' + string + '"'
	return string
	
def quoteValue(string : str) -> str:
	if string is None:
		return ''
	elif not isinstance(string,str):
		return str(string)
	elif string.count('"') > 0:
		return '`' + string + '`'
	elif string.isalpha() or string.count(' ') > 0:
		return '"' + string + '"'
	return string
	
# ----------------------------------------------

class Attribute:

	def __init__(self, name:str, values:[str]):
		self.name = name.replace("\n","")

		if(values != None): 
			self.values = [value for value in values]
		else:
			self.values = None

		self.attributes = {}	# sub-attrs
		self.linked = []		# entities linked to this attr (root)

	# ---
	# Handle linked entities
	# ---

	def addLink(self, entity, count):
		self.linked.append((entity,count))

	# ---
	# Handle sub-attributes
	# ---
	def getAttachedValue(self, key) -> float:
		if (len(self.linked) == 0): return None

		value = 0.0

		for link in self.linked:
			linkedEntity = link[0]
			if len(link) > 1:
				linkedCount = link[1]
			else:
				linkedCount = 1
					
			linkedAttrVal = linkedEntity.getFirstAttrValue(key)
			if linkedAttrVal != None:
				value += float(linkedAttrVal) * float(linkedCount)
		
		return value


	def getFirstAttrValue(self, key:str, includeAttached:bool = True) -> str:
		if( key.count("_self->") > 0 ):
			queryParts  : [str] = key.split("->",1)
			return(self.getFirstAttrValue(queryParts[1],False))

		# print("get [["+self.name+"]]::[["+key+"]]")

		attrList = self.getPath(key,False)
		if attrList is None:
			if includeAttached:
				return self.getAttachedValue(key)
			else:
				return None

		firstValue = attrList[0].values[0]

		if includeAttached == False or len(self.linked) == 0:
			return firstValue

		if is_number(firstValue):
			attachedValue = self.getAttachedValue(key)
			if attachedValue is not None:
				value = float(firstValue) + attachedValue 
				return str(value)
		
		return firstValue

	def getAttrList(self, key:str, create : bool = False) -> ['Attribute']:
		if key in self.attributes:
			return self.attributes[key]
		elif create:
			self.attributes[key] = [Attribute(key,None)]
			return self.attributes[key]
		else:
			# print("self.getAttrList [["+key+"]] -> None; \n\t" + str( self.attributes.keys() ))
			return None

	def getPath(self, key:str, create:bool = False) -> ['Attribute']:
		if( key.count("->") > 0 ):
			queryParts  : [str] = key.split("->",1)
		
			outerName : str = queryParts[0]
			innerName : str = queryParts[1]

			outerAttrs = self.getAttrList(outerName,create)
			if outerAttrs is not None:
				for candidate in outerAttrs: # return the first attribute in the list that has the innerName attr we need
					result = candidate.getPath(innerName, create)
					if result != None: return result
						
			return None
		else:
			return self.getAttrList(key,create)
		
	def addAttr(self, attr:'Attribute'):
		if(attr.name not in self.attributes):
			self.attributes[attr.name] = [attr]
		else:
			self.attributes[attr.name].append(attr)
	# ---
	# File output formatting
	# ---

	def getString(self,indent = 0) -> str:
		indentStr = ""
		for i in range(0, indent):
			indentStr += "\t"

		return indentStr + self.getStringSelf() + "\n" + self.getStringAttributes(indent + 1)

	def getValuesStr(self) -> str:
		out = ""
		if( self.values != None ):
			for value in self.values:
				out += " " + quoteValue(value)
		return out

	def getStringSelf(self) -> str:		
		return quoteName(self.name) + self.getValuesStr()

	def getStringAttributes(self,indent = 0) -> str:
		attrStr = ""
		for name, attrList in self.attributes.items():
			if attrList != None:
				for attr in attrList:
					attrStr += attr.getString(indent)
		return attrStr

class Entity(Attribute):
	def __init__(self, name:str, entityName : str):
		super(Entity, self).__init__(name,[entityName])

	def getStringSelf(self) -> str:
		return self.values[0] + " " + quoteValue(self.name)

# ----------------------------------------------

class Effect(Entity):
	def __init__(self, name:str):
		super(Effect, self).__init__(name,"effect")

class Outfit(Entity):
	def __init__(self, name:str):
		super(Outfit, self).__init__(name,"outfit")
	
class Ship(Entity):
	def __init__(self, name:str):
		super(Ship, self).__init__(name,"ship")
	
# ----------------------------------------------

classMap = {
		"outfit": Outfit,
		"effect": Effect,
		"ship": Ship
	}

entityIndex = {}
for typeName, clazz in classMap.items():
	entityIndex[typeName] = {}

# ----------------------------------------------

def loadContents():
	print("Load Ships:")
	for fileName in setupData["Files"]["Ships"]:
		outfitFileContents[fileName] = loadFile(fileName)

	print("Load Outfits:")
	for fileName in setupData["Files"]["Outfits"]:
		outfitFileContents[fileName] = loadFile(fileName)
	
	print("Load Effects:")
	for fileName in setupData["Files"]["Effects"]:
		outfitFileContents[fileName] = loadFile(fileName)

# ----------------------------------------------

def loadFile(fileName) -> {}:
	print(fileName)

	fileContents = []
	with open(inputPath + fileName) as fileHandle:
		entity = None						# currently loaded entity
		attributeStack :[Attribute] = []	# currently loaded attribute stack
		count : int = 0
		for line in fileHandle:
			line : str = line
			count += 1
			
			for typeName, clazz in classMap.items():
				if line.startswith(typeName):
					entityName :str= re.sub("^"+typeName+"\s+","", line).replace("\n","")

					if(entityName.count('`')>0):
						entityName = entityName.replace('`',"")
					else:
						entityName = entityName.replace('"',"")

					entity = clazz(entityName)

					fileContents.append(entity)
					entityIndex[typeName][entityName] = entity

			if entity != None and line.startswith("\t") and not line.isspace():				
				match : typing.Match = re.match('^(\t+)(("[^"]+")|(`[^`]+`)|([\S]+))\s?(.*)?$',line)

				if match == None:
					print("Failed match:\n\t[["+line+"]]\n\t@"+str(count))
					continue

				index : int = len(match.group(1))
				attrName :str = match.group(2)
				attrValue :str = match.group(6)

				if attrName == "#":
					continue

				if match.group(3) != None:
					attrName = attrName.replace('"',"")
				elif match.group(4) != None:
					attrName = attrName.replace('`',"")					

				valueMatches = re.findall('(("[^"]+")|(`[^`]+`)|(\S+))', attrValue)

				values = []
				for match in valueMatches:
					if match[1] != None:
						values.append(  match[0].replace('"',"") )
					elif match[2] != None:
						values.append(  match[0].replace('`',"") )
					else:
						values.append( match[0] )

				#values = [ match[0] for match in valueMatches ]
			
				attr = Attribute(attrName,values)

				if index == 1:	# outfit attribute
					entity.addAttr(attr)
					attributeStack :[Attribute] = [attr]
				elif index >= 2: # nested attribute	
					parent : Attribute = attributeStack[index-2]
					parent.addAttr(attr)

					if len(attributeStack) == index-1:
						attributeStack.append(attr)
					elif len(attributeStack) >= index:
						attributeStack[index-1] = attr
			elif line.startswith("#"):
				fileContents.append(line)
			# process line
		# for line in fileHandle
	# open file
	return fileContents
	
# ----------------------------------------------
def saveContents():
	print("Save:")
	for typeName in setupData["Files"].keys():
		saveEntities(typeName)
		
def saveEntities(entityType : str):
	print("\t"+entityType+":")
	for fileName in setupData["Files"][entityType]:
		print("\t\t"+fileName)

		contents = outfitFileContents[fileName]

		with open(outputPath + fileName, "w") as fileHandle:
			for entry in contents:
				if isinstance(entry, str):
					print( entry, end="", file=fileHandle )
				else:				
					print( entry.getString(), file=fileHandle )
					print( "", file=fileHandle )

					
# ----------------------------------------------		
def calculateValuesForOutfit(outfit : Outfit, stepCalculations:{} ) -> {str,float}:
	values : {str,float} = {}

	for value, process in stepCalculations.items():
		params : {str,float} = {}

		# get required params - skip outfit on fail
		if "withRequired" in process:
			for param, source in process["withRequired"].items():
				attrValue = outfit.getFirstAttrValue(source)
				if attrValue != None:
					params[param] = float(attrValue)
				else:
					return None

		# get optional data - default to zero on fail
		if "with" in process:
			for param, source in process["with"].items():
				attrValue = outfit.getFirstAttrValue(source)
				if attrValue != None:
					params[param] = float(attrValue)
				else:
					params[param] = 0.0

		# print("\t |-> "+value+" :: "+process["formula"]+": " + str(params))
		values[value] = parser.parse(process["formula"]).evaluate(params)
				
	return values

# ----------------------------------------------
def filter_greaterThan(attrValue:str,condData) -> bool:
	floatValue = float(attrValue)
	floatCond = float(condData)
	return floatValue > floatCond

def filter_containsAny(attrValue:str,condData) -> bool:
	for value in condData:
		if attrValue.lower().count( value.lower() ) > 0: 
			return True
	return False

filters = {
	"containsAny": filter_containsAny,
	"greaterThan": filter_greaterThan,
	}

def checkCriteriaForOutfit(outfit:Entity, criteria:{}) -> bool:
	for attrName,condition in criteria.items():
		if attrName == "_name":
			if isinstance(condition, str):
				if outfit.name != condition: return False
			else:
				for condType, condData in condition.items():
					if filters[condType](outfit.name,condData) == False: return False
		else:
			attrValue = outfit.getFirstAttrValue(attrName)

			if attrValue == None: 
				return False

			if isinstance(condition, str):
				if attrValue != condition: return False
			else:
				for condType, condData in condition.items():
					if filters[condType](attrValue,condData) == False: return False

	return True

# ----------------------------------------------
def execStep(setup : {}):
	stepName :str = setup["name"]
	stepTarget :str = setup["type"]
	stepCriteria : {str,str} = setup["criteria"]
	stepReference : [str] = setup["reference"] if ("reference" in setup) else  None
	stepCalculations : {} = setup["calculate"] if ("calculate" in setup) else  None
	stepActions : {} = setup["set"]

	referenceValues = {}

	print("")
	print("Execute step [["+stepName+"]] targeting [["+stepTarget+"]]")

	reference : [Outfit] = []
	workSet : [Outfit] = []

	for index,outfit in entityIndex[stepTarget].items():
		if checkCriteriaForOutfit(outfit, stepCriteria):
			workSet.append(outfit)

	print( "\t processing "+ str(len(workSet)) + " "+ stepTarget +"s")
		
	# ---
	# get reference entities
	# ---
	if stepReference is not None:
		for refName in stepReference:
			if refName in entityIndex[stepTarget]:
				reference.append(entityIndex[stepTarget][refName])

		for outfit in reference:
			print( "\t reference item: "+ outfit.name)
			referenceValues[outfit.name] = calculateValuesForOutfit(outfit, stepCalculations)
			for key,value in referenceValues[outfit.name].items():
				print( "\t\t - "+ key +": "+str(value))

		print("")

	for outfit in workSet:
		
		print("\n\t [ "+outfit.name+" ]")
		if stepCalculations is not None:
			values = calculateValuesForOutfit(outfit, stepCalculations)
			if values == None:
				print("\t |-> Skip " + stepTarget + " @ calculateValuesForOutfit()")
				continue
		else:
			values = {}

		for attributeName, process in stepActions.items():
			params : {str,float} = {}

			if "with" in process:
				for param, source in process["with"].items():
					attrValue = outfit.getFirstAttrValue(source)

					if attrValue != None:
						params[param] = float(attrValue)
					else:
						# TODO: skip here
						print("\t |-> Missing " + param + " @ set->with")
						params[param] = 0.0						

			for valueName, value in values.items():
				params[valueName] = value

			if stepReference is not None:
				#TODO: pick closest ref item
				for paramName, paramValue in referenceValues[ reference[0].name ].items():
					params["reference."+paramName] = paramValue

			# ----------------------------------------------		
			# calculate final value
			# ----------------------------------------------	

			print("\t |-> "+process["formula"]+": " + str(params))

			floatValue : float = parser.parse(process["formula"]).evaluate(params)
			value = floatValue

			# ----------------------------------------------		
			# handle value format
			# ----------------------------------------------		

			if( "format" in process ):
				formatDef : {} = process["format"]
				if( "precision" in formatDef ):
					formatPrecision = formatDef["precision"]
					formatStr = "{:."+formatPrecision+"f}"
					value = str.format(formatStr,floatValue)
				elif( "multiple" in formatDef ):
					formatMultiple : float = float(formatDef["multiple"])
					value = floatValue - (floatValue % formatMultiple)					

			# ----------------------------------------------		
			# set the value
			# ----------------------------------------------		
			attrList = outfit.getPath(attributeName,True)
			attrList[0].values = [value]
			print("\t |-> "+attributeName+": " + str(value))

# ----------------------------------------------			
def alterContents():
	for step in setupActions:
		execStep(step)

# ----------------------------------------------
def parseLink(link : str) -> (str,int):
	match = re.match("([a-zA-Z0-9\->]+)(\[(\d+)\])?",link)
	if match.group(3) != None:
		return (match.group(1), int(match.group(3)))
	else:
		return (match.group(1), 0)

def assembleContents():
	for entityType, connections in setupData["Structure"].items():
		print("Assembling: " + entityType)
		for link, targetType in connections.items():
			for name, entity in entityIndex[entityType].items():
				# remove index from link def, if present
				
				linkClean,linkIndex = parseLink(link)

				attrList : [Attribute] = entity.getPath(linkClean)
				if attrList != None:
					for ref in attrList:
						if len(ref.attributes) == 0 and len(ref.values) > linkIndex:
							targetName = ref.values[linkIndex]

							if targetName in entityIndex[targetType]:
								target = entityIndex[targetType][targetName]
								# extract count param, if present
								if len(ref.values) > linkIndex+1:
									count = ref.values[linkIndex+1]
								else:
									count = 1

								# print("Link [["+entityType+"]]:[[" + name + "]]@" + link + " -> [["+targetType+"]]:[["+targetName+"]] X " + str(count))

								ref.addLink(target, count)
								entity.addLink(target, count)

							else:
								print("Cannot find [["+targetType+"]]:[["+targetName+"]], \n\trequired by [["+entityType+"]]:[[" + name + "]] @ " + link)
						else:
							for targetName, attrValue in ref.attributes.items():
								if targetName in entityIndex[targetType]:
									target = entityIndex[targetType][targetName]
									# extract count param, if present
									if len(ref.values) > linkIndex+1:
										count = ref.values[linkIndex+1]
									else:
										count = 1

									# print("Link [["+entityType+"]]:[[" + name + "]]@" + link + " -> [["+targetType+"]]:[["+targetName+"]] X " + str(count))

									ref.addLink(target, count)
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
print("---")
assembleContents()
print("---")
alterContents()
print("---")
saveContents()
