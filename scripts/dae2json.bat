@rem Copyright (c) 2012-2013 Turbulenz Limited
@echo off
@rem Convert Collada (.dae) files into a Turbulenz JSON asset.

@python -m turbulenz_tools.tools.dae2json %*
