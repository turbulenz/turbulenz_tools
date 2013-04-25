@rem Copyright (c) 2012-2013 Turbulenz Limited
@echo off
@rem Convert XML assets into a structured JSON asset.

@python -m turbulenz_tools.tools.xml2json %*
