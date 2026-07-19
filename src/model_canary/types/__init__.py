from typing import Any, Dict, List, Optional, Union

JSONValue = Union[str, int, float, bool, None, "JSONDict", "JSONList"]
JSONDict = dict[str, JSONValue]
JSONList = list[JSONValue]
JSON = Union[JSONDict, JSONList]

MaybeAsyncFunc = Union[callable, Any]
