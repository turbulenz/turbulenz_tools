@rem Copyright (c) 2012-2013 Turbulenz Limited
@echo off
@rem Convert Effect Yaml (.effect) files into a Turbulenz JSON asset.

@python -m turbulenz_tools.tools.effect2json %*
