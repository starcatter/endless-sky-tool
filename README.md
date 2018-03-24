# endless-sky-tool
Python tool for manipulating and analyzing Endless Sky data.

# Installation/requirements
1. A recent version of Python 3
2. [py-expression-eval module](https://github.com/Axiacore/py-expression-eval) is required (run `pip install py_expression_eval` to get it)
3. Put project files where convenient, update input/output paths in JSON file

# Usage
Edit the `balancer.json` file and run the script. Make sure the output directory exists, making input=output is not recommended.

# balancer.json file
The file is split into two sections, `Setup` and `Actions`. The former one defines paths, file names and entity relations, while the latter decides what the script actually does.

The `Setup` section is composed of following keys:
- `Paths`, which defines input and output directories for the script, with a trailing slash
- `Files`, which defines file categories and their contents. Category names are just for readability, as the files can contain a mix of entity types. Files will be read from the input dir then their modified version will be written to the output dir.
- `Structure`, which defines entity relations by mapping attribute paths (with optional offsets) to entity types attached there. The offesets are used to skip hardpoint positioning info when looking for attached outift names in ship definitions.

The `Actions` section of the config file contains objects like this:

		{
			"name":"Balance Power - reactors",
			"type":"outfit",
			"criteria":{
				"category":"Power",
				"_name":{
					"containsAny":[
						"reactor",
						"core"
					]
				}
			},
			"reference":[
				"Fusion Reactor"
			],
			"calculate":{
				"powerToMassRatio":{
					"with":{
						"collection":"solar collection",
						"generation":"energy generation",
						"capacity":"energy capacity"
					},
					"withRequired":{
						"mass":"mass"
					},
					"formula":"(generation*2 + collection + capacity/18000)/mass"
				},
				"wasteRatio":{
					"with":{
						"heat":"heat generation"
					},
					"withRequired":{
						"mass":"mass"
					},
					"formula":"heat/mass"
				}
			},
			"set":{
				"required maintenance":{
					"with":{
						"mass":"mass"
					},
					"formula":"( (powerToMassRatio/reference.powerToMassRatio) * mass * (1 + wasteRatio*1.2) )/10"
				}
			}
		}

The `name` key is just for display/description

The `type` key defines the entity type that will be processed, currently only `outfit` and `ship` make sense, even though `effect` might work as well. Type names must be lowercase.

The `criteria` key defines which outfits will be included in the process
  - the keys are outfit attributes to be considered. Exception is the special key `_name` which refers to the outfit name.
  - the values define what the keys' values should be. Currently the options are: 
  	- a simple string that has to match the attribute value
	- a filter, currently supported filters are:
		- `containsAny`, which accepts a list of strings, at least one of which must be a part of the attribute value
		- `greaterThan`, which accepts a number that the given attribute has to be greater than for the entity to qualify

The `reference` key accepts a list of entity names which will be used as a reference point for calculating values. Currently only the first one is used.

The `calculate` key defines values that need to be calculated for the final value. They are calculated for both the currently processed outfit and the reference outfit.
  - the keys define variable names which will be available in the `set` section
  - the calculation definition is composed of three elements:
    - `with`, which map optional attributes from the outfit to variable names used in the `formula`
    - `withRequired`, which map required values. If the values are not present, the outfit will not be processed.
    - `formula`, expressing how the final variable is calculated
 
The `set` key defines outfit attributes which are supposed to be set by the process.
  - the keys are the attribute names which will be set. They can either be top-level attributes or refer to a path like `weapon->shield damage`.
  - the "set attribute" definition is composed of three elements:
	  - `with`, which maps attributes from the outfit to variable names (additional to the ones from `calculate`) available in the `formula`
	  - `formula`, expressing how the final variable is calculated
	  - `format`, defining how numbers will be formatted. Currently two options are available:
		- `precision`, which specifies decimal places in generated values
		- `multiple`, which forces the output value to be the multiple of the given number, eg for a value `532`, `"multiple":"25"` results in `525`.
  
  
# Notes
- In order to access nested attributes, use `->`, for example `"hDmg":"weapon->hull damage"`
- By default attributes are calculated including all connected outfits, such as `submunitions`, to get their raw values prefix the attribute name/path with `_self->`.
