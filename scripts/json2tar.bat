@rem Copyright (c) 2012-2013 Turbulenz Limited
@echo off
@rem Generate a TAR file for binary assets referenced from a JSON asset.

@python -m turbulenz_tools.tools.json2tar %*
