@rem Copyright (c) 2013 Turbulenz Limited
@echo off
@rem Convert Wavefront (.obj) files into a Turbulenz JSON asset.

@python -m turbulenz_tools.tools.obj2json %*
