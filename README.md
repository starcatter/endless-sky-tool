# endless-sky-tool
Python tool for manipulating and analyzing Endless Sky data

# Installation/requirements
1. A recent version of Python 3
2. [py-expression-eval module](https://github.com/Axiacore/py-expression-eval) is required (run `pip install py_expression_eval` to get it)
3. Put project files where convenient, update input/output paths in JSON file

# Usage
Edit the `balancer.json` file and run the script. Make sure the output directory exists, making input=output is not recommended.

The `Actions` section of the config file contains objects like this:

		{
			"name":"Balance Power - reactors",
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

The `criteria` key defines which outfits will be included in the process
  - the keys are outfit attributes to be considered. Exception is the special key `_name` which refers to the outfit name.
  - the values define what the keys' values should be. Currently the only options are a simple string that has to match the attribute value and the `containsAny` filter, which accepts a list of strings, at least one of which must be a part of the attribute value.

The `reference` key accepts a list of outfit names which will be used as a reference point for calculating values. Currently only the first one is used.

The `calculate` key defines values that need to be calculated for the final value. They are calculated for both the currently processed outfit and the reference outfit.
  - the keys define variable names which will be available in the `set` section
  - the calculation definition is composed of three elements:
    - `with`, which map optional attributes from the outfit to variable names used in the `formula`
    - `withRequired`, which map required values. If the values are not present, the outfit will not be processed.
    - `formula`, expressing how the final variable is calculated
 
The `set` key defines outfit attributes which are supposed to be set by the process.
  - the keys are the attribute names which will be set. Currently only top-level attributes can be set.
  - the set definition is similar to the one for `calculate`, except all keys are required, ie. `with` works like `withRequired`.
  
# Notes
- Values are currently shortened to one decimal place. Formatting is on the TODO list
- In order to access nested attributes, use `->`, for example `"hDmg":"weapon->hull damage"`
- Attributes are calculated including all connected outfits, such as `submunitions`
