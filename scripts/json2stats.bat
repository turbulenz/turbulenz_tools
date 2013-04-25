@rem Copyright (c) 2012-2013 Turbulenz Limited
@echo off
@rem Report metrics on Turbulenz JSON assets.

@python -m turbulenz_tools.tools.json2stats %*
