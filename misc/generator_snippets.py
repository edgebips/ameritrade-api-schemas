def GenerateTypes(pr, valid_types):

    for dname, dtype in sorted(valid_types.types.items()):
        GenerateType(pr, dtype)


# class GenerateHandler(TypeCallback):

#     def __init__(self, pr):
#         self.pr = pr

#     def Boolean(self, fname, dtype):
#         pass
#     def Integer(self, fname, dtype):
#         pass
#     def Float(self, fname, dtype):
#         pass
#     def String(self, fname, dtype):
#         pass
#     def Enum(self, fname, dtype):
#         pass
#     def Object(self, fname, dtype):
#         pass
#     def Array(self, fname, dtype):
#         pass
#

# def Dispatch(dtype, cb):
#     subtype_map = None
#     if dtype['type'] == 'boolean':
#         cb.Boolean(dtype)
#     elif dtype['type'] == 'integer':
#         cb.Integer(dtype)
#     elif ctype['type'] == 'number':
#         cb.Float(dtype)
#     elif ctype['type'] == 'string':
#         if 'enum' in ctype:
#             cb.Enum(dtype)
#         else:
#             cb.String(dtype)
#     elif ctype['type'] == 'object':
#         if 'properties' in ctype:
#             subtype_map = ctype['properties']
#             cb.Object(dtype)
#         elif 'additionalProperties' in ctype:
#             cb.Object(ctype['additionalProperties'])
#     elif ctype['type'] == 'array':
#         #subtype_map = {'ARRAY_ITEMS': ctype['items']}
#         cb.Array(dtype)
#     else:
#         raise NotImplementedError(str(dtype))

    # if subtype_map:
    #     Dispatch(subtype_map, name, accum)


    # for endpoint, request, response in convert_ameritrade_schemas.ParseSchemas(schemas_root):
    #     print("-" * 32, endpoint)
    #     string = ProcessResponse(endpoint, response)
    #     print(string)
    #     #break


"""

"XXXCollection": {
    "items": {
        "type": "object"
        "discriminator": "activityType",
        "properties": {
            "activityType": {
                "enum": [ ... ],
                "type": "string"
            }
        },
    },
    "type": "array",
    "xml": {
        "name": "XXX",
        "wrapped": true
    }
},

{
    "type": "object"
    "discriminator": "assetType",
    "properties": {
        "assetType": {
            "enum": [...],
            "type": "string"
        },
        ...
},


"""
